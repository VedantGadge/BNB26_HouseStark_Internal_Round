from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CaptionStyle(StrEnum):
    CLEAN = "clean"
    BOLD = "bold"
    BOLD_HIGHLIGHT = "bold_highlight"


class OverlayPosition(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"


class OutputCanvas(BaseModel):
    width: int = Field(default=1080, ge=360, le=1920)
    height: int = Field(default=1920, ge=360, le=1920)
    safe_top_px: int = Field(default=80, ge=0, le=500)
    safe_bottom_px: int = Field(default=150, ge=0, le=500)


class CropPosition(BaseModel):
    center_x: float = Field(default=0.5, ge=0, le=1)
    center_y: float = Field(default=0.5, ge=0, le=1)


class CaptionItem(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def has_positive_duration(self) -> "CaptionItem":
        if self.end_ms <= self.start_ms:
            raise ValueError("caption end_ms must be greater than start_ms")
        return self


class TitleOverlay(BaseModel):
    text: str = Field(min_length=1, max_length=140)
    start_ms: int = Field(default=0, ge=0)
    end_ms: int = Field(default=3_000, gt=0)
    position: OverlayPosition = OverlayPosition.TOP

    @model_validator(mode="after")
    def has_positive_duration(self) -> "TitleOverlay":
        if self.end_ms <= self.start_ms:
            raise ValueError("title end_ms must be greater than start_ms")
        return self


class EmphasisZoom(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    scale: float = Field(default=1.08, ge=1.02, le=1.2)

    @model_validator(mode="after")
    def has_positive_duration(self) -> "EmphasisZoom":
        if self.end_ms <= self.start_ms:
            raise ValueError("zoom end_ms must be greater than start_ms")
        return self


class AudioPolish(BaseModel):
    normalize: bool = True
    fade_in_ms: int = Field(default=120, ge=0, le=1_000)
    fade_out_ms: int = Field(default=180, ge=0, le=1_000)


class EditRecipePayload(BaseModel):
    """Single-source, short-form recipe. All overlay timings use output time."""

    schema_version: int = Field(default=1, ge=1, le=1)
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)
    output: OutputCanvas = Field(default_factory=OutputCanvas)
    crop: CropPosition = Field(default_factory=CropPosition)
    captions_enabled: bool = True
    caption_style: CaptionStyle = CaptionStyle.BOLD_HIGHLIGHT
    captions: list[CaptionItem] = Field(default_factory=list, max_length=20)
    title: TitleOverlay | None = None
    emphasis_zooms: list[EmphasisZoom] = Field(default_factory=list, max_length=2)
    audio: AudioPolish = Field(default_factory=AudioPolish)

    @model_validator(mode="after")
    def has_usable_source_duration(self) -> "EditRecipePayload":
        duration_ms = self.source_end_ms - self.source_start_ms
        if duration_ms < 2_000:
            raise ValueError("An edit must be at least two seconds long")
        if duration_ms > 60_000:
            raise ValueError("An edit cannot exceed sixty seconds")
        return self


class EditVersionCreate(BaseModel):
    """Omit recipe only for an initial assistant-seeded version."""

    base_version_id: UUID | None = None
    recipe: EditRecipePayload | None = None


class EditVersionResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    asset_id: UUID
    revision: int
    parent_version_id: UUID | None
    author_type: str
    recipe: EditRecipePayload
    created_at: datetime

    model_config = {"from_attributes": True}


class EditRenderResponse(BaseModel):
    id: UUID
    edit_version_id: UUID
    asset_id: UUID
    public_id: str
    provider_version: str | None
    format: str
    width: int | None
    height: int | None
    duration_ms: int | None
    processing_status: str
    processing_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
