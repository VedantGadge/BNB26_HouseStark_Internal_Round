from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.schemas import Platform


class ClipRequest(BaseModel):
    asset_id: UUID
    script_version_id: UUID | None = None
    max_candidates: int = Field(default=3, ge=1, le=10)


class ManualClipRequest(BaseModel):
    asset_id: UUID
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)


class ExportRequest(BaseModel):
    edit_version_id: UUID
    preset: Literal[
        "vertical",
        "square",
        "landscape",
        "instagram_reel",
        "tiktok",
        "youtube_short",
        "instagram_feed",
        "linkedin_feed",
        "youtube_video",
    ] = "vertical"
    platform: Platform = Platform.INSTAGRAM
    title: str = Field(min_length=1, max_length=160)
    caption: str = Field(min_length=1, max_length=2000)
    hashtags: list[str] = Field(default_factory=list, max_length=20)
    fit: Literal["crop", "pad"] = "crop"

    @model_validator(mode="after")
    def validate_platform_preset(self):
        from app.features.platform_exports.presets import PRESETS
        from app.features.platform_exports.schemas import PlatformExportPreset

        if self.preset not in {"vertical", "square", "landscape"}:
            if PRESETS[PlatformExportPreset(self.preset)].platform != self.platform:
                raise ValueError("Choose the platform matching this named preset")
        return self


class ReviewRequest(BaseModel):
    edit_version_id: UUID


class PerformanceInput(BaseModel):
    observed_at: AwareDatetime
    reporting_window_days: int = Field(ge=1, le=365)
    views: int = Field(ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    retention: float | None = Field(default=None, ge=0, le=1)
    source: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def not_future(self):
        if self.observed_at > datetime.now(UTC):
            raise ValueError("Observation date cannot be in the future")
        return self
