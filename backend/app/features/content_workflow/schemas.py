from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, Field, HttpUrl, model_validator

from app.schemas import Platform, SchemaModel

Stage = Literal["idea", "assets", "editing", "review", "approved", "exported", "published"]


class PackageInput(SchemaModel):
    title: str = Field(min_length=1, max_length=160)
    caption: str = Field(min_length=1, max_length=2000)
    media_checked: bool = False


class WorkflowPatch(SchemaModel):
    expected_revision: int = Field(ge=1)
    assets_ready: bool | None = None
    editing_complete: bool | None = None
    package: PackageInput | None = None

    @model_validator(mode="after")
    def requires_a_change(self):
        if not ({"assets_ready", "editing_complete", "package"} & self.model_fields_set):
            raise ValueError("Provide a checklist value or package to update the workflow.")
        return self


class TransitionRequest(SchemaModel):
    expected_revision: int = Field(ge=1)
    stage: Stage


class PublicationInput(SchemaModel):
    expected_revision: int = Field(ge=1)
    platform: Platform
    planned_at: AwareDatetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    caption: str | None = Field(default=None, min_length=1, max_length=2000)


class PublicationPatch(SchemaModel):
    expected_revision: int = Field(ge=1)
    planned_at: AwareDatetime | None = None
    confirm_published: bool = False
    published_at: AwareDatetime | None = None
    external_url: HttpUrl | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    caption: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validates_confirmation(self):
        if self.confirm_published and (self.title is not None or self.caption is not None):
            raise ValueError("Save supporting copy before confirming publication.")
        if self.confirm_published:
            if self.published_at is None or self.external_url is None:
                raise ValueError("Confirmation requires an actual date and HTTP(S) post URL.")
            if self.published_at > datetime.now(UTC):
                raise ValueError("Actual publication date cannot be in the future.")
        elif self.published_at is not None or self.external_url is not None:
            raise ValueError("Post details require explicit publication confirmation.")
        if not self.confirm_published and not (
            {"planned_at", "title", "caption"} & self.model_fields_set
        ):
            raise ValueError("Provide a planned date or supporting copy to update the publication.")
        return self


class PublicationResponse(SchemaModel):
    id: str
    platform: Platform
    status: Literal["draft", "planned", "published"]
    mode: Literal["manual"] = "manual"
    planned_at: datetime | None
    published_at: datetime | None
    external_url: str | None
    package_snapshot: dict
    supporting_copy: dict


class WorkflowResponse(SchemaModel):
    project_id: str
    name: str
    brief: str
    target_platforms: list[Platform]
    stage: Stage
    revision: int
    checklist: dict[str, bool]
    review_status: str
    package: dict | None
    approved_package: dict | None
    timestamps: dict[str, str]
    next_stage: Stage | None
    blocking_reasons: list[str]
    next_action: str
    jobs: list[dict]
    publications: list[PublicationResponse]
