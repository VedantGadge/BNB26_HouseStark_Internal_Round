from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SchemaModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


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


class JobType(StrEnum):
    SCRIPT_GENERATION = "script_generation"
    ASSISTANT_REVISION = "assistant_revision"
    STYLE_PROFILE_SUGGESTION = "style_profile_suggestion"


class ContentMode(StrEnum):
    PERSONAL = "personal"
    BRAND = "brand"


class ContentLanguage(StrEnum):
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"


class SignatureInclusionPolicy(StrEnum):
    ALWAYS = "always"
    WHEN_RELEVANT = "when_relevant"
    ON_REQUEST = "on_request"


class SignaturePlacement(StrEnum):
    OPENING = "opening"
    BODY = "body"
    CLOSING = "closing"


class BrandRequirementKind(StrEnum):
    LITERAL = "literal"
    TALKING_POINT = "talking_point"


class RequirementStatus(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"


class PublishingDestination(StrEnum):
    CREATOR_ACCOUNT = "creator_account"
    BRAND_ACCOUNT = "brand_account"


class AssistantTargetScope(StrEnum):
    SCRIPT = "script"
    HOOK = "hook"
    SECTION = "section"
    CTA = "cta"
    SUPPORTING_COPY = "supporting_copy"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    DISCARDED = "discarded"


class ScriptOrigin(StrEnum):
    GENERATED = "generated"
    CREATOR = "creator"
    ASSISTANT_APPLIED = "assistant_applied"


StableId = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class ProjectCreate(SchemaModel):
    name: str = Field(min_length=1, max_length=120)
    brief: str = Field(min_length=1, max_length=8_000)
    audience: str | None = Field(default=None, max_length=500)
    tone: str | None = Field(default=None, max_length=120)
    target_platforms: list[Platform] = Field(default_factory=list)


class ProjectSummary(SchemaModel):
    id: str
    name: str
    workflow_stage: str


class JobResponse(SchemaModel):
    id: str
    status: JobStatus
    stage: str
    error: str | None = None
    conversation_id: str | None = None


class SignatureLine(SchemaModel):
    id: str = StableId
    text: str = Field(min_length=1, max_length=240)
    inclusion_policy: SignatureInclusionPolicy
    placement: SignaturePlacement


class CreatorStyleProfileContent(SchemaModel):
    voice: str | None = Field(default=None, max_length=500)
    preferred_language: ContentLanguage | None = None
    pacing: str | None = Field(default=None, max_length=500)
    typical_structure: str | None = Field(default=None, max_length=1_000)
    preferred_ctas: list[str] = Field(default_factory=list, max_length=10)
    avoided_expressions: list[str] = Field(default_factory=list, max_length=20)
    signature_lines: list[SignatureLine] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def has_unique_signature_lines(self) -> CreatorStyleProfileContent:
        ids = [line.id for line in self.signature_lines]
        if len(ids) != len(set(ids)):
            raise ValueError("signature_lines must have unique IDs")
        return self


class CreatorStyleProfileSaveRequest(SchemaModel):
    base_revision: int | None = Field(default=None, ge=1)
    profile: CreatorStyleProfileContent
    suggestion_id: str | None = Field(default=None, min_length=1, max_length=120)


class CreatorStyleProfileResponse(SchemaModel):
    revision: int = Field(ge=1)
    profile: CreatorStyleProfileContent


class StyleExample(SchemaModel):
    text: str = Field(min_length=1, max_length=8_000)


class StyleProfileSuggestionRequest(SchemaModel):
    examples: list[StyleExample] = Field(min_length=1, max_length=5)


class StyleProfileSuggestionResponse(SchemaModel):
    id: str = StableId
    status: JobStatus
    profile: CreatorStyleProfileContent | None = None


class BrandRequirement(SchemaModel):
    id: str = StableId
    kind: BrandRequirementKind
    description: str = Field(min_length=1, max_length=1_000)
    literal_text: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validates_literal_text(self) -> BrandRequirement:
        if self.kind is BrandRequirementKind.LITERAL and not self.literal_text:
            raise ValueError("literal requirements need literal_text")
        if self.kind is BrandRequirementKind.TALKING_POINT and self.literal_text:
            raise ValueError("talking-point requirements cannot set literal_text")
        return self


class BrandCampaignBrief(SchemaModel):
    brand_name: str = Field(min_length=1, max_length=160)
    product_name: str = Field(min_length=1, max_length=160)
    product_description: str = Field(min_length=1, max_length=2_000)
    approved_claims: list[str] = Field(default_factory=list, max_length=20)
    campaign_goal: str = Field(min_length=1, max_length=500)
    campaign_audience: str = Field(min_length=1, max_length=500)
    preferred_tone: str | None = Field(default=None, max_length=120)
    target_platforms: list[Platform] = Field(default_factory=list)
    target_duration_seconds: int | None = Field(default=None, ge=15, le=300)
    call_to_action: str | None = Field(default=None, max_length=500)
    discount_code: str | None = Field(default=None, max_length=80)
    requirements: list[BrandRequirement] = Field(default_factory=list, max_length=20)
    forbidden_phrases: list[str] = Field(default_factory=list, max_length=20)
    publishing_destination: PublishingDestination

    @model_validator(mode="after")
    def has_unique_requirement_ids(self) -> BrandCampaignBrief:
        ids = [requirement.id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("requirements must have unique IDs")
        return self


class CampaignBriefSaveRequest(SchemaModel):
    base_revision: int | None = Field(default=None, ge=1)
    content_mode: ContentMode
    brand_brief: BrandCampaignBrief | None = None

    @model_validator(mode="after")
    def validates_mode(self) -> CampaignBriefSaveRequest:
        if self.content_mode is ContentMode.BRAND and self.brand_brief is None:
            raise ValueError("brand mode requires brand_brief")
        if self.content_mode is ContentMode.PERSONAL and self.brand_brief is not None:
            raise ValueError("personal mode cannot include brand_brief")
        return self


class CampaignBriefResponse(SchemaModel):
    revision: int = Field(ge=1)
    content_mode: ContentMode
    brand_brief: BrandCampaignBrief | None = None


class ScriptGenerationRequest(SchemaModel):
    brief: str | None = Field(default=None, min_length=1, max_length=8_000)
    audience: str | None = Field(default=None, max_length=500)
    tone: str | None = Field(default=None, max_length=120)
    target_platforms: list[Platform] | None = None
    target_duration_seconds: int | None = Field(default=None, ge=15, le=300)
    language: ContentLanguage = ContentLanguage.ENGLISH
    use_style_profile: bool = False
    style_profile_revision: int | None = Field(default=None, ge=1)
    campaign_brief_revision: int | None = Field(default=None, ge=1)
    optional_signature_line_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validates_profile_choice(self) -> ScriptGenerationRequest:
        if self.use_style_profile and self.style_profile_revision is None:
            raise ValueError("use_style_profile requires style_profile_revision")
        if not self.use_style_profile and self.style_profile_revision is not None:
            raise ValueError("style_profile_revision requires use_style_profile")
        if len(self.optional_signature_line_ids) != len(set(self.optional_signature_line_ids)):
            raise ValueError("optional_signature_line_ids must be unique")
        return self


class ScriptHook(SchemaModel):
    id: str = StableId
    text: str = Field(min_length=1, max_length=500)


class ScriptSection(SchemaModel):
    id: str = StableId
    position: int = Field(ge=1, le=50)
    heading: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=3_000)
    estimated_duration_seconds: int | None = Field(default=None, ge=1, le=300)


class ScriptContent(SchemaModel):
    hooks: list[ScriptHook] = Field(min_length=1, max_length=5)
    selected_hook_id: str = StableId
    sections: list[ScriptSection] = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2_000)
    call_to_action: str = Field(min_length=1, max_length=500)
    production_notes: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validates_structure(self) -> ScriptContent:
        hook_ids = [hook.id for hook in self.hooks]
        if len(hook_ids) != len(set(hook_ids)):
            raise ValueError("hooks must have unique IDs")
        if self.selected_hook_id not in hook_ids:
            raise ValueError("selected_hook_id must reference a hook")

        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("sections must have unique IDs")
        positions = [section.position for section in self.sections]
        if positions != list(range(1, len(self.sections) + 1)):
            raise ValueError("sections must be ordered with consecutive positions starting at 1")
        return self


