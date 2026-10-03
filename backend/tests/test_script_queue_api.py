from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.main import create_app
from app.models import Base, ScriptVersion
from app.repositories import ProjectRepository
from app.schemas import Platform, ProjectCreate


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
    settings = Settings(openrouter_api_key="test-key", openrouter_default_model="free/model")

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
