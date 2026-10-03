from pathlib import Path
from subprocess import CompletedProcess
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.features.assets.models import Asset
from app.features.clip_generation.models import ClipCandidate
from app.features.editing.renderer import render_recipe_to_mp4
from app.features.editing.schemas import EditRecipePayload, EditVersionCreate, TitleOverlay
from app.features.editing.service import EditConflictError, create_edit_version
from app.features.footage_analysis.models import TranscriptSegment
from app.models import Base, Project


def test_assisted_recipe_versions_are_immutable_and_detect_stale_saves() -> None:
    session, asset, candidate = _editing_fixture()
    first = create_edit_version(
        session,
        candidate=candidate,
        asset=asset,
        payload=EditVersionCreate(),
    )

    assert first.revision == 1
    assert first.author_type == "assistant"
    assert first.recipe["captions"]
    draft = EditRecipePayload.model_validate(first.recipe)
    revised_recipe = draft.model_copy(update={"captions_enabled": False})
    second = create_edit_version(
        session,
        candidate=candidate,
        asset=asset,
        payload=EditVersionCreate(base_version_id=first.id, recipe=revised_recipe),
    )

    assert second.revision == 2
    assert second.parent_version_id == first.id
    assert second.recipe["captions_enabled"] is False
    assert first.recipe["captions_enabled"] is True
    with pytest.raises(EditConflictError):
        create_edit_version(
            session,
            candidate=candidate,
            asset=asset,
            payload=EditVersionCreate(base_version_id=first.id, recipe=draft),
        )
    session.close()


def test_renderer_uses_text_files_not_untrusted_overlay_text(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"placeholder")
    captured_command: list[str] = []
    unsafe_text = "hello; rm -rf / : [video]"

    def fake_run(command: list[str], **_kwargs: object) -> CompletedProcess[str]:
        captured_command.extend(command)
        destination.write_bytes(b"rendered")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("app.features.editing.renderer.subprocess.run", fake_run)
    recipe = EditRecipePayload(
        source_start_ms=0,
        source_end_ms=8_000,
        title=TitleOverlay(text=unsafe_text),
    )

    render_recipe_to_mp4(
        source_path=source,
        destination=destination,
        recipe=recipe,
        has_audio=True,
        timeout_seconds=30,
    )

    assert unsafe_text not in captured_command
    assert (tmp_path / "overlay-text" / "title.txt").read_text(encoding="utf-8") == unsafe_text
    assert "libx264" in captured_command
    assert captured_command[captured_command.index("-movflags") + 1] == "+faststart"
    assert (
        "asetpts=PTS-STARTPTS,loudnorm=I=-16:LRA=11:TP=-1.5,"
        "afade=t=in:st=0:d=0.120,afade=t=out:st=7.820:d=0.180" in captured_command
    )


def _editing_fixture() -> tuple[Session, Asset, ClipCandidate]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
    Base.metadata.create_all(engine)
    project = Project(
        id=uuid4(), owner_id="edit-owner", name="Test", brief="Test", target_platforms=[]
    )
    asset = Asset(
        id=uuid4(),
        project_id=project.id,
        owner_id=project.owner_id,
        kind="video",
        public_id="creatorai/tests/editing",
        resource_type="video",
        format="mp4",
        duration_ms=30_000,
        processing_status="ready",
        tags=[],
    )
    candidate = ClipCandidate(
        id=uuid4(),
        asset_id=asset.id,
        source_start_ms=4_000,
        source_end_ms=16_000,
        hook="A stronger opening hook",
        transcript_text="First transcript evidence",
        score=0.9,
        reasons=["test"],
    )
    segment = TranscriptSegment(
        asset_id=asset.id,
        source_start_ms=4_000,
        source_end_ms=8_000,
        text="This is a caption generated from real transcript evidence.",
    )
    session.add_all([project, asset, candidate, segment])
    session.commit()
    return session, asset, candidate
