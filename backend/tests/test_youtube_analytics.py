import copy
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.youtube import provider as youtube
from app.features.youtube.models import YouTubeConnection, YouTubeOAuthAttempt
from app.main import create_app
from app.models import Base, Job, PerformanceSnapshot, Project, Publication

VIDEO_ID = "dQw4w9WgXcQ"
REPORT = {
    "columnHeaders": [{"name": name} for name in ["day", "shares", "views", "comments", "likes"]],
    "rows": [["2025-01-31", 2, 100, 3, 10], ["2025-02-01", 1, 50, 1, 5]],
}


@pytest.fixture
def connected(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    settings = Settings(
        _env_file=None,
        youtube_client_id="test-client",
        youtube_client_secret="test-client-secret",
        youtube_token_encryption_key=Fernet.generate_key().decode(),
    )
    owner = ["creator-a"]
    remote = {
        "requests": [],
        "report": copy.deepcopy(REPORT),
        "channel": "channel-a",
        "token_status": 200,
        "report_status": 200,
        "published_at": "2025-02-01T01:00:00Z",
        "scope": " ".join(youtube.SCOPES),
    }

    def request(method, url, **kwargs):
        remote["requests"].append((method, url, kwargs))
        if url.endswith("/token"):
            if remote["token_status"] != 200:
                return httpx.Response(remote["token_status"], json={"error": "invalid_grant"})
            return httpx.Response(
                200,
                json={
                    "access_token": "secret-access",
                    "refresh_token": "secret-refresh",
                    "scope": remote["scope"],
                },
            )
        if url.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "channel-a",
                            "snippet": {
                                "title": "My channel",
                            },
                        }
                    ]
                },
            )
        if url.endswith("/videos"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": VIDEO_ID,
                            "snippet": {
                                "channelId": remote["channel"],
                                "publishedAt": remote["published_at"],
                            },
                        }
                    ]
                },
            )
        if url.endswith("/reports"):
            return httpx.Response(remote["report_status"], json=remote["report"])
        raise AssertionError("Unexpected Google endpoint")

    monkeypatch.setattr(youtube.httpx, "request", request)
    monkeypatch.setattr(youtube.httpx, "post", lambda *args, **kwargs: httpx.Response(200))
    with Session(engine, expire_on_commit=False) as session:
        project = Project(
            owner_id=owner[0], name="YouTube project", brief="Test", target_platforms=["youtube"]
        )
        session.add(project)
        session.flush()
        publication = Publication(
            project_id=project.id,
            platform="youtube",
            status="published",
            published_at=datetime(2025, 2, 1, 1, tzinfo=UTC),
            external_url=f"https://www.youtube.com/shorts/{VIDEO_ID}",
            supporting_copy={"title": "My video"},
        )
        session.add(publication)
        session.commit()
        app = create_app()
        app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator(owner[0])
        app.dependency_overrides[get_session] = lambda: session
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app) as client:
            yield client, session, project, publication, owner, remote, settings
    engine.dispose()


def begin(fixture):
    client, _, project, *_ = fixture
    response = client.post("/v1/me/youtube/authorize", json={"project_id": str(project.id)})
    assert response.status_code == 200, response.text
    return response.json()


def connect(fixture):
    state = begin(fixture)["state"]
    response = fixture[0].post("/v1/me/youtube/callback", json={"state": state, "code": "code"})
    assert response.status_code == 200, response.text
    return state


def sync(fixture, days=7):
    return fixture[0].post(
        f"/v1/publications/{fixture[3].id}/performance/youtube",
        json={"reporting_window_days": days},
    )


def test_connect_scopes_encryption_status_and_replay(connected):
    client, session, project, _, _, remote, settings = connected
    started = begin(connected)
    url = urlparse(started["authorization_url"])
    query = parse_qs(url.query)
    assert url.hostname == "accounts.google.com"
    assert query["scope"] == [" ".join(youtube.SCOPES)]
    assert query["access_type"] == ["offline"]
    assert query["redirect_uri"] == [settings.youtube_redirect_uri]
    attempt = session.scalar(select(YouTubeOAuthAttempt))
    assert started["state"] not in attempt.state_hash
    payload = {"state": started["state"], "code": "code"}
    result = client.post("/v1/me/youtube/callback", json=payload)
    assert result.json()["project_id"] == str(project.id)
    record = session.get(YouTubeConnection, "creator-a")
    assert "secret-refresh" not in record.encrypted_refresh_token
    assert (
        youtube.YouTubeProvider(settings).decrypt(record.encrypted_refresh_token)
        == "secret-refresh"
    )
    status = client.get("/v1/me/youtube").json()
    assert status == {
        "configured": True,
        "public_lookup_configured": False,
        "connected": True,
        "channel_id": "channel-a",
        "channel_title": "My channel",
    }
    assert "secret-" not in str(result.json()) + str(status)
    before = len(remote["requests"])
    assert client.post("/v1/me/youtube/callback", json=payload).status_code == 409
    assert len(remote["requests"]) == before


