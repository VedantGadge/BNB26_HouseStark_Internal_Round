from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Platform(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brief: str = Field(min_length=1, max_length=8_000)
    audience: str | None = Field(default=None, max_length=500)
    tone: str | None = Field(default=None, max_length=120)
    target_platforms: list[Platform] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    id: str
    name: str
    workflow_stage: str


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    stage: str
    error: str | None = None


class EditSegment(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def has_positive_duration(self) -> "EditSegment":
        if self.source_end_ms <= self.source_start_ms:
            raise ValueError("source_end_ms must be greater than source_start_ms")
        return self


class OutputFormat(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fit: str = Field(pattern="^(crop|pad)$")


class CropPosition(BaseModel):
    center_x: float = Field(ge=0, le=1)
    center_y: float = Field(ge=0, le=1)


class Caption(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def has_positive_duration(self) -> "Caption":
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class EditRecipe(BaseModel):
    schema_version: int = Field(ge=1)
    source_asset_id: str = Field(min_length=1)
    segments: list[EditSegment] = Field(min_length=1)
    output: OutputFormat
    crop: CropPosition
    captions: list[Caption] = Field(default_factory=list)


# Compatibility exports for callers that still use the original shared schema module.
from app.features.assets.schemas import (  # noqa: E402
    AssetKind,
    AssetProcessingStatus,
    AssetResponse,
    AssetUploadComplete,
    AssetUploadSession,
    AssetUploadSessionCreate,
)

__all__ = [
    "AssetKind",
    "AssetProcessingStatus",
    "AssetResponse",
    "AssetUploadComplete",
    "AssetUploadSession",
    "AssetUploadSessionCreate",
    "Caption",
    "CropPosition",
    "EditRecipe",
    "EditSegment",
    "JobResponse",
    "JobStatus",
    "OutputFormat",
    "Platform",
    "ProjectCreate",
    "ProjectSummary",
]
