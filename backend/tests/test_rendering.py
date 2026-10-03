import subprocess
from pathlib import Path

import pytest

from app.services.rendering import MediaProbeError, probe_media


def test_probe_media_extracts_normalized_video_facts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source.mp4"
    source.touch()

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[:2] == ["ffprobe", "-v"]
        assert command[-1] == str(source)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"format":{"format_name":"mov,mp4,m4a,3gp,3g2,mj2","duration":"12.34"},'
                '"streams":[{"codec_type":"video","codec_name":"h264","width":1920,'
                '"height":1080},{"codec_type":"audio","codec_name":"aac"}]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    probe = probe_media(source)

    assert probe.duration_ms == 12_340
    assert probe.width == 1920
    assert probe.height == 1080
    assert probe.video_codec == "h264"
    assert probe.audio_codec == "aac"
    assert probe.has_audio is True


def test_probe_media_rejects_failed_ffprobe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "broken.mp4"
    source.touch()

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 1, stdout="", stderr="Invalid data found"
        ),
    )

    with pytest.raises(MediaProbeError, match="Invalid data found"):
        probe_media(source)


def test_probe_media_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(MediaProbeError, match="does not exist"):
        probe_media(tmp_path / "missing.mp4")
