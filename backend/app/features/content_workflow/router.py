import uuid
from copy import deepcopy
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.features.assets.router import get_storage
from app.features.assets.storage import CloudinaryStorage
from app.features.content_workflow import service
from app.features.content_workflow.schemas import (
    PublicationInput,
    PublicationPatch,
    PublicationResponse,
    TransitionRequest,
    WorkflowPatch,
    WorkflowResponse,
)
from app.features.media_workflow.service import owned_render
from app.models import Publication

router = APIRouter()


@router.get("/{project_id}")
def get_project(
    project_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = service.owned_project(session, creator.id, project_id)
    return {
        "id": str(project.id),
        "name": project.name,
        "brief": project.brief,
        "audience": project.audience,
        "tone": project.tone,
        "current_script_version_id": str(project.current_script_version_id)
        if project.current_script_version_id
        else None,
        "target_platforms": project.target_platforms,
        "workflow_stage": project.workflow_stage,
    }


@router.get("/{project_id}/workflow", response_model=WorkflowResponse)
def get_workflow(
    project_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    return service.response(session, service.owned_project(session, creator.id, project_id))


@router.patch("/{project_id}/workflow", response_model=WorkflowResponse)
def patch_workflow(
    project_id: uuid.UUID,
    payload: WorkflowPatch,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    return service.patch_workflow(
        session, service.owned_project(session, creator.id, project_id), payload
    )


@router.post("/{project_id}/workflow/transitions", response_model=WorkflowResponse)
def transition(
    project_id: uuid.UUID,
    payload: TransitionRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    return service.transition(
        session, service.owned_project(session, creator.id, project_id), payload
    )


@router.get("/{project_id}/workflow/media")
def get_media(
    project_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    storage: CloudinaryStorage = Depends(get_storage),
):
    project = service.owned_project(session, creator.id, project_id)
    package = (project.workflow_data or {}).get("approved_package") or (
        project.workflow_data or {}
    ).get("package")
    if not package or not service.valid_package(session, project, package):
        raise HTTPException(409, "No completed rendered package is available.")
    render = owned_render(session, creator.id, uuid.UUID(package["render_ids"][0]))
    return RedirectResponse(
        storage.delivery_url(
            public_id=render.public_id,
            resource_type="video",
            asset_format="mp4",
        ),
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{project_id}/publications", response_model=list[PublicationResponse])
def get_publications(
    project_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = service.owned_project(session, creator.id, project_id)
    return [service.publication_response(p) for p in service.publications(session, project)]


@router.post("/{project_id}/publications", response_model=PublicationResponse, status_code=201)
def create_publication(
    project_id: uuid.UUID,
    payload: PublicationInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = service.owned_project(session, creator.id, project_id)
    service.check_revision(project, payload.expected_revision)
    if project.workflow_stage == "published":
        service.conflict("This publishing cycle is complete. Start a new project.")
    if project.target_platforms and payload.platform.value not in project.target_platforms:
        raise HTTPException(422, "Choose a target platform belonging to this project.")
    if any(p.platform == payload.platform.value for p in service.publications(session, project)):
        service.conflict("A publication already exists for this platform.")
    record = Publication(
        project_id=project.id,
        platform=payload.platform.value,
        planned_at=payload.planned_at.astimezone(UTC) if payload.planned_at else None,
        status="planned" if payload.planned_at else "draft",
        package_snapshot={},
        supporting_copy={
            key: value
            for key, value in {"title": payload.title, "caption": payload.caption}.items()
            if value is not None
        },
    )
    session.add(record)
    with session.no_autoflush:
        service.save(
            session,
            project,
            payload.expected_revision,
            deepcopy(project.workflow_data or {}),
            project.workflow_stage,
        )
    session.refresh(record)
    return service.publication_response(record)


@router.patch("/{project_id}/publications/{publication_id}", response_model=PublicationResponse)
def patch_publication(
    project_id: uuid.UUID,
    publication_id: uuid.UUID,
    payload: PublicationPatch,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = service.owned_project(session, creator.id, project_id)
    record = next(
        (p for p in service.publications(session, project) if p.id == publication_id), None
    )
    if record is None:
        raise HTTPException(404, "Publication not found.")
    service.check_revision(project, payload.expected_revision)
    if record.status == "published":
        if (
            payload.confirm_published
            and str(payload.external_url) == record.external_url
            and payload.published_at == service.publication_response(record)["published_at"]
        ):
            return service.publication_response(record)
        service.conflict("Published records are preserved and cannot be edited.")
    data = deepcopy(project.workflow_data or {})
    stage = project.workflow_stage
    if payload.confirm_published:
        if stage != "exported":
            service.conflict("Approve the package and mark it ready for download first.")
        reasons = service.blockers(session, project, data, "exported")
        if reasons:
            service.conflict(" ".join(reasons))
        render_ids = data["approved_package"]["render_ids"]
        selected = [owned_render(session, creator.id, uuid.UUID(value)) for value in render_ids]
        selected = [render for render in selected if render.platform == record.platform]
        if not selected:
            service.conflict("The approved package has no completed export for this platform.")
        record.status = "published"
        record.published_at = payload.published_at.astimezone(UTC)
        record.external_url = str(payload.external_url)
        record.package_snapshot = deepcopy(data["approved_package"])
        record.package_snapshot["export_id"] = str(selected[0].id)
        record.package_snapshot["edit_version_id"] = str(selected[0].edit_version_id)
        record.package_snapshot.update(record.supporting_copy)
        # Avoid flushing publication changes before acquiring the project revision.
        with session.no_autoflush:
            records = service.publications(session, project)
            required = set(project.target_platforms) or {p.platform for p in records}
            confirmed = {p.platform for p in records if p.status == "published"}
            if required and confirmed == required:
                stage = "published"
                data.setdefault("timestamps", {})[stage] = datetime.now(UTC).isoformat()
    else:
        if "planned_at" in payload.model_fields_set:
            record.planned_at = payload.planned_at.astimezone(UTC) if payload.planned_at else None
        record.supporting_copy = {
            **record.supporting_copy,
            **{
                key: value
                for key, value in {"title": payload.title, "caption": payload.caption}.items()
                if value is not None
            },
        }
        record.status = "planned" if record.planned_at else "draft"
    with session.no_autoflush:
        service.save(session, project, payload.expected_revision, data, stage)
    session.refresh(record)
    return service.publication_response(record)
