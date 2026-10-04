"""Temporary audio and frame extraction for provider-backed footage analysis."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.features.footage_analysis.probe import probe_media


class MediaExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrameSample:
    source_time_ms: int
    reference: str
    path: Path


def extract_audio_to_flac(source_path: Path, destination: Path) -> None:
    """Create compact, speech-ready 16 kHz mono FLAC for transcription providers."""

    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "flac",
            str(destination),
        ]
    )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise MediaExtractionError("FFmpeg did not produce an audio track for transcription.")


def sample_video_frames(
    source_path: Path,
    destination_directory: Path,
    *,
    interval_seconds: int,
    max_frames: int,
    source_timestamps_ms: list[int] | None = None,
) -> list[FrameSample]:
    probe = probe_media(source_path)
    if probe.duration_ms is None or probe.duration_ms <= 0:
        raise MediaExtractionError("Cannot sample video frames without a positive source duration.")
    timestamps = (
        sorted({t for t in source_timestamps_ms if 0 <= t < probe.duration_ms})[:max_frames]
        if source_timestamps_ms is not None
        else _sample_timestamps(probe.duration_ms, interval_seconds * 1000, max_frames)
    )
    samples: list[FrameSample] = []
    for timestamp_ms in timestamps:
        frame_path = destination_directory / f"frame-{timestamp_ms:09d}.jpg"
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{timestamp_ms / 1000:.3f}",
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(frame_path),
            ]
        )
        if frame_path.is_file() and frame_path.stat().st_size > 0:
            samples.append(
                FrameSample(
                    source_time_ms=timestamp_ms,
                    reference=f"source_frame_ms:{timestamp_ms}",
                    path=frame_path,
                )
            )
    if not samples:
        raise MediaExtractionError("FFmpeg could not extract a usable video frame.")
    return samples


def _sample_timestamps(duration_ms: int, interval_ms: int, max_frames: int) -> list[int]:
    first_time_ms = min(1_000, max(duration_ms - 1, 0))
    return list(range(first_time_ms, duration_ms, interval_ms))[:max_frames]


def _run_ffmpeg(command: list[str]) -> None:
    command[0] = get_settings().ffmpeg_binary
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    except FileNotFoundError as error:
        raise MediaExtractionError("ffmpeg is not installed on this worker.") from error
    except subprocess.TimeoutExpired as error:
        raise MediaExtractionError("ffmpeg timed out while preparing analysis media.") from error
    if result.returncode != 0:
        raise MediaExtractionError(result.stderr.strip() or "ffmpeg media extraction failed.")
