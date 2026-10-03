import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Project(Base):
    """Initial durable root entity; child entities follow the same owner-scoped pattern."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(120))
    brief: Mapped[str] = mapped_column(Text)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_platforms: Mapped[list[str]] = mapped_column(JSON, default=list)
    workflow_stage: Mapped[str] = mapped_column(String(64), default="idea", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Compatibility exports let shared code import one domain module while each feature
# owns its implementation model in a focused folder.
from app.features.assets.models import Asset  # noqa: E402
from app.features.clip_generation.models import ClipCandidate  # noqa: E402
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation  # noqa: E402
from app.features.script_alignment.models import ScriptAlignment  # noqa: E402

__all__ = [
    "Asset", "Base", "ClipCandidate", "Project", "ScriptAlignment",
    "TranscriptSegment", "VisualObservation",
]
