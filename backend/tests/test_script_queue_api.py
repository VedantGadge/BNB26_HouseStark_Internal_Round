from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_script_workflow import FakeProvider, valid_script_payload

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.service import ScriptCreationService
from app.main import create_app
from app.models import Base, Job, ScriptVersion
from app.repositories import ProjectRepository
from app.schemas import JobStatus, JobType, Platform, ProjectCreate


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
        _env_file=None, openrouter_api_key="test-key", openrouter_default_model="free/model"
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


def create_project(session: Session):
    return ProjectRepository(session).create(
        "creator-a",
        ProjectCreate(
            name="Creator queue API",
            brief="Explain a creator workflow in a short, useful Reel.",
            target_platforms=[Platform.INSTAGRAM],
        ),
    )


def test_generation_queue_polls_and_enforces_idempotency(
    client_session: tuple[TestClient, Session],
) -> None:
    client, session = client_session
    project = create_project(session)
    url = f"/v1/projects/{project.id}/scripts/generate"
    headers = {"Idempotency-Key": "generation-1"}

    accepted = client.post(url, headers=headers, json={})
    repeated = client.post(url, headers=headers, json={})
    conflict = client.post(url, headers=headers, json={"brief": "A different brief"})

    assert accepted.status_code == 202
    assert repeated.status_code == 202
    assert repeated.json()["id"] == accepted.json()["id"]
    assert conflict.status_code == 409

    polled = client.get(f"/v1/jobs/{accepted.json()['id']}")
    assert polled.status_code == 200
    assert polled.json()["status"] == "queued"


def test_queued_generation_runs_review_graph_and_returns_final_version(client_session):
    client, session = client_session
    project = create_project(session)
    accepted = client.post(
        f"/v1/projects/{project.id}/scripts/generate",
        headers={"Idempotency-Key": "reviewed-generation"},
        json={},
    )
    assert accepted.status_code == 202
    job = JobRepository(session).claim_next(900)
    assert job is not None
    final = valid_script_payload()
    final["title"] = "The reviewed creator workflow"
    provider = FakeProvider(
        [
            valid_script_payload(),
            {"approved": False, "feedback": ["Make the title more specific."]},
            final,
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    polled = client.get(f"/v1/jobs/{accepted.json()['id']}")
    assert polled.json()["status"] == "completed"
    versions = client.get(f"/v1/projects/{project.id}/scripts/versions")
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["content"]["title"] == final["title"]
    assert versions.json()[0]["generation_job_id"] == accepted.json()["id"]
    assert versions.json()[0]["input_snapshot"] == job.input_snapshot
    assert provider.calls == 3


def test_script_queue_rejects_insufficient_review_budget(client_session):
    client, session = client_session
    project = create_project(session)
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        openrouter_default_model="free/model",
        openrouter_max_calls_per_operation=2,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings

    response = client.post(
        f"/v1/projects/{project.id}/scripts/generate",
        headers={"Idempotency-Key": "insufficient-budget"},
        json={},
    )

    assert response.status_code == 503
    assert "MAX_CALLS_PER_OPERATION" in response.json()["detail"]
    assert session.query(Job).count() == 0


def test_style_suggestion_queue_is_retrievable_by_job_id(
    client_session: tuple[TestClient, Session],
) -> None:
    client, _session = client_session

    accepted = client.post(
        "/v1/me/style-profile/suggestions",
        headers={"Idempotency-Key": "style-1"},
        json={"examples": [{"text": "I open with a bold point, then explain it simply."}]},
    )

    assert accepted.status_code == 202
    suggestion = client.get(f"/v1/me/style-profile/suggestions/{accepted.json()['id']}")
    assert suggestion.status_code == 200
    assert suggestion.json()["status"] == "queued"
    assert suggestion.json()["profile"] is None


def test_completed_insight_job_downloads_a_pdf(client_session: tuple[TestClient, Session]) -> None:
    client, session = client_session
    job = Job(
        owner_id="creator-a",
        type=JobType.INSIGHT_SUMMARY.value,
        idempotency_key="completed-insight-pdf",
        payload_hash="pdf-report",
        status=JobStatus.COMPLETED.value,
        stage="completed",
        input_snapshot={
            "facts": {
                "performance": [
                    {
                        "snapshot_id": "public-short",
                        "title": "Public Short",
                        "channel_title": "Public Channel",
                        "views": 1429189,
                        "likes": 52043,
                        "comments": 201,
                        "engagement_rate": 0.0366,
                        "channel_statistics": {
                            "views": 9123416180,
                            "subscribers": 44700000,
                            "videos": 271234,
                            "subscribers_hidden": False,
                        },
                        "observed_at": "2026-10-04T11:11:52Z",
                        "source": "YouTube Data API public lifetime statistics",
                    }
                ],
                "missing_data": ["Shares and retention are unavailable."],
            },
            "result": {
                "summary": "This Short has 1.4 million lifetime views.",
                "evidence_snapshot_ids": ["public-short"],
                "limitations": ["One publication does not establish causation."],
            },
        },
        routing_snapshot={},
    )
    session.add(job)
    session.commit()

    response = client.get(f"/v1/jobs/{job.id}/insight-report.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].endswith(f"creatorai-insight-{job.id}.pdf\"")
    assert response.content.startswith(b"%PDF-")


def test_assistant_revision_queues_against_the_current_script(
    client_session: tuple[TestClient, Session],
) -> None:
    client, session = client_session
    project = create_project(session)
    version = ScriptVersion(
        project_id=project.id,
        version=1,
        origin="generated",
        content={
            "hooks": [{"id": "hook-1", "text": "Stop overthinking your workflow."}],
            "selected_hook_id": "hook-1",
            "sections": [{"id": "section-1", "position": 1, "text": "Start here."}],
            "title": "A better workflow",
            "description": "A clear creator workflow.",
            "call_to_action": "Try it today.",
            "production_notes": [],
        },
        requirement_checks=[],
        warning_ids=[],
        input_snapshot={},
    )
    session.add(version)
    session.flush()
    project.current_script_version_id = version.id
    session.commit()

    accepted = client.post(
        f"/v1/projects/{project.id}/scripts/assistant/messages",
        headers={"Idempotency-Key": "assistant-1"},
        json={
            "base_version": 1,
            "message": "Make the opening more casual.",
            "target_scope": "hook",
            "target_id": "hook-1",
        },
    )

    assert accepted.status_code == 202
    assert accepted.json()["status"] == "queued"


def test_cors_allows_browser_put_requests(client_session: tuple[TestClient, Session]) -> None:
    client, _session = client_session

    response = client.options(
        "/v1/me/style-profile",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
        },
    )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
