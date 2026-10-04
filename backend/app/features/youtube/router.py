import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.content_workflow.service import owned_project
from app.features.media_workflow.router import Key, enqueue
from app.features.script_creation.routing import require_openrouter_configuration, routing_snapshot
from app.features.youtube.models import YouTubeConnection, YouTubeOAuthAttempt
from app.features.youtube.provider import (
    SCOPES,
    YouTubeProvider,
    public_video_metrics,
    token_cipher,
    video_id_from_url,
)
from app.models import PerformanceSnapshot, Project, Publication
from app.schemas import JobResponse, JobType

router = APIRouter()


class ConnectInput(BaseModel):
    project_id: UUID


class CallbackInput(BaseModel):
    state: str = Field(min_length=20, max_length=200)
    code: str = Field(min_length=1, max_length=4096)


class SyncInput(BaseModel):
    reporting_window_days: int = Field(default=7, ge=1, le=365)


class PublicVideoInput(BaseModel):
    url: str = Field(min_length=1, max_length=2_048)


def public_insight_facts(metrics: dict) -> dict:
    """Make a provenance-preserving, immutable fact set for one public video."""
    snapshot_id = f"youtube-public:{metrics['video_id']}:{metrics['observed_at']}"
    return {
        "project_id": None,
        "scope": "public_youtube_video",
        "production": {},
        "performance": [
            {
                "snapshot_id": snapshot_id,
                "publication_id": metrics["video_id"],
                "project_id": None,
                "platform": "youtube",
                "reporting_window_days": None,
                "reporting_basis": "youtube_public_lifetime",
                "observed_at": metrics["observed_at"],
                "published_at": metrics["published_at"],
                "source": metrics["source"],
                "title": metrics["title"],
                "channel_title": metrics["channel_title"],
                "canonical_url": metrics["canonical_url"],
                "duration": metrics["duration"],
                "views": metrics["views"],
                "likes": metrics["likes"],
                "comments": metrics["comments"],
                "shares": None,
                "retention": None,
                "engagement_rate": metrics["engagement_rate"],
                "favorites": metrics["favorites"],
                "channel_statistics": metrics["channel_statistics"],
                "metadata": metrics["metadata"],
            }
        ],
        "recommendations": [],
        "missing_data": [
            "Public YouTube statistics are current lifetime totals, not a reporting window.",
            "Public YouTube data does not include shares, retention, audience demographics, "
            "or historical daily performance.",
            "One video cannot establish what caused its performance.",
        ],
    }


def get_provider(settings: Settings = Depends(get_settings)) -> YouTubeProvider:
    return YouTubeProvider(settings)


@router.post("/youtube/public/metrics")
def public_metrics(
    payload: PublicVideoInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
):
    del creator  # Keep the server API key and its quota behind application authentication.
    return public_video_metrics(settings, payload.url)


