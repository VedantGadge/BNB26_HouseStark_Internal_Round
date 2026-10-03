"""Safe FFprobe media inspection for worker-local source files."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaProbeError(RuntimeError):
    """Raised when a source cannot be inspected safely with ffprobe."""


@dataclass(frozen=True)
class MediaProbe:
    format_name: str | None
    duration_ms: int | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    has_audio: bool


def probe_media(source_path: Path, *, timeout_seconds: int = 30) -> MediaProbe:
    if not source_path.is_file():
        raise MediaProbeError("The local media source does not exist or is not a regular file.")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(source_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as error:
        raise MediaProbeError("ffprobe is not installed on this worker.") from error
    except subprocess.TimeoutExpired as error:
        raise MediaProbeError("ffprobe timed out while inspecting the media source.") from error
    if result.returncode != 0:
        raise MediaProbeError(
            result.stderr.strip() or "ffprobe could not inspect the media source."
        )
    try:
        payload: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise MediaProbeError("ffprobe returned invalid metadata.") from error
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise MediaProbeError("ffprobe response did not contain media streams.")
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    format_metadata = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    return MediaProbe(
        format_name=_optional_string(format_metadata.get("format_name")),
        duration_ms=_duration_milliseconds(format_metadata, video_stream, audio_stream),
        width=_optional_positive_integer(video_stream, "width"),
        height=_optional_positive_integer(video_stream, "height"),
        video_codec=_optional_string(video_stream.get("codec_name")) if video_stream else None,
        audio_codec=_optional_string(audio_stream.get("codec_name")) if audio_stream else None,
        has_audio=audio_stream is not None,
    )


def _duration_milliseconds(
    format_metadata: dict[str, Any],
    video_stream: dict[str, Any] | None,
    audio_stream: dict[str, Any] | None,
) -> int | None:
    for candidate in (
        format_metadata.get("duration"),
        video_stream.get("duration") if video_stream else None,
        audio_stream.get("duration") if audio_stream else None,
    ):
        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return round(value * 1000)
    return None


def _optional_positive_integer(stream: dict[str, Any] | None, key: str) -> int | None:
    if stream is None:
        return None
    try:
        value = int(stream[key])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value > 0 else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