class RequirementCheck(SchemaModel):
    requirement_id: str = StableId
    status: RequirementStatus
    evidence_section_ids: list[str] = Field(default_factory=list, max_length=20)
    message: str | None = Field(default=None, max_length=1_000)


class ScriptVersionResponse(SchemaModel):
    id: str = StableId
    version: int = Field(ge=1)
    origin: ScriptOrigin
    created_at: datetime
    generation_job_id: str | None = None
    input_snapshot: dict = Field(default_factory=dict)
    content: ScriptContent
    requirement_checks: list[RequirementCheck] = Field(default_factory=list)
    warning_ids: list[str] = Field(default_factory=list)


class CreatorEditRequest(SchemaModel):
    base_version: int = Field(ge=1)
    content: ScriptContent
    acknowledged_warning_ids: list[str] = Field(default_factory=list, max_length=20)


class AssistantMessageRequest(SchemaModel):
    base_version: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=2_000)
    target_scope: AssistantTargetScope
    target_id: str | None = Field(default=None, min_length=1, max_length=120)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def validates_target(self) -> AssistantMessageRequest:
        target_required = self.target_scope in {
            AssistantTargetScope.HOOK,
            AssistantTargetScope.SECTION,
        }
        if target_required and not self.target_id:
            raise ValueError("hook and section targets require target_id")
        if not target_required and self.target_id is not None:
            raise ValueError("this target scope cannot include target_id")
        return self