@router.post("/youtube/public/insights", response_model=JobResponse, status_code=202)
def summarize_public_metrics(
    payload: PublicVideoInput,
    idempotency_key: Key,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Queue an AI explanation from a fresh, server-fetched public metrics snapshot."""
    require_openrouter_configuration(settings)
    metrics = public_video_metrics(settings, payload.url)
    return enqueue(
        session,
        creator,
        None,
        JobType.INSIGHT_SUMMARY,
        idempotency_key,
        {"facts": public_insight_facts(metrics)},
        routing_snapshot(settings),
    )


@router.get("/me/youtube")
def connection_status(
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    try:
        token_cipher(settings)
        configured = True
    except HTTPException:
        configured = False
    record = session.get(YouTubeConnection, creator.id)
    return {
        "configured": configured,
        "public_lookup_configured": settings.youtube_public_api_key is not None,
        "connected": record is not None,
        "channel_id": record.channel_id if record else None,
        "channel_title": record.channel_title if record else None,
    }


@router.post("/me/youtube/authorize")
def authorize(
    payload: ConnectInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    owned_project(session, creator.id, payload.project_id)
    token_cipher(settings)
    state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.execute(
        delete(YouTubeOAuthAttempt)
        .where(
            (YouTubeOAuthAttempt.owner_id == creator.id) | (YouTubeOAuthAttempt.expires_at < now)
        )
        .execution_options(synchronize_session="fetch")
    )
    session.add(
        YouTubeOAuthAttempt(
            state_hash=hashlib.sha256(state.encode()).hexdigest(),
            owner_id=creator.id,
            project_id=payload.project_id,
            expires_at=now + timedelta(minutes=10),
        )
    )
    session.commit()
    return {
        "state": state,
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": settings.youtube_client_id,
                "redirect_uri": settings.youtube_redirect_uri,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "access_type": "offline",
                "prompt": "consent select_account",
                "state": state,
            }
        ),
    }


@router.post("/me/youtube/callback")
def callback(
    payload: CallbackInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    provider: YouTubeProvider = Depends(get_provider),
):
    # Consume once, atomically, and bind to the authenticated creator. No public callback
    # can attach an account by guessing a creator or project identifier.
    project_id = session.execute(
        delete(YouTubeOAuthAttempt)
        .where(
            YouTubeOAuthAttempt.state_hash == hashlib.sha256(payload.state.encode()).hexdigest(),
            YouTubeOAuthAttempt.owner_id == creator.id,
            YouTubeOAuthAttempt.expires_at > datetime.now(UTC),
        )
        .returning(YouTubeOAuthAttempt.project_id)
        .execution_options(synchronize_session="fetch")
    ).scalar_one_or_none()
    session.commit()
    if project_id is None:
        raise HTTPException(409, "YouTube connection expired or was already used. Connect again.")
    owned_project(session, creator.id, project_id)
    tokens = provider.exchange_code(payload.code)
    channel = provider.channel(tokens["access_token"])
    record = session.get(YouTubeConnection, creator.id)
    if record is None:
        record = YouTubeConnection(owner_id=creator.id)
        session.add(record)
    record.channel_id = channel["id"]
    record.channel_title = channel["title"]
    record.encrypted_refresh_token = provider.encrypt(tokens["refresh_token"])
    record.connected_at = datetime.now(UTC)
    session.commit()
    return {"project_id": str(project_id), "channel_title": record.channel_title}


@router.delete("/me/youtube", status_code=204)
def disconnect(
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    record = session.get(YouTubeConnection, creator.id)
    encrypted_token = record.encrypted_refresh_token if record else None
    if record:
        session.delete(record)
    session.execute(delete(YouTubeOAuthAttempt).where(YouTubeOAuthAttempt.owner_id == creator.id))
    session.commit()
    if encrypted_token:
        try:
            YouTubeProvider(settings).revoke(encrypted_token)
        except HTTPException:
            pass
    return Response(status_code=204)


@router.post("/publications/{publication_id}/performance/youtube")
def sync_performance(
    publication_id: UUID,
    payload: SyncInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    provider: YouTubeProvider = Depends(get_provider),
):
    publication = session.scalar(
        select(Publication)
        .join(Project)
        .where(
            Publication.id == publication_id,
            Project.owner_id == creator.id,
        )
    )
    if publication is None:
        raise HTTPException(404, "Publication not found.")
    if publication.platform != "youtube" or publication.status != "published":
        raise HTTPException(409, "Confirm a YouTube publication before syncing its metrics.")
    connection = session.scalar(
        select(YouTubeConnection)
        .where(
            YouTubeConnection.owner_id == creator.id,
        )
        .with_for_update()
    )
    if connection is None:
        raise HTTPException(409, "Connect your YouTube channel first.")
    video_id = video_id_from_url(publication.external_url)
    access = provider.refresh_access(connection.encrypted_refresh_token)
    facts = provider.performance(
        access, connection.channel_id, video_id, payload.reporting_window_days
    )
    snapshot = PerformanceSnapshot(publication_id=publication.id, **facts)
    session.add(snapshot)
    session.commit()
    return {
        "id": str(snapshot.id),
        "source": snapshot.source,
        "reporting_window_days": snapshot.reporting_window_days,
        "views": snapshot.views,
        "likes": snapshot.likes,
        "comments": snapshot.comments,
        "shares": snapshot.shares,
    }
