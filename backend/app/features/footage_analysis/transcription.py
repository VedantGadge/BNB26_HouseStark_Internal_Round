"""Provider-neutral timestamped speech-to-text contract."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

import httpx

from app.features.footage_analysis.media import extract_audio_to_flac


class TranscriptionNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptSegmentResult:
    source_start_ms: int
    source_end_ms: int
    text: str
    word_timings: list[dict[str, object]] | None = None


class TranscriptionProvider(Protocol):
    def transcribe(self, source_path: Path) -> list[TranscriptSegmentResult]: ...


class UnconfiguredTranscriptionProvider:
    def transcribe(self, source_path: Path) -> list[TranscriptSegmentResult]:
        raise TranscriptionNotConfigured(
            "Configure a timestamp-capable transcription provider before running analysis."
        )


class GroqTranscriptionProvider:
    """Groq Whisper adapter that always returns evidence on the source-media clock."""

    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def transcribe(self, source_path: Path) -> list[TranscriptSegmentResult]:
        with TemporaryDirectory(prefix="creatorai-transcript-") as temporary_directory:
            audio_path = Path(temporary_directory) / "speech.flac"
            extract_audio_to_flac(source_path, audio_path)
            with audio_path.open("rb") as audio_file:
                response = httpx.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=[
                        ("file", (audio_path.name, audio_file, "audio/flac")),
                        ("model", (None, self.model)),
                        ("response_format", (None, "verbose_json")),
                        ("timestamp_granularities[]", (None, "segment")),
                        ("timestamp_granularities[]", (None, "word")),
                        ("temperature", (None, "0")),
                    ],
                    timeout=180,
                )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise TranscriptionNotConfigured(
                f"Groq transcription rejected the request: {response.text}"
            ) from error
        return _parse_groq_transcript(response.json())


def _parse_groq_transcript(payload: object) -> list[TranscriptSegmentResult]:
    if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
        raise TranscriptionNotConfigured("Groq did not return timestamped transcript segments.")
    words = payload.get("words") if isinstance(payload.get("words"), list) else []
    results: list[TranscriptSegmentResult] = []
    for segment in payload["segments"]:
        if not isinstance(segment, dict):
            continue
        start_ms, end_ms = _milliseconds(segment.get("start")), _milliseconds(segment.get("end"))
        text = segment.get("text")
        if start_ms is None or end_ms is None or end_ms <= start_ms or not isinstance(text, str):
            continue
        timing = _words_for_segment(words, start_ms, end_ms)
        results.append(TranscriptSegmentResult(start_ms, end_ms, text, timing or None))
    if not results:
        raise TranscriptionNotConfigured("Groq returned no valid timestamped transcript segments.")
    return results


def _words_for_segment(words: list[object], start_ms: int, end_ms: int) -> list[dict[str, object]]:
    timings: list[dict[str, object]] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        word_start, word_end = _milliseconds(word.get("start")), _milliseconds(word.get("end"))
        token = word.get("word")
        if word_start is None or word_end is None or not isinstance(token, str):
            continue
        if word_start >= start_ms and word_end <= end_ms:
            timings.append(
                {"word": token, "source_start_ms": word_start, "source_end_ms": word_end}
            )
    return timings


def _milliseconds(value: object) -> int | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    return round(seconds * 1000) if seconds >= 0 else None
