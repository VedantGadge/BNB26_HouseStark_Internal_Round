import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    source_start_ms: Mapped[int] = mapped_column(BigInteger)
    source_end_ms: Mapped[int] = mapped_column(BigInteger)
    hook: Mapped[str] = mapped_column(Text)
    transcript_text: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(Text, default="suggested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
