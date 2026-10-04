"""Contracts for RiskRadar's reviewable, non-legal pre-publish findings."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas import JobStatus


class RiskCategory(StrEnum):
    PERSONAL_DATA = "personal_data"
    BRAND_POLICY = "brand_policy"
    DISCLOSURE = "disclosure"
    CONTENT_MISMATCH = "content_mismatch"
    VISUAL_REVIEW = "visual_review"
    ACCESSIBILITY = "accessibility"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingOrigin(StrEnum):
    DETERMINISTIC = "deterministic"
    MODEL = "model"


class ReviewReadiness(StrEnum):
    NO_HIGH_OR_MEDIUM_RISKS_FOUND = "no_high_or_medium_risks_found"
    CREATOR_REVIEW_REQUIRED = "creator_review_required"


class RiskRadarScanRequest(BaseModel):
    """Select one ready source asset and the content being reviewed against it."""

    asset_id: UUID
    script_version_id: UUID | None = None
    edit_version_id: UUID | None = None


class RiskRadarModelFinding(BaseModel):
    """Strict provider output before CreatorAI adds an origin and validates evidence IDs."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: RiskCategory
    severity: RiskSeverity
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=600)
    recommendation: str = Field(min_length=1, max_length=600)
    reference_ids: list[str] = Field(min_length=1, max_length=8)


class RiskRadarModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=600)
    findings: list[RiskRadarModelFinding] = Field(default_factory=list, max_length=20)


class RiskRadarFinding(RiskRadarModelFinding):
    origin: FindingOrigin


class RiskRadarResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=600)
    findings: list[RiskRadarFinding] = Field(default_factory=list, max_length=40)
    reviewed_reference_count: int = Field(ge=0)
    review_readiness: ReviewReadiness
    limitations: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def readiness_matches_findings(self) -> RiskRadarResult:
        requires_review = any(
            finding.severity in {RiskSeverity.MEDIUM, RiskSeverity.HIGH}
            for finding in self.findings
        )
        expected = (
            ReviewReadiness.CREATOR_REVIEW_REQUIRED
            if requires_review
            else ReviewReadiness.NO_HIGH_OR_MEDIUM_RISKS_FOUND
        )
        if self.review_readiness is not expected:
            raise ValueError("review_readiness must reflect medium and high findings")
        return self


class RiskRadarScanResponse(BaseModel):
    id: UUID
    status: JobStatus
    stage: str
    error: str | None = None
    result: RiskRadarResult | None = None
