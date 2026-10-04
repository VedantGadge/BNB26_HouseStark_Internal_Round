from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Asset, Base, Project
from app.services.ingestion import AssetIngestionError, ingest_uploaded_asset
from app.services.rendering import MediaProbe, MediaProbeError


class FakeStorage:
    def download_original_to_path(self, *, destination: Path, **_kwargs: object) -> None:
        destination.write_bytes(b"temporary media bytes")


@pytest.fixture
def ingestion_session() -> tuple[Session, Asset]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(
        id=uuid4(),
        owner_id="ingestion-owner",
        name="Ingestion test",
        brief="Validate worker-local media inspection.",
        target_platforms=[],
    )
    asset = Asset(
        id=uuid4(),
        project_id=project.id,
        owner_id=project.owner_id,
        kind="video",
        public_id="creatorai/tests/ingestion",
        resource_type="video",
        format="mp4",
        processing_status="uploaded",
        tags=[],
    )
    session.add_all([project, asset])
    session.commit()
    yield session, asset
    session.close()
    engine.dispose()


def test_ingestion_marks_verified_asset_ready(
    ingestion_session: tuple[Session, Asset], monkeypatch: pytest.MonkeyPatch
) -> None:
    session, asset = ingestion_session
    expected_probe = MediaProbe(
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        duration_ms=12_340,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec="aac",
        has_audio=True,
    )
    monkeypatch.setattr(
        "app.features.footage_analysis.ingestion.probe_media", lambda _path: expected_probe
    )

    probe = ingest_uploaded_asset(session, asset=asset, storage=FakeStorage())

    assert probe == expected_probe
    assert asset.processing_status == "ready"
    assert asset.duration_ms == 12_340
    assert asset.width == 1920
    assert asset.height == 1080
    assert asset.processing_error is None


def test_ingestion_persists_failure_for_retry_visibility(
    ingestion_session: tuple[Session, Asset], monkeypatch: pytest.MonkeyPatch
) -> None:
    session, asset = ingestion_session

    def fail_probe(_path: Path) -> MediaProbe:
        raise MediaProbeError("Invalid media")

    monkeypatch.setattr("app.features.footage_analysis.ingestion.probe_media", fail_probe)

    with pytest.raises(AssetIngestionError, match="Asset ingestion failed"):
        ingest_uploaded_asset(session, asset=asset, storage=FakeStorage())

    assert asset.processing_status == "failed"
    assert asset.processing_error == "Invalid media"
