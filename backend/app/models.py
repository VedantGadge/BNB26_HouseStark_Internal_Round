import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
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


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(TimestampedModel, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(120))
    brief: Mapped[str] = mapped_column(Text)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_platforms: Mapped[list[str]] = mapped_column(JSON, default=list)
    workflow_stage: Mapped[str] = mapped_column(String(64), default="idea", index=True)
    current_script_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    workflow_revision: Mapped[int] = mapped_column(Integer, default=1)
    workflow_data: Mapped[dict] = mapped_column(JSON, default=dict)


class Publication(TimestampedModel, Base):
    __tablename__ = "content_publications"
    __table_args__ = (UniqueConstraint("project_id", "platform", name="uq_publication_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    package_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    supporting_copy: Mapped[dict] = mapped_column(JSON, default=dict)


class StyleProfileRevision(TimestampedModel, Base):
    __tablename__ = "ai_script_style_profile_revisions"
    __table_args__ = (
        UniqueConstraint("owner_id", "revision", name="uq_ai_script_style_profile_owner_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    profile: Mapped[dict] = mapped_column(JSON)
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class CampaignBriefRevision(TimestampedModel, Base):
    __tablename__ = "ai_script_campaign_brief_revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "revision", name="uq_ai_script_campaign_project_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    content_mode: Mapped[str] = mapped_column(String(32))
    brand_brief: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Job(TimestampedModel, Base):
    __tablename__ = "ai_script_jobs"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "type",
            "idempotency_key",
            name="uq_ai_script_job_owner_type_idempotency_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(128), default="awaiting_worker")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    routing_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    graph_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class StyleProfileSuggestion(TimestampedModel, Base):
    __tablename__ = "ai_script_style_profile_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_script_jobs.id"), unique=True)
    examples: Mapped[list[dict]] = mapped_column(JSON)
    profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ScriptVersion(TimestampedModel, Base):
    __tablename__ = "ai_script_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_ai_script_project_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_script_versions.id"), nullable=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_script_jobs.id"), nullable=True, unique=True
    )
    origin: Mapped[str] = mapped_column(String(64))
    content: Mapped[dict] = mapped_column(JSON)
    requirement_checks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    warning_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class AssistantConversation(TimestampedModel, Base):
    __tablename__ = "ai_script_assistant_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)


class AssistantMessage(TimestampedModel, Base):
    __tablename__ = "ai_script_assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_script_assistant_conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    target_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    base_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class RevisionProposal(TimestampedModel, Base):
    __tablename__ = "ai_script_revision_proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_script_assistant_conversations.id"), index=True
    )
    base_script_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_script_versions.id"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_script_jobs.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    requirement_checks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    warning_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class LlmCall(TimestampedModel, Base):
    __tablename__ = "ai_script_llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_script_jobs.id"), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    requested_model: Mapped[str] = mapped_column(String(255))
    actual_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(64))
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)

# Compatibility exports let shared code import one domain module while each feature
# owns its implementation model in a focused folder.
from app.features.assets.models import Asset  # noqa: E402
from app.features.clip_generation.models import ClipCandidate  # noqa: E402
from app.features.editing.models import EditRender, EditVersion  # noqa: E402
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation  # noqa: E402
from app.features.script_alignment.models import ScriptAlignment  # noqa: E402

__all__ = [
    "Asset", "AssistantConversation", "AssistantMessage", "Base", "CampaignBriefRevision",
    "ClipCandidate", "EditRender", "EditVersion", "Job", "LlmCall", "Project", "Publication",
    "RevisionProposal", "ScriptAlignment", "ScriptVersion", "StyleProfileRevision",
    "StyleProfileSuggestion", "TranscriptSegment", "VisualObservation",
]
