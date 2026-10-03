"""Provider-neutral bounded visual-observation contract."""

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

import httpx

from app.features.footage_analysis.media import FrameSample, sample_video_frames


class VisionNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class VisualObservationResult:
    source_start_ms: int
    source_end_ms: int
    frame_references: list[str]
    description: str
    confidence: float | None = None


class VisionProvider(Protocol):
    def inspect(self, source_path: Path) -> list[VisualObservationResult]: ...


class UnconfiguredVisionProvider:
    def inspect(self, source_path: Path) -> list[VisualObservationResult]:
        raise VisionNotConfigured(
            "Configure a vision provider and bounded frame sampler before running analysis."
        )


class GroqVisionProvider:
    """Bounded single-frame Llama Vision analysis with stable source-time references."""

    def __init__(
        self, *, api_key: str, base_url: str, model: str, interval_seconds: int, max_frames: int
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.interval_seconds = interval_seconds
        self.max_frames = max_frames

    def inspect(self, source_path: Path) -> list[VisualObservationResult]:
        with TemporaryDirectory(prefix="creatorai-frames-") as temporary_directory:
            samples = sample_video_frames(
                source_path,
                Path(temporary_directory),
                interval_seconds=self.interval_seconds,
                max_frames=self.max_frames,
            )
            return [self._describe_frame(sample) for sample in samples]

    def _describe_frame(self, frame: FrameSample) -> VisualObservationResult:
        encoded_image = base64.b64encode(frame.path.read_bytes()).decode("ascii")
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Describe only visible, factual video evidence. Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": 'Return {"description":"concise visual description"}.',
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                            },
                        ],
                    },
                ],
            },
            timeout=90,
        )
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            description = json.loads(content)["description"]
        except (httpx.HTTPStatusError, KeyError, TypeError, ValueError) as error:
            raise VisionNotConfigured(
                f"Groq vision could not describe a source frame: {response.text}"
            ) from error
        if not isinstance(description, str) or not description.strip():
            raise VisionNotConfigured("Groq vision returned a blank frame description.")
        return VisualObservationResult(
            source_start_ms=frame.source_time_ms,
            source_end_ms=frame.source_time_ms,
            frame_references=[frame.reference],
            description=description,
        )
