from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Asset, Base, Project, TranscriptSegment, VisualObservation
from app.services.analysis import replace_transcript_segments, replace_visual_observations
from app.services.transcription import TranscriptSegmentResult
from app.services.vision import VisualObservationResult


@pytest.fixture
def analysis_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    project = Project(
        id=uuid4(),
        owner_id="analysis-owner",
        name="Analysis test",
        brief="Validate source evidence persistence.",
        target_platforms=[],
    )
    asset = Asset(
        id=uuid4(),
        project_id=project.id,
        owner_id=project.owner_id,
        kind="video",
        public_id="creatorai/tests/analysis",
        resource_type="video",
        format="mp4",
        duration_ms=10_000,
        processing_status="ready",
        tags=[],
    )
    session.add_all([project, asset])
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_replacing_transcript_segments_preserves_only_latest_analysis(
    analysis_session: Session,
) -> None:
    asset = analysis_session.scalar(select(Asset))
    assert asset is not None

    replace_transcript_segments(
        analysis_session,
        asset=asset,
        segments=[TranscriptSegmentResult(0, 2_000, "First result")],
    )
    analysis_session.commit()

    replace_transcript_segments(
        analysis_session,
        asset=asset,
        segments=[TranscriptSegmentResult(2_000, 4_000, "Replacement result")],
    )
    analysis_session.commit()

    saved_segments = list(analysis_session.scalars(select(TranscriptSegment)))
    assert [segment.text for segment in saved_segments] == ["Replacement result"]


def test_analysis_rejects_evidence_outside_source_duration(analysis_session: Session) -> None:
    asset = analysis_session.scalar(select(Asset))
    assert asset is not None

    with pytest.raises(ValueError, match="beyond the source asset duration"):
        replace_visual_observations(
            analysis_session,
            asset=asset,
            observations=[
                VisualObservationResult(
                    source_start_ms=9_500,
                    source_end_ms=10_500,
                    frame_references=["frame_09500"],
                    description="Product shown on screen",
                    confidence=0.8,
                )
            ],
        )


def test_visual_observations_are_persisted_with_source_evidence(
    analysis_session: Session,
) -> None:
    asset = analysis_session.scalar(select(Asset))
    assert asset is not None

    replace_visual_observations(
        analysis_session,
        asset=asset,
        observations=[
            VisualObservationResult(
                source_start_ms=5_000,
                source_end_ms=5_000,
                frame_references=["frame_05000"],
                description="The creator holds the product package.",
                confidence=0.9,
            )
        ],
    )
    analysis_session.commit()

    observation = analysis_session.scalar(select(VisualObservation))
    assert observation is not None
    assert observation.frame_references == ["frame_05000"]
    assert observation.confidence == 0.9
