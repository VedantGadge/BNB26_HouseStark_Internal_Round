import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.features.assets.router import get_storage
from app.main import create_app
from app.models import Asset, Base, ClipCandidate, EditRender, EditVersion, Project, ScriptVersion


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator("creator-a")
        with TestClient(app) as client:
            result = client.post(
                "/v1/projects",
                json={
                    "name": "Workflow demo",
                    "brief": "Demo idea",
                    "target_platforms": ["instagram", "youtube"],
                },
            )
            project_id = result.json()["id"]
            project = session.get(Project, uuid.UUID(project_id))
            version = ScriptVersion(
                project_id=project.id,
                version=1,
                origin="creator",
                content={},
                requirement_checks=[],
                warning_ids=[],
                input_snapshot={},
            )
            session.add(version)
            session.flush()
            project.current_script_version_id = version.id
            session.commit()
            asset = Asset(
                project_id=project.id,
                owner_id=project.owner_id,
                kind="video",
                public_id="source",
                resource_type="video",
                processing_status="ready",
                duration_ms=10000,
                format="mp4",
            )
            session.add(asset)
            session.flush()
            candidate = ClipCandidate(
                asset_id=asset.id,
                source_start_ms=0,
                source_end_ms=8000,
                hook="Hook",
                transcript_text="Evidence",
                score=0.8,
            )
            session.add(candidate)
            session.flush()
            edit = EditVersion(candidate_id=candidate.id, asset_id=asset.id, revision=1, recipe={})
            session.add(edit)
            session.flush()
            for platform in project.target_platforms:
                session.add(
                    EditRender(
                        edit_version_id=edit.id,
                        asset_id=asset.id,
                        public_id=f"render-{platform}",
                        platform=platform,
                        processing_status="completed",
                        format="mp4",
                    )
                )
            session.commit()

            class Storage:
                def delivery_url(self, **kwargs):
                    return "https://example.test/render.mp4"

            app.dependency_overrides[get_storage] = lambda: Storage()
            yield client, session, f"/v1/projects/{project_id}"
    engine.dispose()


def state(client, root):
    result = client.get(root + "/workflow")
    assert result.status_code == 200, result.text
    return result.json()


def move(client, root, stage):
    return client.post(
        root + "/workflow/transitions",
        json={"expected_revision": state(client, root)["revision"], "stage": stage},
    )


def package_ready(client, root):
    result = client.patch(
        root + "/workflow",
        json={
            "expected_revision": state(client, root)["revision"],
            "assets_ready": True,
            "editing_complete": True,
            "package": {
                "title": "Original",
                "caption": "Demo copy",
                "media_checked": True,
                "render_ids": [r["id"] for r in client.get(root + "/exports").json()],
            },
        },
    )
    assert result.status_code == 200, result.text


def exported(client, root):
    package_ready(client, root)
    for stage in ("assets", "editing", "review", "approved", "exported"):
        result = move(client, root, stage)
        assert result.status_code == 200, result.text


