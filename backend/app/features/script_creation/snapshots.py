"""Immutable request snapshots resolved before work enters the queue."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CampaignBriefRevision, Project, StyleProfileRevision
from app.schemas import ScriptGenerationRequest


def resolve_generation_snapshot(
    session: Session,
    *,
    owner_id: str,
    project: Project,
    request: ScriptGenerationRequest,
) -> dict:
    target_platforms = (
        [platform.value for platform in request.target_platforms]
        if request.target_platforms is not None
        else project.target_platforms
    )
    if not target_platforms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one target platform must be resolved before generation.",
        )

    snapshot: dict = {
        "project": {
            "id": str(project.id),
            "brief": request.brief or project.brief,
            "audience": request.audience if request.audience is not None else project.audience,
            "tone": request.tone if request.tone is not None else project.tone,
            "target_platforms": target_platforms,
        },
        "request": request.model_dump(mode="json"),
    }
    if request.use_style_profile:
        style_profile = session.scalar(
            select(StyleProfileRevision).where(
                StyleProfileRevision.owner_id == owner_id,
                StyleProfileRevision.revision == request.style_profile_revision,
            )
        )
        if style_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Style profile not found.",
            )
        snapshot["style_profile"] = {
            "id": str(style_profile.id),
            "revision": style_profile.revision,
            "profile": style_profile.profile,
        }
    if request.campaign_brief_revision is not None:
        campaign_brief = session.scalar(
            select(CampaignBriefRevision).where(
                CampaignBriefRevision.project_id == project.id,
                CampaignBriefRevision.revision == request.campaign_brief_revision,
            )
        )
        if campaign_brief is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign brief not found.",
            )
        snapshot["campaign_brief"] = {
            "id": str(campaign_brief.id),
            "revision": campaign_brief.revision,
            "content_mode": campaign_brief.content_mode,
            "brand_brief": campaign_brief.brand_brief,
        }
    return snapshot


def parse_conversation_id(conversation_id: str | None) -> uuid.UUID | None:
    if conversation_id is None:
        return None
    try:
        return uuid.UUID(conversation_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="conversation_id must be a UUID.",
        ) from error
