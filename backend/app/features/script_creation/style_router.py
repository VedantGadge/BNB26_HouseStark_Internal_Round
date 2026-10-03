"""Creator-style endpoints for the script-creation feature."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.script_creation.jobs import IdempotencyConflictError, JobRepository, job_response
from app.features.script_creation.persistence import (
    StaleRevisionError,
    current_style_profile,
    save_style_profile,
)
from app.features.script_creation.routing import require_openrouter_configuration, routing_snapshot
from app.models import StyleProfileSuggestion
from app.schemas import (
    CreatorStyleProfileResponse,
    CreatorStyleProfileSaveRequest,
    JobResponse,
    JobStatus,
    JobType,
    StyleProfileSuggestionRequest,
    StyleProfileSuggestionResponse,
)

router = APIRouter()

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=200),
]


@router.get("", response_model=CreatorStyleProfileResponse)
def get_style_profile(
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> CreatorStyleProfileResponse:
    profile = current_style_profile(session, creator.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style profile not found.",
        )
    return CreatorStyleProfileResponse(revision=profile.revision, profile=profile.profile)


@router.put("", response_model=CreatorStyleProfileResponse)
def put_style_profile(
    request: CreatorStyleProfileSaveRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> CreatorStyleProfileResponse:
    try:
        return save_style_profile(session, creator.id, request)
    except StaleRevisionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Style profile was updated elsewhere. Refresh before saving.",
        ) from error


@router.post("/suggestions", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def queue_style_suggestion(
    request: StyleProfileSuggestionRequest,
    idempotency_key: IdempotencyKey,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> JobResponse:
    require_openrouter_configuration(settings)
    input_snapshot = request.model_dump(mode="json")
    jobs = JobRepository(session)
    existing = jobs.find_by_idempotency(
        creator.id,
        JobType.STYLE_PROFILE_SUGGESTION,
        idempotency_key,
    )
    try:
        job = jobs.enqueue(
            owner_id=creator.id,
            project_id=None,
            job_type=JobType.STYLE_PROFILE_SUGGESTION,
            idempotency_key=idempotency_key,
            input_snapshot=input_snapshot,
            routing_snapshot=routing_snapshot(settings),
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with different input.",
        ) from error
    if existing is None:
        session.add(
            StyleProfileSuggestion(
                owner_id=creator.id,
                job_id=job.id,
                examples=input_snapshot["examples"],
            )
        )
        session.commit()
    return job_response(job)


@router.get("/suggestions/{suggestion_id}", response_model=StyleProfileSuggestionResponse)
def get_style_suggestion(
    suggestion_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> StyleProfileSuggestionResponse:
    suggestion = session.scalar(
        select(StyleProfileSuggestion).where(
            StyleProfileSuggestion.job_id == suggestion_id,
            StyleProfileSuggestion.owner_id == creator.id,
        )
    )
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style suggestion not found.",
        )
    job = JobRepository(session).get_owned(creator.id, suggestion.job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style suggestion not found.",
        )
    return StyleProfileSuggestionResponse(
        id=str(suggestion.id),
        status=JobStatus(job.status),
        profile=suggestion.profile,
    )