def plan(client, root, platform="instagram"):
    result = client.post(
        root + "/publications",
        json={
            "expected_revision": state(client, root)["revision"],
            "platform": platform,
            "planned_at": "2026-10-04T10:30:00+05:30",
            "title": f"{platform} title",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def confirmation(client, root, record):
    return client.patch(
        root + "/publications/" + record["id"],
        json={
            "expected_revision": state(client, root)["revision"],
            "confirm_published": True,
            "published_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "external_url": f"https://example.com/posts/{record['platform']}",
        },
    )


def test_full_journey_and_published_snapshot(api):
    client, session, root = api
    exported(client, root)
    first = plan(client, root)
    assert first["planned_at"] == "2026-10-04T05:00:00Z"
    result = confirmation(client, root, first)
    assert result.status_code == 200, result.text
    assert result.json()["package_snapshot"]["title"] == "instagram title"
    # An unplanned target platform still prevents the project being marked fully published.
    assert state(client, root)["stage"] == "exported"
    second = plan(client, root, "youtube")
    assert confirmation(client, root, second).status_code == 200
    session.expire_all()
    assert state(client, root)["stage"] == "published"
    assert move(client, root, "editing").status_code == 409
    assert (
        client.patch(
            root + "/workflow",
            json={"expected_revision": state(client, root)["revision"], "editing_complete": False},
        ).status_code
        == 409
    )
    assert client.get(root + "/publications").json()[0]["status"] == "published"


def test_invalid_transitions_prerequisites_and_noop(api):
    client, session, root = api
    assert move(client, root, "review").status_code == 409
    before = state(client, root)
    assert move(client, root, "idea").json()["revision"] == before["revision"]
    assert move(client, root, "assets").status_code == 200
    assert move(client, root, "editing").status_code == 409
    project = session.get(Project, uuid.UUID(root.rsplit("/", 1)[1]))
    project.current_script_version_id = None
    session.commit()
    assert "Save a script" in " ".join(state(client, root)["blocking_reasons"])


def test_changes_clear_approval_and_stale_writes_do_not_overwrite(api):
    client, _, root = api
    exported(client, root)
    old = state(client, root)
    result = client.patch(
        root + "/workflow",
        json={
            "expected_revision": old["revision"],
            "package": {
                "title": "Changed",
                "caption": "New copy",
                "media_checked": True,
                "render_ids": old["package"]["render_ids"],
            },
        },
    )
    assert result.status_code == 200
    assert result.json()["stage"] == "editing"
    assert result.json()["approved_package"] is None
    assert (
        client.patch(
            root + "/workflow", json={"expected_revision": old["revision"], "assets_ready": False}
        ).status_code
        == 409
    )
    assert state(client, root)["checklist"]["assets_ready"] is True
    assert move(client, root, "exported").status_code == 409


def test_planning_does_not_publish_duplicate_or_clear_copy(api):
    client, _, root = api
    record = plan(client, root)
    assert state(client, root)["stage"] == "idea"
    assert confirmation(client, root, record).status_code == 409
    assert (
        client.post(
            root + "/publications",
            json={"expected_revision": state(client, root)["revision"], "platform": "instagram"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/publications",
            json={"expected_revision": state(client, root)["revision"], "platform": "tiktok"},
        ).status_code
        == 422
    )
    patched = client.patch(
        root + "/publications/" + record["id"],
        json={"expected_revision": state(client, root)["revision"], "planned_at": None},
    )
    assert patched.json()["status"] == "draft"
    assert patched.json()["supporting_copy"]["title"] == "instagram title"


@pytest.mark.parametrize(
    "fields",
    [
        {"planned_at": "2026-10-04T10:30:00"},
        {"confirm_published": True},
        {
            "confirm_published": True,
            "published_at": "2099-01-01T00:00:00Z",
            "external_url": "https://example.com/post",
        },
        {
            "confirm_published": True,
            "published_at": "2020-01-01T00:00:00Z",
            "external_url": "javascript:alert(1)",
        },
        {"external_url": "https://example.com/post"},
    ],
)
def test_invalid_dates_and_explicit_confirmation(api, fields):
    client, _, root = api
    record = plan(client, root)
    assert (
        client.patch(
            root + "/publications/" + record["id"],
            json={"expected_revision": state(client, root)["revision"], **fields},
        ).status_code
        == 422
    )


def test_empty_updates_are_rejected_without_consuming_a_revision(api):
    client, _, root = api
    before = state(client, root)["revision"]
    assert client.patch(root + "/workflow", json={"expected_revision": before}).status_code == 422
    assert state(client, root)["revision"] == before
    record = plan(client, root)
    before = state(client, root)["revision"]
    assert (
        client.patch(
            root + "/publications/" + record["id"], json={"expected_revision": before}
        ).status_code
        == 422
    )
    assert state(client, root)["revision"] == before


def test_owner_scope_missing_media_and_safe_delivery(api):
    client, session, root = api
    assert client.get(root + "/workflow/media").status_code == 409
    package_ready(client, root)
    media = client.get(root + "/workflow/media", follow_redirects=False)
    assert media.status_code == 307
    assert media.headers["location"] == "https://example.test/render.mp4"
    for render in session.query(EditRender).all():
        render.processing_status = "failed"
    session.commit()
    for stage in ("assets", "editing"):
        assert move(client, root, stage).status_code == 200
    assert move(client, root, "review").status_code == 409
    assert client.get(root + "/workflow/media").status_code == 409
    client.app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator("creator-b")
    for suffix in ("", "/workflow", "/publications", "/workflow/media"):
        assert client.get(root + suffix).status_code == 404
    assert (
        client.patch(
            root + "/workflow", json={"expected_revision": 1, "assets_ready": True}
        ).status_code
        == 404
    )


def test_confirmation_is_repeatable_without_new_timestamp_or_record(api):
    client, _, root = api
    exported(client, root)
    record = plan(client, root)
    first = confirmation(client, root, record)
    assert first.status_code == 200
    revision = state(client, root)["revision"]
    result = client.patch(
        root + "/publications/" + record["id"],
        json={
            "expected_revision": revision,
            "confirm_published": True,
            "published_at": first.json()["published_at"],
            "external_url": first.json()["external_url"],
        },
    )
    assert result.status_code == 200
    assert state(client, root)["revision"] == revision
    assert len(client.get(root + "/publications").json()) == 1
