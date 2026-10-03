import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScriptAlignment(Base):
    __tablename__ = "script_alignments"

    script_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ai_script_versions.id"), nullable=True
    )
    section_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    match_status: Mapped[str] = mapped_column(String(32), default="matched")
    visual_evidence: Mapped[list[dict]] = mapped_column(JSON, default=list)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    source_start_ms: Mapped[int] = mapped_column(BigInteger)
    source_end_ms: Mapped[int] = mapped_column(BigInteger)
    script_beat: Mapped[str] = mapped_column(Text)
    evidence_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
