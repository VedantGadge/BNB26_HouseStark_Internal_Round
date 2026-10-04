import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlatformExport(Base):
    """A rendered platform variant with an immutable recipe and copy snapshot."""

    __tablename__ = "platform_exports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    render_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("edit_renders.id"), nullable=True, unique=True
    )
    edit_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("edit_versions.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    preset: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    derived_recipe: Mapped[dict[str, object]] = mapped_column(JSON)
    supporting_copy: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list)
    public_id: Mapped[str] = mapped_column(String(500), unique=True)
    provider_asset_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    format: Mapped[str] = mapped_column(String(32), default="mp4")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
