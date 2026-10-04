"""Owner-scoped durable RiskRadar submissions and result retrieval."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.risk_radar.schemas import (
    RiskRadarScanRequest,
    RiskRadarScanResponse,
)
from app.features.risk_radar.service import build_scan_snapshot
from app.features.script_creation.jobs import IdempotencyConflictError, JobRepository, job_response
from app.features.script_creation.routing import routing_snapshot
from app.repositories import ProjectRepository
from app.schemas import JobResponse, JobType

router = APIRouter()

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=200),
]


@router.post("/scans", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def queue_risk_radar_scan(
    project_id: uuid.UUID,
    request: RiskRadarScanRequest,
    idempotency_key: IdempotencyKey,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> JobResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if settings.openrouter_api_key is None or not settings.openrouter_default_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RiskRadar AI review is not configured.",
        )

    jobs = JobRepository(session)
    idempotency_payload = request.model_dump(mode="json")
    existing = jobs.find_by_idempotency(creator.id, JobType.RISK_RADAR, idempotency_key)
    if existing is not None:
        try:
            return job_response(
                jobs.enqueue(
                    owner_id=creator.id,
                    project_id=project.id,
                    job_type=JobType.RISK_RADAR,
                    idempotency_key=idempotency_key,
                    input_snapshot=existing.input_snapshot,
                    routing_snapshot=routing_snapshot(settings),
                    idempotency_payload=idempotency_payload,
                )
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used with different input.",
            ) from error

    input_snapshot = build_scan_snapshot(
        session,
        project=project,
        owner_id=creator.id,
        asset_id=request.asset_id,
        script_version_id=request.script_version_id,
        edit_version_id=request.edit_version_id,
    )
    try:
        job = jobs.enqueue(
            owner_id=creator.id,
            project_id=project.id,
            job_type=JobType.RISK_RADAR,
            idempotency_key=idempotency_key,
            input_snapshot=input_snapshot,
            routing_snapshot=routing_snapshot(settings),
            idempotency_payload=idempotency_payload,
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with different input.",
        ) from error
    return job_response(job)


@router.get("/scans/{job_id}", response_model=RiskRadarScanResponse)
def get_risk_radar_scan(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> RiskRadarScanResponse:
    if ProjectRepository(session).get_owned(creator.id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    job = JobRepository(session).get_owned(creator.id, job_id)
    if job is None or job.project_id != project_id or job.type != JobType.RISK_RADAR.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RiskRadar scan not found.",
        )
    return RiskRadarScanResponse(
        id=job.id,
        status=job.status,
        stage=job.stage,
        error=job.error,
        result=job.input_snapshot.get("result"),
    )
