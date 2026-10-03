from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScriptAlignmentCreate(BaseModel):
    script_text: str = Field(min_length=1, max_length=20_000)


class ScriptAlignmentResponse(BaseModel):
    id: UUID
    asset_id: UUID
    source_start_ms: int
    source_end_ms: int
    script_beat: str
    evidence_text: str
    confidence: float = Field(ge=0, le=1)
    created_at: datetime

    model_config = {"from_attributes": True}
