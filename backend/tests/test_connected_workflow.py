import copy
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from workflow_fakes import SCRIPT, Alignment, Storage, Transcriber, Vision

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_db_session, get_session
from app.features.assets.router import get_storage
from app.features.media_workflow.service import MediaWorkflowService
from app.features.script_creation.jobs import JobRepository
from app.main import create_app
from app.models import Base, Project, ScriptAlignment, ScriptVersion


@pytest.fixture
def connected(tmp_path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        app = create_app()
        owner = ["creator-a"]
        settings = Settings(_env_file=None, auth_required=True)
        storage = Storage(tmp_path)
        app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator(owner[0])
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[get_db_session] = lambda: session
        app.dependency_overrides[get_storage] = lambda: storage
        saver = InMemorySaver()

        def execute():
            job = JobRepository(session).claim_next(900)
            assert job is not None
            # Construct a fresh service each time to exercise checkpoint resume.
            MediaWorkflowService(
                session, settings, storage, saver, (Transcriber(), Vision()), Alignment()
            ).execute(job)
            assert job.status != "failed", job.error
            return job

        with TestClient(app) as client:
            yield client, session, storage, owner, execute
    engine.dispose()


def create_project(client, session):
    response = client.post(
        "/v1/projects",
        json={
            "name": "Connected workflow",
            "brief": "Production guide",
            "target_platforms": ["instagram", "youtube"],
        },
    )
    assert response.status_code == 201, response.text
    project = session.get(Project, uuid.UUID(response.json()["id"]))
    script = ScriptVersion(
        project_id=project.id, version=1, origin="generated", content=SCRIPT, input_snapshot={}
    )
    session.add(script)
    session.flush()
    project.current_script_version_id = script.id
    session.commit()
    return project


def upload(client, project):
    result = client.post(
        f"/v1/projects/{project.id}/assets/upload-session",
        json={
            "filename": "source.mp4",
            "content_type": "video/mp4",
            "byte_size": 1000,
            "kind": "video",
            "tags": ["camera"],
        },
    )
    assert result.status_code == 201, result.text
    asset_id = result.json()["asset_id"]
    complete = client.post(
        f"/v1/assets/{asset_id}/complete",
        json={
            "provider_asset_id": "provider-source",
            "provider_version": "1",
        },
    )
    assert complete.status_code == 200, complete.text
    return asset_id


def test_connected_video_to_published_insights(connected):
    client, session, storage, owner, execute = connected
    project = create_project(client, session)
    root = f"/v1/projects/{project.id}"
    assert client.get(root + "/insights").json()["performance"] == []
    assert client.get(root + "/insights").json()["production"]["clips_per_source"] is None
    asset_id = upload(client, project)
    ingest = execute()
    assert ingest.type == "asset_ingestion" and ingest.status == "completed"
    analysis = client.get(f"/v1/assets/{asset_id}/analysis").json()
    assert len(analysis["transcript_segments"]) == 2
    assert len(analysis["visual_observations"]) == 1
    assert client.get(f"/v1/assets/{asset_id}/delivery").status_code == 200
    request = {"asset_id": asset_id, "max_candidates": 3}
    queued = client.post(
        root + "/clips/generate", json=request, headers={"Idempotency-Key": "clip-operation"}
    )
    assert queued.status_code == 202, queued.text
    duplicate = client.post(
        root + "/clips/generate", json=request, headers={"Idempotency-Key": "clip-operation"}
    )
    assert duplicate.json()["id"] == queued.json()["id"]
    assert (
        client.post(
            root + "/clips/generate",
            json={**request, "max_candidates": 2},
            headers={"Idempotency-Key": "clip-operation"},
        ).status_code
        == 409
    )
    job = execute()
    assert job.status == "waiting_review" and job.lease_expires_at is None
    alignments = list(session.scalars(select(ScriptAlignment)))
    assert any(a.visual_evidence and a.section_id == "section-3" for a in alignments)
    assert any(a.match_status == "unmatched" and a.section_id == "section-4" for a in alignments)
    clips = client.get(root + "/clips").json()
    assert len(clips) == 3
    clip_id = clips[0]["id"]
    version = client.get(f"/v1/clips/{clip_id}").json()["versions"][0]
    recipe = copy.deepcopy(version["recipe"])
    recipe["captions"][0]["text"] = "Creator corrected caption %{literal}"
    recipe["source_end_ms"] -= 500
    if recipe["title"]:
        recipe["title"]["end_ms"] = min(
            recipe["title"]["end_ms"], recipe["source_end_ms"] - recipe["source_start_ms"]
        )
    save = client.post(
        f"/v1/clip-candidates/{clip_id}/edit-versions",
        json={
            "base_version_id": version["id"],
            "recipe": recipe,
        },
    )
    assert save.status_code == 201, save.text
    latest = save.json()
    assert latest["revision"] == 2
    assert (
        client.post(
            f"/v1/clip-candidates/{clip_id}/edit-versions",
            json={
                "base_version_id": version["id"],
                "recipe": recipe,
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/v1/jobs/{job.id}/review", json={"edit_version_id": version["id"]}
        ).status_code
        == 409
    )
    assert (
        client.post(f"/v1/jobs/{job.id}/review", json={"edit_version_id": latest["id"]}).status_code
        == 202
    )
    assert (
        client.post(f"/v1/jobs/{job.id}/review", json={"edit_version_id": latest["id"]}).status_code
        == 409
    )
    resumed = execute()
    assert resumed.id == job.id and resumed.status == "completed"
    assert resumed.input_snapshot["result"]["selected_edit_version_id"] == latest["id"]
    export_ids = []
    for preset, platform in [("vertical", "instagram"), ("square", "youtube")]:
        payload = {
            "edit_version_id": latest["id"],
            "preset": preset,
            "platform": platform,
            "title": f"{platform} title",
            "caption": f"{platform} copy",
            "hashtags": ["#camera"],
            "fit": "crop",
        }
        result = client.post(
            f"/v1/clips/{clip_id}/exports",
            json=payload,
            headers={"Idempotency-Key": f"export-{preset}"},
        )
        assert result.status_code == 202, result.text
        exported = execute()
        render_id = exported.input_snapshot["result"]["export_id"]
        export_ids.append(render_id)
        # Re-executing a completed artifact must not upload a second copy.
        exported.status = "running"
        session.commit()
        MediaWorkflowService(session, Settings(_env_file=None), storage).execute(exported)
        assert exported.status == "completed"
        assert client.get(f"/v1/exports/{render_id}/delivery").status_code == 200
    assert len(storage.uploads) == 3  # one draft and two exports
    probes = [entry["probe"] for entry in storage.uploads.values()]
    assert all(p.has_audio and p.video_codec == "h264" for p in probes)
    assert (1080, 1920) in [(p.width, p.height) for p in probes]
    assert (1080, 1080) in [(p.width, p.height) for p in probes]
    first_version = client.get(f"/v1/clips/{clip_id}").json()["versions"][1]
    assert first_version["recipe"]["captions"][0]["text"] != recipe["captions"][0]["text"]

    def state():
        return client.get(root + "/workflow").json()

    package = {
        "title": "Guide",
        "caption": "Guide copy",
        "media_checked": True,
        "render_ids": export_ids,
    }
    assert (
        client.patch(
            root + "/workflow",
            json={
                "expected_revision": state()["revision"],
                "assets_ready": True,
                "editing_complete": True,
                "package": package,
            },
        ).status_code
        == 200
    )
    for stage in ["assets", "editing", "review", "approved", "exported"]:
        response = client.post(
            root + "/workflow/transitions",
            json={"expected_revision": state()["revision"], "stage": stage},
        )
        assert response.status_code == 200, response.text
    assert client.get(root + "/package").json()["package"]["provenance"] == "rendered_exports"
    now = datetime.now(UTC)
    for platform in ["instagram", "youtube"]:
        response = client.post(
            root + "/publications",
            json={
                "expected_revision": state()["revision"],
                "platform": platform,
                "title": platform,
            },
        )
        assert response.status_code == 201, response.text
        publication_id = response.json()["id"]
        response = client.patch(
            root + f"/publications/{publication_id}",
            json={
                "expected_revision": state()["revision"],
                "confirm_published": True,
                "published_at": (now - timedelta(days=8)).isoformat(),
                "external_url": f"https://example.test/{platform}",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["package_snapshot"]["export_id"] in export_ids
        for days, views, shares in [(2, 100, 3), (1, 200, None)]:
            response = client.post(
                f"/v1/publications/{publication_id}/performance",
                json={
                    "observed_at": (now - timedelta(days=days)).isoformat(),
                    "reporting_window_days": 7,
                    "views": views,
                    "likes": 10,
                    "comments": 2,
                    "shares": shares,
                    "source": "Manually entered fixture metrics",
                },
            )
            assert response.status_code == 201, response.text
    assert state()["stage"] == "published"
    insights = client.get(root + "/insights").json()
    assert insights["production"]["projects_completed"] == 1
    assert len(insights["performance"]) == 2  # latest snapshots, not sum of cumulative counts
    assert all(
        row["views"] == 200 and row["engagement_rate"] is None for row in insights["performance"]
    )
    assert all(r["sample_size"] == 1 for r in insights["recommendations"])

    owner[0] = "creator-b"
    for path in [
        root,
        root + "/clips",
        root + "/exports",
        root + "/insights",
        f"/v1/assets/{asset_id}/analysis",
        f"/v1/clips/{clip_id}",
        f"/v1/jobs/{job.id}",
        f"/v1/exports/{export_ids[0]}/delivery",
    ]:
        assert client.get(path).status_code == 404, path


def test_media_routes_never_trust_creator_header():
    app = create_app()
    settings = Settings(_env_file=None, auth_required=True, environment="production")
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        for path in ["/v1/projects", f"/v1/assets/{uuid.uuid4()}/analysis"]:
            response = client.get(path, headers={"X-Creator-ID": "somebody-else"})
            assert response.status_code == 401
    # Even an accidental local-demo setting cannot disable production authentication.
    settings.auth_required = False
    with TestClient(app) as client:
        assert client.get("/v1/projects").status_code == 401
