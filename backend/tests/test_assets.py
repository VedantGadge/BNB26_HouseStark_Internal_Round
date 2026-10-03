from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db_session
from app.main import app
from app.models import Base, Project
from app.routes.assets import get_storage


class FakeStorage:
    def create_upload_session(self, *, public_id: str, resource_type: str) -> dict[str, str | int]:
        return {
            "cloud_name": "demo-cloud",
            "api_key": "public-key",
            "resource_type": resource_type,
            "upload_url": f"https://example.test/{resource_type}/upload",
            "public_id": public_id,
            "delivery_type": "authenticated",
            "overwrite": False,
            "timestamp": 1_700_000_000,
            "signature": "server-generated-signature",
        }

    def get_asset_metadata(self, *, public_id: str, resource_type: str) -> dict[str, object]:
        return {
            "asset_id": "cloudinary-asset-1",
            "version": 7,
            "public_id": public_id,
            "resource_type": resource_type,
            "type": "authenticated",
            "format": "mp4",
            "bytes": 12_345,
            "width": 1920,
            "height": 1080,
            "duration": 12.34,
        }


@pytest.fixture
def asset_client() -> Generator[tuple[TestClient, UUID], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = "asset-test-owner"
    project_id = uuid4()

    with session_factory() as session:
        session.add(
            Project(
                id=project_id,
                owner_id=owner_id,
                name="Asset test project",
                brief="Validate the upload flow.",
                target_platforms=[],
            )
        )
        session.commit()

    def override_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    with TestClient(app) as client:
        yield client, project_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_video_upload_session_completion_and_listing(
    asset_client: tuple[TestClient, UUID],
) -> None:
    client, project_id = asset_client
    headers = {"X-Creator-ID": "asset-test-owner"}

    session_response = client.post(
        f"/v1/projects/{project_id}/assets/upload-session",
        headers=headers,
        json={
            "filename": "creator-intro.mp4",
            "content_type": "video/mp4",
            "byte_size": 12_345,
            "kind": "video",
            "tags": ["intro"],
        },
    )

    assert session_response.status_code == 201
    upload_session = session_response.json()
    assert upload_session["resource_type"] == "video"
    assert upload_session["delivery_type"] == "authenticated"
    assert upload_session["overwrite"] is False
    assert upload_session["signature"] == "server-generated-signature"
    assert "secret" not in upload_session

    completion_response = client.post(
        f"/v1/assets/{upload_session['asset_id']}/complete",
        headers=headers,
        json={"provider_asset_id": "cloudinary-asset-1", "provider_version": "7"},
    )

    assert completion_response.status_code == 200
    completed_asset = completion_response.json()
    assert completed_asset["processing_status"] == "uploaded"
    assert completed_asset["duration_ms"] == 12_340
    assert completed_asset["tags"] == ["intro"]

    list_response = client.get(f"/v1/projects/{project_id}/assets", headers=headers)
    assert list_response.status_code == 200
    assert [asset["id"] for asset in list_response.json()] == [upload_session["asset_id"]]


def test_upload_session_rejects_mismatched_media_type(
    asset_client: tuple[TestClient, UUID],
) -> None:
    client, project_id = asset_client

    response = client.post(
        f"/v1/projects/{project_id}/assets/upload-session",
        headers={"X-Creator-ID": "asset-test-owner"},
        json={
            "filename": "not-a-video.jpg",
            "content_type": "image/jpeg",
            "byte_size": 512,
            "kind": "video",
        },
    )

    assert response.status_code == 422
