from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.assets.models import Asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.features.risk_radar.service import RiskRadarService, build_scan_snapshot
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import ProviderResult
from app.main import create_app
from app.models import Base, CampaignBriefRevision, LlmCall, Project, ScriptVersion
from app.schemas import JobType


class FakeProvider:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.requests: list[dict[str, Any]] = []

    def generate_json(self, **kwargs: Any) -> ProviderResult:
        self.requests.append(kwargs)
        return ProviderResult(
            payload=self.payload,
            actual_model="fake/radar-model",
            provider="fixture",
            input_tokens=120,
            output_tokens=80,
        )


def script_content() -> dict[str, Any]:
    return {
        "hooks": [{"id": "hook-1", "text": "Avoid this creator mistake."}],
        "selected_hook_id": "hook-1",
        "sections": [
            {
                "id": "section-1",
                "position": 1,
                "heading": "Opening",
                "text": "Email hello@example.com for guaranteed results.",
            }
        ],
        "title": "Creator workflow",
        "description": "A practical workflow.",
        "call_to_action": "Save this guide.",
        "production_notes": [],
    }


def routing() -> dict[str, Any]:
    return {
        "default_model": "fake/radar-model",
        "fallback_models": [],
        "free_only": True,
        "require_structured_output": True,
        "timeout_seconds": 30,
        "max_output_tokens": 512,
        "reasoning_effort": "low",
        "max_calls": 2,
    }


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)


def create_reviewable_content(session: Session) -> tuple[Project, Asset, ScriptVersion]:
    project = Project(
        owner_id="creator-a",
        name="RiskRadar demo",
        brief="Prepare a trustworthy product video.",
        target_platforms=["instagram"],
    )
    session.add(project)
    session.flush()
    asset = Asset(
        project_id=project.id,
        owner_id="creator-a",
        kind="video",
        public_id=f"creatorai/tests/risk-radar/{project.id}",
        resource_type="video",
        format="mp4",
        duration_ms=12_000,
        processing_status="ready",
        tags=[],
    )
    script = ScriptVersion(
        project_id=project.id,
        version=1,
        origin="creator",
        content=script_content(),
        requirement_checks=[],
        warning_ids=[],
        input_snapshot={},
    )
    session.add_all(
        [
            asset,
            script,
            CampaignBriefRevision(
                project_id=project.id,
                revision=1,
                content_mode="brand",
                brand_brief={
                    "brand_name": "CreatorAI",
                    "product_name": "CreatorAI Studio",
                    "approved_claims": [],
                    "requirements": [],
                    "forbidden_phrases": ["guaranteed results"],
                },
            ),
        ]
    )
    session.flush()
    project.current_script_version_id = script.id
    session.add_all(
        [
            TranscriptSegment(
                asset_id=asset.id,
                source_start_ms=0,
                source_end_ms=2_000,
                text="The source says this workflow helps creators plan clearly.",
            ),
            VisualObservation(
                asset_id=asset.id,
                source_start_ms=500,
                source_end_ms=500,
                frame_references=["frame_00500"],
                description="A laptop screen with an unreviewed notification is visible.",
                confidence=0.9,
            ),
        ]
    )
    session.commit()
    return project, asset, script


def test_risk_radar_merges_model_and_deterministic_findings(session: Session) -> None:
    project, asset, script = create_reviewable_content(session)
    snapshot = build_scan_snapshot(
        session,
        project=project,
        owner_id="creator-a",
        asset_id=asset.id,
        script_version_id=script.id,
        edit_version_id=None,
    )
    visual_reference = next(
        item["id"]
        for item in snapshot["review_references"]
        if item["source_type"] == "visual_observation"
    )
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.RISK_RADAR,
        idempotency_key="risk-radar-service",
        input_snapshot=snapshot,
        routing_snapshot=routing(),
    )
    claimed = JobRepository(session).claim_next(lease_seconds=30)
    assert claimed is not None and claimed.id == job.id
    provider = FakeProvider(
        {
            "summary": "Review the visible notification before release.",
            "findings": [
                {
                    "category": "visual_review",
                    "severity": "medium",
                    "title": "Visible notification needs review",
                    "description": (
                        "A sampled visual observation mentions an unreviewed notification."
                    ),
                    "recommendation": "Review the frame and crop or blur it if needed.",
                    "reference_ids": [visual_reference],
                }
            ],
        }
    )

    RiskRadarService(session, provider).execute_claimed_job(claimed)

    result = claimed.input_snapshot["result"]
    assert claimed.status == "completed"
    assert result["review_readiness"] == "creator_review_required"
    assert {finding["origin"] for finding in result["findings"]} == {"deterministic", "model"}
    assert any(finding["category"] == "personal_data" for finding in result["findings"])
    assert any(finding["category"] == "brand_policy" for finding in result["findings"])
    assert provider.requests[0]["routing"]["max_calls"] == 1
    calls = list(session.scalars(select(LlmCall).where(LlmCall.job_id == claimed.id)))
    assert len(calls) == 1 and calls[0].actual_model == "fake/radar-model"


def test_risk_radar_rejects_unknown_model_evidence(session: Session) -> None:
    project, asset, script = create_reviewable_content(session)
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.RISK_RADAR,
        idempotency_key="risk-radar-unknown-evidence",
        input_snapshot=build_scan_snapshot(
            session,
            project=project,
            owner_id="creator-a",
            asset_id=asset.id,
            script_version_id=script.id,
            edit_version_id=None,
        ),
        routing_snapshot=routing(),
    )
    claimed = JobRepository(session).claim_next(lease_seconds=30)
    assert claimed is not None and claimed.id == job.id
    provider = FakeProvider(
        {
            "summary": "An invalid evidence reference was returned.",
            "findings": [
                {
                    "category": "visual_review",
                    "severity": "low",
                    "title": "Invalid evidence",
                    "description": "This must not be accepted.",
                    "recommendation": "Do not show the finding.",
                    "reference_ids": ["visual:not-owned"],
                }
            ],
        }
    )

    RiskRadarService(session, provider).execute_claimed_job(claimed)

    assert claimed.status == "failed"
    assert "outside the selected project content" in claimed.error
    assert "result" not in claimed.input_snapshot


@pytest.fixture
def client_session() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    app = create_app()
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        openrouter_default_model="fake/radar-model",
    )

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator(id="creator-a")
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, session
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)


def test_risk_radar_api_queues_idempotently_and_returns_a_scoped_result(
    client_session: tuple[TestClient, Session],
) -> None:
    client, session = client_session
    project, asset, script = create_reviewable_content(session)
    url = f"/v1/projects/{project.id}/risk-radar/scans"
    request = {"asset_id": str(asset.id), "script_version_id": str(script.id)}
    headers = {"Idempotency-Key": "risk-radar-api"}

    accepted = client.post(url, headers=headers, json=request)
    repeated = client.post(url, headers=headers, json=request)
    conflict = client.post(url, headers=headers, json={"asset_id": str(asset.id)})

    assert accepted.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["id"] == accepted.json()["id"]
    assert conflict.status_code == 409
    result = client.get(f"{url}/{accepted.json()['id']}")
    assert result.status_code == 200
    assert result.json()["status"] == "queued"
    assert result.json()["result"] is None

    client.app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator(
        id="creator-b"
    )
    hidden = client.get(f"{url}/{accepted.json()['id']}")
    assert hidden.status_code == 404
