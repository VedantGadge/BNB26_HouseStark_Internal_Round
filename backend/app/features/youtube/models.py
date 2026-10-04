from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class YouTubeConnection(Base):
    __tablename__ = "youtube_connections"

    owner_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(128))
    channel_title: Mapped[str] = mapped_column(String(255))
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class YouTubeOAuthAttempt(Base):
    __tablename__ = "youtube_oauth_attempts"

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("projects.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
