from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.assets.schemas import AssetProcessingStatus


class TranscriptSegmentResponse(BaseModel):
    id: UUID
    source_start_ms: int
    source_end_ms: int
    text: str
    word_timings: list[dict[str, object]] | None

    model_config = {"from_attributes": True}


class VisualObservationResponse(BaseModel):
    id: UUID
    source_start_ms: int
    source_end_ms: int
    frame_references: list[str]
    description: str
    confidence: float | None = Field(default=None, ge=0, le=1)

    model_config = {"from_attributes": True}


class AssetAnalysisResponse(BaseModel):
    asset_id: UUID
    processing_status: AssetProcessingStatus
    processing_error: str | None
    duration_ms: int | None
    transcript_segments: list[TranscriptSegmentResponse]
    visual_observations: list[VisualObservationResponse]
    updated_at: datetime
