import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TranscriptSegment(Base):
    """A time-bounded speech-to-text result in the source asset's clock."""

    __tablename__ = "transcript_segments"
    __table_args__ = (
        CheckConstraint("source_start_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        CheckConstraint(
            "source_end_ms > source_start_ms",
            name="ck_transcript_segments_positive_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    source_start_ms: Mapped[int] = mapped_column(BigInteger)
    source_end_ms: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text)
    word_timings: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VisualObservation(Base):
    """A bounded visual description grounded in sampled source frames."""

    __tablename__ = "visual_observations"
    __table_args__ = (
        CheckConstraint("source_start_ms >= 0", name="ck_visual_observations_start_nonnegative"),
        CheckConstraint(
            "source_end_ms >= source_start_ms",
            name="ck_visual_observations_valid_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    source_start_ms: Mapped[int] = mapped_column(BigInteger)
    source_end_ms: Mapped[int] = mapped_column(BigInteger)
    frame_references: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
