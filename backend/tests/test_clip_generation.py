from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.features.assets.models import Asset
from app.features.clip_generation.models import ClipCandidate
from app.features.clip_generation.service import generate_candidates
from app.features.script_alignment.models import ScriptAlignment
from app.models import Base, Project


def test_clip_candidates_are_ranked_bounded_and_persisted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(
        id=uuid4(), owner_id="clip-owner", name="Test", brief="Test", target_platforms=[]
    )
    asset = Asset(
        id=uuid4(), project_id=project.id, owner_id=project.owner_id, kind="video",
        public_id="creatorai/tests/clips", resource_type="video", format="mp4",
        duration_ms=30_000, processing_status="ready", tags=[],
    )
    alignments = [
        ScriptAlignment(asset_id=asset.id, source_start_ms=20_000, source_end_ms=21_000,
                        script_beat="Second hook", evidence_text="Second evidence", confidence=0.7),
        ScriptAlignment(asset_id=asset.id, source_start_ms=1_000, source_end_ms=2_000,
                        script_beat="Best hook", evidence_text="Best evidence", confidence=0.95),
    ]
    session.add_all([project, asset, *alignments])
    session.commit()

    candidates = generate_candidates(
        session, asset=asset, alignments=alignments, max_candidates=2,
        min_duration_ms=8_000, max_duration_ms=12_000,
    )

    assert candidates[0].hook == "Best hook"
    assert all(8_000 <= item.source_end_ms - item.source_start_ms <= 12_000 for item in candidates)
    assert all(item.source_end_ms <= 30_000 for item in candidates)
    assert len(list(session.scalars(select(ClipCandidate)))) == 2
    session.close()
    engine.dispose()