def test_public_video_metrics_returns_current_lifetime_counts(monkeypatch):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "public-channel",
                            "statistics": {
                                "viewCount": "20000",
                                "subscriberCount": "500",
                                "videoCount": "100",
                                "hiddenSubscriberCount": False,
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": VIDEO_ID,
                        "snippet": {
                            "title": "Public Short",
                            "channelId": "public-channel",
                            "channelTitle": "Public channel",
                            "publishedAt": "2025-02-01T01:00:00Z",
                        },
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "90",
                            "commentCount": "10",
                        },
                        "contentDetails": {"duration": "PT42S"},
                    }
                ]
            },
        )

    monkeypatch.setattr(youtube.httpx, "get", get)
    result = youtube.public_video_metrics(
        Settings(_env_file=None, youtube_public_api_key="public-api-key"),
        f"https://youtube.com/shorts/{VIDEO_ID}?si=tracking",
    )
    assert result == {
        "video_id": VIDEO_ID,
        "canonical_url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
        "title": "Public Short",
        "channel_id": "public-channel",
        "channel_title": "Public channel",
        "published_at": "2025-02-01T01:00:00+00:00",
        "duration": "PT42S",
        "views": 1000,
        "likes": 90,
        "comments": 10,
        "favorites": None,
        "engagement_rate": 0.1,
        "channel_statistics": {
            "views": 20000,
            "subscribers": 500,
            "videos": 100,
            "subscribers_hidden": False,
        },
        "metadata": {
            "category_id": None,
            "live_broadcast_content": None,
            "definition": None,
            "dimension": None,
            "caption_available": False,
            "licensed_content": None,
            "projection": None,
            "embeddable": None,
            "public_stats_viewable": None,
            "made_for_kids": None,
            "topic_categories": [],
            "concurrent_viewers": None,
        },
        "source": "YouTube Data API public lifetime statistics",
        "observed_at": result["observed_at"],
    }
    assert calls[0][0] == "https://www.googleapis.com/youtube/v3/videos"
    assert calls[0][1]["params"]["part"] == (
        "snippet,statistics,contentDetails,status,topicDetails,liveStreamingDetails"
    )
    assert calls[0][1]["params"]["id"] == VIDEO_ID
    assert calls[0][1]["params"]["key"] == "public-api-key"
    assert calls[1][0] == "https://www.googleapis.com/youtube/v3/channels"
    assert calls[1][1]["params"]["id"] == "public-channel"


@pytest.mark.parametrize(
    "response,status",
    [
        (httpx.Response(200, json={"items": []}), 404),
        (httpx.Response(403, json={"error": {}}), 503),
        (httpx.Response(429, json={"error": {}}), 503),
        (httpx.Response(200, json={"items": [{"id": VIDEO_ID}]}), 502),
    ],
)
def test_public_video_metrics_rejects_unavailable_or_invalid_data(monkeypatch, response, status):
    monkeypatch.setattr(youtube.httpx, "get", lambda *args, **kwargs: response)
    with pytest.raises(HTTPException) as error:
        youtube.public_video_metrics(
            Settings(_env_file=None, youtube_public_api_key="public-api-key"),
            f"https://youtu.be/{VIDEO_ID}",
        )
    assert error.value.status_code == status


def test_public_video_metrics_requires_a_separate_server_key():
    with pytest.raises(HTTPException) as error:
        youtube.public_video_metrics(Settings(_env_file=None), f"https://youtu.be/{VIDEO_ID}")
    assert error.value.status_code == 503


