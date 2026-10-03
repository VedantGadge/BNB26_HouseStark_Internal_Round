from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AssetKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"


class AssetProcessingStatus(StrEnum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AssetUploadSessionCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)
    byte_size: int = Field(gt=0, le=100_000_000)
    kind: AssetKind
    tags: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def content_type_matches_kind(self) -> "AssetUploadSessionCreate":
        expected_prefix = "audio/" if self.kind is AssetKind.AUDIO else f"{self.kind.value}/"
        if not self.content_type.lower().startswith(expected_prefix):
            raise ValueError(f"content_type must be a {self.kind.value} media type")
        return self


class AssetUploadSession(BaseModel):
    asset_id: UUID
    cloud_name: str
    api_key: str
    resource_type: str
    upload_url: str
    public_id: str
    delivery_type: str
    overwrite: bool
    timestamp: int
    signature: str


class AssetUploadComplete(BaseModel):
    provider_asset_id: str = Field(min_length=1, max_length=255)
    provider_version: str = Field(min_length=1, max_length=64)


class AssetResponse(BaseModel):
    id: UUID
    project_id: UUID
    kind: AssetKind
    public_id: str
    resource_type: str
    delivery_type: str
    provider_version: str | None
    format: str | None
    byte_size: int | None
    width: int | None
    height: int | None
    duration_ms: int | None
    tags: list[str]
    processing_status: AssetProcessingStatus
    processing_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
