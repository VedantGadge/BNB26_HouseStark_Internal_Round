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
from app.features.youtube.models import YouTubeConnection, YouTubeOAuthAttempt
from app.features.youtube.provider import SCOPES, YouTubeProvider, token_cipher, video_id_from_url
from app.models import PerformanceSnapshot, Project, Publication

router = APIRouter()


class ConnectInput(BaseModel):
    project_id: UUID


class CallbackInput(BaseModel):
    state: str = Field(min_length=20, max_length=200)
    code: str = Field(min_length=1, max_length=4096)


class SyncInput(BaseModel):
    reporting_window_days: int = Field(default=7, ge=1, le=365)


def get_provider(settings: Settings = Depends(get_settings)) -> YouTubeProvider:
    return YouTubeProvider(settings)


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