def test_public_short_metrics_queue_an_ai_report_with_frozen_api_evidence(connected, monkeypatch):
    client, session, _, _, _, _, _ = connected

    def get(url, **kwargs):
        if url.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "public-channel",
                            "statistics": {
                                "viewCount": "20000",
                                "subscriberCount": "500",
                                "videoCount": "100",
                                "hiddenSubscriberCount": False,
                            },
                        }
                    ]
                },
            )
        assert url == "https://www.googleapis.com/youtube/v3/videos"
        assert kwargs["params"]["id"] == VIDEO_ID
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": VIDEO_ID,
                        "snippet": {
                            "title": "Public Short",
                            "channelId": "public-channel",
                            "channelTitle": "Public channel",
                            "publishedAt": "2025-02-01T01:00:00Z",
                        },
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "90",
                            "commentCount": "10",
                        },
                        "contentDetails": {"duration": "PT42S"},
                    }
                ]
            },
        )

    monkeypatch.setattr(youtube.httpx, "get", get)
    configured = Settings(
        _env_file=None,
        youtube_public_api_key="public-api-key",
        openrouter_api_key="test-openrouter-key",
    )
    client.app.dependency_overrides[get_settings] = lambda: configured
    response = client.post(
        "/v1/youtube/public/insights",
        json={"url": f"https://youtube.com/shorts/{VIDEO_ID}"},
        headers={"Idempotency-Key": "public-short-report"},
    )

    assert response.status_code == 202, response.text
    job = session.get(Job, UUID(response.json()["id"]))
    assert job is not None and job.type == "insight_summary"
    facts = job.input_snapshot["facts"]
    assert facts["scope"] == "public_youtube_video"
    assert facts["performance"] == [
        {
            "snapshot_id": facts["performance"][0]["snapshot_id"],
            "publication_id": VIDEO_ID,
            "project_id": None,
            "platform": "youtube",
            "reporting_window_days": None,
            "reporting_basis": "youtube_public_lifetime",
            "observed_at": facts["performance"][0]["observed_at"],
            "published_at": "2025-02-01T01:00:00+00:00",
            "source": "YouTube Data API public lifetime statistics",
            "title": "Public Short",
            "channel_title": "Public channel",
            "canonical_url": f"https://www.youtube.com/watch?v={VIDEO_ID}",
            "duration": "PT42S",
            "views": 1000,
            "likes": 90,
            "comments": 10,
            "shares": None,
            "retention": None,
            "engagement_rate": 0.1,
            "favorites": None,
            "channel_statistics": {
                "views": 20000,
                "subscribers": 500,
                "videos": 100,
                "subscribers_hidden": False,
            },
            "metadata": {
                "category_id": None,
                "live_broadcast_content": None,
                "definition": None,
                "dimension": None,
                "caption_available": False,
                "licensed_content": None,
                "projection": None,
                "embeddable": None,
                "public_stats_viewable": None,
                "made_for_kids": None,
                "topic_categories": [],
                "concurrent_viewers": None,
            },
        }
    ]
    assert facts["missing_data"][-1] == "One video cannot establish what caused its performance."


def test_oauth_owner_expiry_and_no_public_callback(connected):
    client, session, project, _, owner, remote, _ = connected
    state = begin(connected)["state"]
    owner[0] = "creator-b"
    assert (
        client.post("/v1/me/youtube/authorize", json={"project_id": str(project.id)}).status_code
        == 404
    )
    payload = {"state": state, "code": "code"}
    assert client.post("/v1/me/youtube/callback", json=payload).status_code == 409
    assert not remote["requests"]
    owner[0] = "creator-a"
    attempt = session.scalar(select(YouTubeOAuthAttempt))
    attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert client.post("/v1/me/youtube/callback", json=payload).status_code == 409
    assert not remote["requests"]
    client.app.dependency_overrides.pop(get_current_creator)
    assert client.post("/v1/me/youtube/callback", json=payload).status_code == 401


def test_sync_saves_actual_window_and_updates_existing_insights(connected):
    client, session, project, publication, _, remote, _ = connected
    connect(connected)
    # YouTube's Jan 31 publication day is different from the UTC Feb 1 date.
    response = sync(connected)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["reporting_window_days"] == 2
    assert (result["views"], result["likes"], result["comments"], result["shares"]) == (
        150,
        15,
        4,
        3,
    )
    assert "2025-01-31 to 2025-02-01 (Pacific)" in result["source"]
    report_request = remote["requests"][-1][2]["params"]
    assert report_request["startDate"] == "2025-01-31"
    assert report_request["endDate"] == "2025-02-06"
    assert report_request["filters"] == f"video=={VIDEO_ID}"
    assert report_request["ids"] == "channel==channel-a"
    remote["report"]["rows"][0][2] = 200
    assert sync(connected).status_code == 200
    assert len(list(session.scalars(select(PerformanceSnapshot)))) == 2
    insights = client.get(f"/v1/projects/{project.id}/insights").json()
    assert len(insights["performance"]) == 1  # latest cumulative snapshot only
    row = insights["performance"][0]
    assert row["views"] == 250 and row["engagement_rate"] == 22 / 250
    assert row["reporting_basis"] == "youtube_calendar_days"
    assert session.scalar(select(PerformanceSnapshot)).retention is None
    # Manual windows are distinct evidence, not silently overwritten or compared together.
    session.add(
        PerformanceSnapshot(
            publication_id=publication.id,
            observed_at=datetime.now(UTC),
            reporting_window_days=2,
            views=900,
            likes=30,
            comments=2,
            shares=1,
            source="Manual entry",
        )
    )
    session.commit()
    insights = client.get(f"/v1/projects/{project.id}/insights").json()
    assert len(insights["performance"]) == 2
    assert len(insights["recommendations"]) == 2
    assert all(row["sample_size"] == 1 for row in insights["recommendations"])


