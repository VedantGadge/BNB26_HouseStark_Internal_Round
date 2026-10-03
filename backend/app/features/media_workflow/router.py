from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.assets.access import get_owned_asset
from app.features.assets.models import Asset
from app.features.assets.router import get_storage
from app.features.assets.storage import CloudinaryStorage
from app.features.content_workflow.service import owned_project
from app.features.editing.models import EditRender, EditVersion
from app.features.editing.schemas import EditRenderResponse
from app.features.editing.service import get_owned_candidate, get_owned_edit_version
from app.features.media_workflow.schemas import ClipRequest, ExportRequest, ReviewRequest
from app.features.media_workflow.service import owned_render
from app.features.script_creation.jobs import IdempotencyConflictError, JobRepository, job_response
from app.features.script_creation.routing import routing_snapshot
from app.models import Job, ScriptVersion
from app.schemas import JobResponse, JobType

router = APIRouter()
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


def enqueue(session, creator, project_id, kind, key, payload, routing=None):
    try:
        return job_response(
            JobRepository(session).enqueue(
                owner_id=creator.id,
                project_id=project_id,
                job_type=kind,
                idempotency_key=key,
                input_snapshot=payload,
                routing_snapshot=routing or {},
            )
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            409, "Idempotency-Key was already used with different input."
        ) from error


@router.post("/projects/{project_id}/clips/generate", response_model=JobResponse, status_code=202)
def generate_clips(
    project_id: UUID,
    payload: ClipRequest,
    idempotency_key: Key,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    project = owned_project(session, creator.id, project_id)
    asset = get_owned_asset(session, payload.asset_id, creator.id)
    if asset.project_id != project.id:
        raise HTTPException(404, "Asset not found in this project.")
    if asset.kind != "video" or asset.processing_status != "ready":
        raise HTTPException(409, "Wait for video analysis to finish before generating clips.")
    script_id = payload.script_version_id or project.current_script_version_id
    script = session.get(ScriptVersion, script_id) if script_id else None
    if script is None or script.project_id != project.id:
        raise HTTPException(409, "Save a script belonging to this project first.")
    return enqueue(
        session,
        creator,
        project.id,
        JobType.CLIP_GENERATION,
        idempotency_key,
        {**payload.model_dump(mode="json"), "script_version_id": str(script.id)},
        routing_snapshot(settings),
    )


@router.get("/projects/{project_id}/clips")
def clips(
    project_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    from app.features.clip_generation.models import ClipCandidate
    from app.features.clip_generation.schemas import ClipCandidateResponse

    owned_project(session, creator.id, project_id)
    records = session.scalars(
        select(ClipCandidate)
        .join(Asset)
        .where(Asset.project_id == project_id, Asset.owner_id == creator.id)
        .order_by(ClipCandidate.score.desc())
    )
    return [
        ClipCandidateResponse.model_validate(record).model_dump(mode="json") for record in records
    ]


@router.get("/clips/{clip_id}")
def clip(
    clip_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    from app.features.clip_generation.schemas import ClipCandidateResponse
    from app.features.editing.schemas import EditVersionResponse

    candidate = get_owned_candidate(session, clip_id, creator.id)
    versions = session.scalars(
        select(EditVersion)
        .where(EditVersion.candidate_id == candidate.id)
        .order_by(EditVersion.revision.desc())
    )
    return {
        "candidate": ClipCandidateResponse.model_validate(candidate),
        "versions": [EditVersionResponse.model_validate(v) for v in versions],
    }


@router.post("/clips/{clip_id}/exports", response_model=JobResponse, status_code=202)
def export(
    clip_id: UUID,
    payload: ExportRequest,
    idempotency_key: Key,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    candidate = get_owned_candidate(session, clip_id, creator.id)
    version = get_owned_edit_version(session, payload.edit_version_id, creator.id)
    if version.candidate_id != candidate.id:
        raise HTTPException(409, "The edit version belongs to another clip.")
    asset = get_owned_asset(session, version.asset_id, creator.id)
    return enqueue(
        session,
        creator,
        asset.project_id,
        JobType.MEDIA_EXPORT,
        idempotency_key,
        payload.model_dump(mode="json"),
    )


@router.get("/projects/{project_id}/exports", response_model=list[EditRenderResponse])
def exports(
    project_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    owned_project(session, creator.id, project_id)
    return list(
        session.scalars(
            select(EditRender)
            .join(Asset)
            .where(Asset.project_id == project_id, Asset.owner_id == creator.id)
            .order_by(EditRender.created_at.desc())
        )
    )


@router.get("/exports/{render_id}/delivery")
def delivery(
    render_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    storage: CloudinaryStorage = Depends(get_storage),
):
    render = owned_render(session, creator.id, render_id)
    if render.processing_status != "completed":
        raise HTTPException(409, "Export is not complete.")
    return {
        "url": storage.delivery_url(
            public_id=render.public_id, resource_type="video", asset_format="mp4"
        ),
        "expires_in": 300,
    }


@router.get("/projects/{project_id}/package")
def package(
    project_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    storage: CloudinaryStorage = Depends(get_storage),
):
    project = owned_project(session, creator.id, project_id)
    approved = (project.workflow_data or {}).get("approved_package")
    if not approved:
        raise HTTPException(409, "Approve an exported package first.")
    media = []
    for render_id in approved["render_ids"]:
        render = owned_render(session, creator.id, UUID(render_id))
        media.append(
            {
                **EditRenderResponse.model_validate(render).model_dump(mode="json"),
                "download_url": storage.delivery_url(
                    public_id=render.public_id, resource_type="video", asset_format="mp4"
                ),
            }
        )
    return {
        "project_id": str(project.id),
        "package": approved,
        "exports": media,
        "expires_in": 300,
        "publication_mode": "manual",
    }


@router.post("/jobs/{job_id}/review", response_model=JobResponse, status_code=202)
def review(
    job_id: UUID,
    payload: ReviewRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    job = JobRepository(session).get_owned(creator.id, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    if job.type != JobType.CLIP_GENERATION or job.status != "waiting_review":
        raise HTTPException(409, "This job is not waiting for clip review.")
    version = get_owned_edit_version(session, payload.edit_version_id, creator.id)
    candidates = job.input_snapshot.get("result", {}).get("candidate_ids", [])
    latest = session.scalar(
        select(EditVersion)
        .where(EditVersion.candidate_id == version.candidate_id)
        .order_by(EditVersion.revision.desc())
    )
    if str(version.candidate_id) not in candidates or latest.id != version.id:
        raise HTTPException(409, "Select the latest edit version of one of this job's candidates.")
    result = session.execute(
        update(Job)
        .where(Job.id == job.id, Job.status == "waiting_review")
        .values(
            status="queued",
            stage="awaiting_review_resume",
            input_snapshot={
                **job.input_snapshot,
                "review": payload.model_dump(mode="json"),
            },
        ),
        execution_options={"synchronize_session": False},
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "Review was already submitted.")
    session.commit()
    session.refresh(job)
    return job_response(job)
