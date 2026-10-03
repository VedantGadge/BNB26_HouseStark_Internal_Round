from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db_session
from app.features.assets.models import Asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.main import app
from app.models import Base, Project


@pytest.fixture
def analysis_client() -> Generator[tuple[TestClient, UUID], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = "analysis-api-owner"
    project_id = uuid4()
    asset_id = uuid4()
    with session_factory() as session:
        session.add(
            Project(
                id=project_id,
                owner_id=owner_id,
                name="Analysis API project",
                brief="Expose grounded evidence to the editor.",
                target_platforms=[],
            )
        )
        session.add(
            Asset(
                id=asset_id,
                project_id=project_id,
                owner_id=owner_id,
                kind="video",
                public_id="creatorai/tests/analysis-api",
                resource_type="video",
                format="mp4",
                duration_ms=12_000,
                processing_status="ready",
                tags=[],
            )
        )
        session.add_all(
            [
                TranscriptSegment(
                    asset_id=asset_id,
                    source_start_ms=0,
                    source_end_ms=2_000,
                    text="This is the opening hook.",
                ),
                VisualObservation(
                    asset_id=asset_id,
                    source_start_ms=500,
                    source_end_ms=500,
                    frame_references=["frame_00500"],
                    description="The product package appears in frame.",
                    confidence=0.95,
                ),
            ]
        )
        session.commit()

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as client:
        yield client, asset_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_asset_analysis_returns_owned_grounded_evidence(
    analysis_client: tuple[TestClient, UUID],
) -> None:
    client, asset_id = analysis_client

    response = client.get(
        f"/v1/assets/{asset_id}/analysis",
        headers={"X-Creator-ID": "analysis-api-owner"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["processing_status"] == "ready"
    assert payload["transcript_segments"][0]["source_end_ms"] == 2_000
    assert payload["visual_observations"][0]["frame_references"] == ["frame_00500"]


def test_asset_analysis_hides_another_owners_asset(
    analysis_client: tuple[TestClient, UUID],
) -> None:
    client, asset_id = analysis_client

    response = client.get(
        f"/v1/assets/{asset_id}/analysis",
        headers={"X-Creator-ID": "another-owner"},
    )

    assert response.status_code == 404
