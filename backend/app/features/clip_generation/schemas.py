from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClipGenerationCreate(BaseModel):
    max_candidates: int = Field(default=10, ge=1, le=50)
    min_duration_ms: int = Field(default=8_000, ge=1_000, le=120_000)
    max_duration_ms: int = Field(default=60_000, ge=5_000, le=180_000)


class ClipCandidateResponse(BaseModel):
    id: UUID
    asset_id: UUID
    source_start_ms: int
    source_end_ms: int
    hook: str
    transcript_text: str
    score: float = Field(ge=0, le=1)
    reasons: list[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