class ProposalChange(SchemaModel):
    target_scope: AssistantTargetScope
    target_id: str | None = Field(default=None, min_length=1, max_length=120)
    before: str | None = Field(default=None, min_length=1, max_length=3_000)
    after: str | None = Field(default=None, min_length=1, max_length=3_000)
    content_after: ScriptContent | None = None

    @model_validator(mode="after")
    def validates_target(self) -> ProposalChange:
        target_required = self.target_scope in {
            AssistantTargetScope.HOOK,
            AssistantTargetScope.SECTION,
        }
        if target_required and not self.target_id:
            raise ValueError("hook and section changes require target_id")
        if not target_required and self.target_id is not None:
            raise ValueError("this change scope cannot include target_id")
        if self.target_scope is AssistantTargetScope.SCRIPT:
            if self.content_after is None or self.before is not None or self.after is not None:
                raise ValueError("script changes require content_after only")
        elif self.content_after is not None:
            raise ValueError("only script changes can include content_after")
        elif self.before is None or self.after is None:
            raise ValueError("text changes require before and after")
        return self


class RevisionProposalResponse(SchemaModel):
    id: str = StableId
    conversation_id: str = StableId
    base_version: int = Field(ge=1)
    status: ProposalStatus
    explanation: str = Field(min_length=1, max_length=1_000)
    changes: list[ProposalChange] = Field(min_length=1, max_length=20)
    requirement_checks: list[RequirementCheck] = Field(default_factory=list)
    warning_ids: list[str] = Field(default_factory=list)


class AssistantConversationMessageResponse(SchemaModel):
    id: str = StableId
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=2_000)
    target_scope: AssistantTargetScope | None = None
    target_id: str | None = None
    base_version: int | None = Field(default=None, ge=1)


class RevisionProposalSummary(SchemaModel):
    id: str = StableId
    base_version: int = Field(ge=1)
    status: ProposalStatus
    explanation: str | None = Field(default=None, max_length=1_000)
    changes: list[ProposalChange] = Field(default_factory=list, max_length=20)
    requirement_checks: list[RequirementCheck] = Field(default_factory=list)
    warning_ids: list[str] = Field(default_factory=list)


class AssistantConversationResponse(SchemaModel):
    id: str = StableId
    messages: list[AssistantConversationMessageResponse] = Field(default_factory=list)
    proposals: list[RevisionProposalSummary] = Field(default_factory=list)


class ProposalApplyRequest(SchemaModel):
    acknowledged_warning_ids: list[str] = Field(default_factory=list, max_length=20)


class EditSegment(SchemaModel):
    id: str = Field(min_length=1, max_length=120)
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def has_positive_duration(self) -> EditSegment:
        if self.source_end_ms <= self.source_start_ms:
            raise ValueError("source_end_ms must be greater than source_start_ms")
        return self


class OutputFormat(SchemaModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fit: str = Field(pattern="^(crop|pad)$")


class CropPosition(SchemaModel):
    center_x: float = Field(ge=0, le=1)
    center_y: float = Field(ge=0, le=1)


class Caption(SchemaModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def has_positive_duration(self) -> Caption:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class EditRecipe(SchemaModel):
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
