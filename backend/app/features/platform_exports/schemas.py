from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.features.editing.schemas import EditRecipePayload


class PlatformExportPreset(StrEnum):
    INSTAGRAM_REEL = "instagram_reel"
    TIKTOK = "tiktok"
    YOUTUBE_SHORT = "youtube_short"
    INSTAGRAM_FEED = "instagram_feed"
    LINKEDIN_FEED = "linkedin_feed"
    YOUTUBE_VIDEO = "youtube_video"


class PlatformExportCreate(BaseModel):
    preset: PlatformExportPreset
    title: str | None = Field(default=None, min_length=1, max_length=160)
    fit: Literal["crop", "pad"] = "crop"
    supporting_copy: str | None = Field(default=None, max_length=2_200)
    hashtags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("hashtags")
    @classmethod
    def normalize_hashtags(cls, hashtags: list[str]) -> list[str]:
        normalized = [hashtag.strip().lstrip("#") for hashtag in hashtags if hashtag.strip()]
        if any(len(hashtag) > 80 for hashtag in normalized):
            raise ValueError("Each hashtag must be at most 80 characters long")
        if len(set(hashtag.lower() for hashtag in normalized)) != len(normalized):
            raise ValueError("Hashtags must not contain duplicates")
        return normalized


class PlatformExportResponse(BaseModel):
    id: UUID
    edit_version_id: UUID
    asset_id: UUID
    preset: PlatformExportPreset
    platform: str
    derived_recipe: EditRecipePayload
    supporting_copy: str | None
    hashtags: list[str]
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
