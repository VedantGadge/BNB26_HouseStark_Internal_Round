from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClipGenerationCreate(BaseModel):
    max_candidates: int = Field(default=10, ge=1, le=50)
    min_duration_ms: int = Field(default=8_000, ge=2_000, le=60_000)
    max_duration_ms: int = Field(default=60_000, ge=5_000, le=60_000)


class ClipCandidateResponse(BaseModel):
    id: UUID
    asset_id: UUID
    script_version_id: UUID | None
    source_start_ms: int
    source_end_ms: int
    hook: str
    transcript_text: str
    score: float = Field(ge=0, le=1)
    reasons: list[str]
    status: str
    is_stale: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
