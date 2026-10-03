"""Controlled FFmpeg compilation for immutable short-form edit recipes."""

import subprocess
import textwrap
from pathlib import Path

from app.features.editing.schemas import CaptionStyle, EditRecipePayload, OverlayPosition


class RenderCompilationError(RuntimeError):
    pass


def render_recipe_to_mp4(
    *,
    source_path: Path,
    destination: Path,
    recipe: EditRecipePayload,
    has_audio: bool,
    timeout_seconds: int,
    ffmpeg_binary: str = "ffmpeg",
) -> None:
    """Render one source segment without ever accepting executable user input."""

    text_directory = destination.parent / "overlay-text"
    text_directory.mkdir(exist_ok=True)
    video_filter = _build_video_filter(recipe, text_directory=text_directory)
    duration_seconds = _seconds(recipe.source_end_ms - recipe.source_start_ms)
    command = [
        ffmpeg_binary,
        "-y",
        "-ss",
        _seconds(recipe.source_start_ms),
        "-i",
        str(source_path),
        "-t",
        duration_seconds,
        "-filter_complex",
        video_filter,
        "-map",
        "[video]",
    ]
    if has_audio:
        command.extend(["-map", "0:a?"])
        audio_filter = _build_audio_filter(
            recipe, duration_ms=recipe.source_end_ms - recipe.source_start_ms
        )
        if audio_filter:
            command.extend(["-af", audio_filter])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
        ]
    )
    if has_audio:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    command.extend(["-movflags", "+faststart", str(destination)])
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout_seconds
        )
    except FileNotFoundError as error:
        raise RenderCompilationError("ffmpeg is not installed on this worker.") from error
    except subprocess.TimeoutExpired as error:
        raise RenderCompilationError("FFmpeg timed out while rendering this edit.") from error
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        if "No such filter: 'drawtext'" in result.stderr:
            raise RenderCompilationError(
                "This FFmpeg build lacks drawtext. Install a build with FreeType and "
                "HarfBuzz support, then set FFMPEG_BINARY to that executable."
            )
        detail = result.stderr.strip()[-2_000:] if result.stderr else "FFmpeg produced no MP4."
        raise RenderCompilationError(detail)


def _build_video_filter(recipe: EditRecipePayload, *, text_directory: Path) -> str:
    width = recipe.output.width
    height = recipe.output.height
    filters = ["setpts=PTS-STARTPTS", "fps=30"]
    if recipe.output.fit == "pad":
        filters.extend(
            [
                f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
            ]
        )
    else:
        filters.extend(
            [
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                (
                    f"crop={width}:{height}:x=(iw-ow)*{recipe.crop.center_x:.4f}:"
                    f"y=(ih-oh)*{recipe.crop.center_y:.4f}"
                ),
            ]
        )
    if recipe.emphasis_zooms:
        filters.append(_zoom_filter(recipe, width=width, height=height))
    if recipe.title is not None:
        title_path = text_directory / "title.txt"
        title_path.write_text(
            textwrap.fill(recipe.title.text, max(12, width // 34)), encoding="utf-8"
        )
        filters.append(
            _draw_text_filter(
                text_path=title_path,
                style="title",
                position=recipe.title.position,
                start_ms=recipe.title.start_ms,
                end_ms=recipe.title.end_ms,
                safe_top_px=recipe.output.safe_top_px,
                safe_bottom_px=recipe.output.safe_bottom_px,
            )
        )
    if recipe.captions_enabled:
        for index, caption in enumerate(recipe.captions):
            caption_path = text_directory / f"caption-{index}.txt"
            caption_path.write_text(
                textwrap.fill(caption.text, max(12, width // 34)), encoding="utf-8"
            )
            filters.append(
                _draw_text_filter(
                    text_path=caption_path,
                    style=recipe.caption_style.value,
                    position=OverlayPosition.BOTTOM,
                    start_ms=caption.start_ms,
                    end_ms=caption.end_ms,
                    safe_top_px=recipe.output.safe_top_px,
                    safe_bottom_px=recipe.output.safe_bottom_px,
                )
            )
    filters.append("setsar=1")
    return f"[0:v]{','.join(filters)}[video]"


def _zoom_filter(recipe: EditRecipePayload, *, width: int, height: int) -> str:
    expression = "1"
    for zoom in reversed(recipe.emphasis_zooms):
        start_frame = round(zoom.start_ms * 30 / 1_000)
        end_frame = round(zoom.end_ms * 30 / 1_000)
        expression = (
            f"if(between(on\\,{start_frame}\\,{end_frame})\\,{zoom.scale:.3f}\\,{expression})"
        )
    return (
        f"zoompan=z='{expression}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps=30"
    )


def _draw_text_filter(
    *,
    text_path: Path,
    style: str,
    position: OverlayPosition,
    start_ms: int,
    end_ms: int,
    safe_top_px: int,
    safe_bottom_px: int,
) -> str:
    font_color, font_size, box_color = _draw_text_style(style)
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font = f"fontfile={font_path}:" if font_path.is_file() else "font=Arial:"
    y_position = (
        str(safe_top_px) if position is OverlayPosition.TOP else f"h-text_h-{safe_bottom_px}"
    )
    return (
        "drawtext="
        f"{font}textfile={text_path}:expansion=none:"
        f"fontcolor={font_color}:fontsize={font_size}:"
        "x=(w-text_w)/2:"
        f"y={y_position}:box=1:boxcolor={box_color}:boxborderw=18:"
        f"enable='between(t\\,{_seconds(start_ms)}\\,{_seconds(end_ms)})'"
    )


def _draw_text_style(style: str) -> tuple[str, int, str]:
    styles = {
        CaptionStyle.CLEAN.value: ("white", 48, "black@0.45"),
        CaptionStyle.BOLD.value: ("white", 62, "black@0.65"),
        CaptionStyle.BOLD_HIGHLIGHT.value: ("yellow", 62, "black@0.70"),
        "title": ("white", 64, "black@0.70"),
    }
    return styles[style]


def _build_audio_filter(recipe: EditRecipePayload, *, duration_ms: int) -> str | None:
    filters: list[str] = ["asetpts=PTS-STARTPTS"]
    if recipe.audio.normalize:
        filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
    if recipe.audio.fade_in_ms:
        filters.append(f"afade=t=in:st=0:d={_seconds(recipe.audio.fade_in_ms)}")
    if recipe.audio.fade_out_ms:
        filters.append(
            "afade=t=out:"
            f"st={_seconds(max(duration_ms - recipe.audio.fade_out_ms, 0))}:"
            f"d={_seconds(recipe.audio.fade_out_ms)}"
        )
    return ",".join(filters) or None


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1_000:.3f}"
