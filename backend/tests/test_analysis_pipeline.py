from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.features.assets.models import Asset
from app.features.footage_analysis.pipeline import analyze_ready_asset
from app.features.footage_analysis.transcription import TranscriptSegmentResult
from app.features.footage_analysis.vision import VisualObservationResult
from app.models import Base, Project, TranscriptSegment, VisualObservation


class FakeStorage:
    def download_original_to_path(self, *, destination: Path, **_kwargs: object) -> None:
        destination.write_bytes(b"source bytes")


class FakeTranscriptionProvider:
    def transcribe(self, _source_path: Path) -> list[TranscriptSegmentResult]:
        return [TranscriptSegmentResult(0, 1_000, "A test sentence.")]


class FakeVisionProvider:
    def inspect(self, _source_path: Path) -> list[VisualObservationResult]:
        return [
            VisualObservationResult(
                500, 500, ["source_frame_ms:500"], "A creator speaks to camera."
            )
        ]


def test_analysis_pipeline_persists_provider_evidence() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(
        id=uuid4(), owner_id="analysis-worker", name="Test", brief="Test", target_platforms=[]
    )
    asset = Asset(
        id=uuid4(),
        project_id=project.id,
        owner_id=project.owner_id,
        kind="video",
        public_id="creatorai/tests/pipeline",
        resource_type="video",
        format="mp4",
        duration_ms=10_000,
        processing_status="ready",
        tags=[],
    )
    session.add_all([project, asset])
    session.commit()

    analyze_ready_asset(
        session,
        asset=asset,
        storage=FakeStorage(),
        transcription_provider=FakeTranscriptionProvider(),
        vision_provider=FakeVisionProvider(),
    )

    assert asset.processing_status == "ready"
    assert session.scalar(select(TranscriptSegment)).text == "A test sentence."
    assert session.scalar(select(VisualObservation)).frame_references == ["source_frame_ms:500"]
    session.close()
    engine.dispose()
