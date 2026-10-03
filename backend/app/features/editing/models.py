import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EditVersion(Base):
    """An immutable edit recipe derived from one grounded clip candidate."""

    __tablename__ = "edit_versions"
    __table_args__ = (
        UniqueConstraint("candidate_id", "revision", name="uq_edit_versions_candidate_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clip_candidates.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("edit_versions.id", ondelete="SET NULL"), nullable=True
    )
    author_type: Mapped[str] = mapped_column(String(32), default="assistant")
    recipe: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EditRender(Base):
    """One verified MP4 artifact produced from an immutable edit version."""

    __tablename__ = "edit_renders"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ai_script_jobs.id"), nullable=True, unique=True
    )
    preset_name: Mapped[str] = mapped_column(String(32), default="vertical")
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    supporting_copy: Mapped[dict] = mapped_column(JSON, default=dict)
    recipe_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    edit_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("edit_versions.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
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
