from pathlib import Path

import httpx

from app.features.footage_analysis.media import FrameSample
from app.features.footage_analysis.vision import GroqVisionProvider


def test_groq_vision_limits_completion_tokens(monkeypatch, tmp_path: Path) -> None:
    frame_path = tmp_path / "frame.jpg"
    frame_path.write_bytes(b"jpeg bytes")
    request_payload: dict[str, object] = {}

    def fake_post(*_args: object, **kwargs: object) -> httpx.Response:
        request_payload.update(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            json={"choices": [{"message": {"content": '{"description":"A person speaks."}'}}]},
        )

    monkeypatch.setattr("app.features.footage_analysis.vision.httpx.post", fake_post)
    provider = GroqVisionProvider(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        interval_seconds=30,
        max_frames=2,
        max_completion_tokens=256,
    )

    observation = provider._describe_frame(FrameSample(1_000, "source_frame_ms:1000", frame_path))

    assert request_payload["max_completion_tokens"] == 256
    assert observation.description == "A person speaks."


def test_targeted_refinement_uses_bounded_source_timestamps(monkeypatch, tmp_path):
    seen = []

    def sample(source, destination, **kwargs):
        seen.append(kwargs)
        return [FrameSample(5000, "source_frame_ms:5000", tmp_path / "frame.jpg")]

    monkeypatch.setattr("app.features.footage_analysis.vision.sample_video_frames", sample)
    provider = GroqVisionProvider(
        api_key="test-key",
        base_url="https://example.test",
        model="test",
        interval_seconds=30,
        max_frames=2,
        max_completion_tokens=256,
    )
    monkeypatch.setattr(provider, "_describe_frame", lambda frame: frame.reference)
    assert provider.inspect_at(tmp_path / "source.mp4", [5000, 9000]) == ["source_frame_ms:5000"]
    assert seen[0]["max_frames"] == 2 and seen[0]["source_timestamps_ms"] == [5000, 9000]