def test_sync_requires_connection_owner_platform_and_channel(connected):
    client, session, _, publication, owner, remote, _ = connected
    assert sync(connected).status_code == 409
    assert not remote["requests"]
    connect(connected)
    owner[0] = "creator-b"
    assert client.get("/v1/me/youtube").json()["connected"] is False
    assert sync(connected).status_code == 404
    owner[0] = "creator-a"
    publication.platform = "instagram"
    session.commit()
    assert sync(connected).status_code == 409
    publication.platform = "youtube"
    publication.status = "planned"
    session.commit()
    assert sync(connected).status_code == 409
    publication.status = "published"
    session.commit()
    remote["channel"] = "another-channel"
    assert sync(connected).status_code == 409
    assert not any(url.endswith("/reports") for _, url, _ in remote["requests"])
    assert session.scalar(select(PerformanceSnapshot)) is None


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("empty", 409),
        ("missing_metric", 502),
        ("negative", 502),
        ("duplicate_day", 502),
        ("out_of_range", 502),
        ("revoked", 409),
        ("forbidden", 403),
        ("rate_limited", 503),
        ("new_video", 409),
    ],
)
def test_bad_or_unavailable_data_does_not_create_observations(connected, kind, expected):
    _, session, _, _, _, remote, _ = connected
    connect(connected)
    if kind == "empty":
        remote["report"]["rows"] = []
    elif kind == "missing_metric":
        remote["report"]["columnHeaders"][1]["name"] = "unknown"
    elif kind == "negative":
        remote["report"]["rows"][0][2] = -1
    elif kind == "duplicate_day":
        remote["report"]["rows"][1][0] = "2025-01-31"
    elif kind == "out_of_range":
        remote["report"]["rows"][1][0] = "2025-05-01"
    elif kind == "revoked":
        remote["token_status"] = 400
    elif kind == "forbidden":
        remote["report_status"] = 403
    elif kind == "rate_limited":
        remote["report_status"] = 429
    elif kind == "new_video":
        remote["published_at"] = datetime.now(UTC).isoformat()
    response = sync(connected)
    assert response.status_code == expected, response.text
    assert "secret-" not in response.text
    assert session.scalar(select(PerformanceSnapshot)) is None


def test_denied_scope_configuration_and_disconnect(connected):
    client, session, _, _, _, remote, settings = connected
    remote["scope"] = youtube.SCOPES[0]
    state = begin(connected)["state"]
    assert (
        client.post("/v1/me/youtube/callback", json={"state": state, "code": "code"}).status_code
        == 409
    )
    assert session.get(YouTubeConnection, "creator-a") is None
    remote["scope"] = " ".join(youtube.SCOPES)
    connect(connected)
    pending = begin(connected)
    assert client.delete("/v1/me/youtube").status_code == 204
    assert session.get(YouTubeConnection, "creator-a") is None
    assert session.scalar(select(YouTubeOAuthAttempt)) is None
    assert (
        client.post(
            "/v1/me/youtube/callback", json={"state": pending["state"], "code": "code"}
        ).status_code
        == 409
    )
    settings.youtube_token_encryption_key = None
    assert client.get("/v1/me/youtube").json()["configured"] is False
    assert (
        client.post(
            "/v1/me/youtube/authorize", json={"project_id": str(connected[2].id)}
        ).status_code
        == 503
    )


@pytest.mark.parametrize(
    "url",
    [
        f"https://youtu.be/{VIDEO_ID}?t=10",
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/shorts/{VIDEO_ID}",
        f"https://m.youtube.com/live/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
    ],
)
def test_supported_video_urls(url):
    assert youtube.video_id_from_url(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        None,
        "",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://youtube.com@evil.example/watch?v=dQw4w9WgXcQ",
        "file:///etc/passwd",
        "https://youtube.com/watch?v=bad",
        "https://youtu.be/dQw4w9WgXcQ/more",
    ],
)
def test_unsupported_urls_are_rejected(url):
    with pytest.raises(HTTPException) as error:
        youtube.video_id_from_url(url)
    assert error.value.status_code == 422
