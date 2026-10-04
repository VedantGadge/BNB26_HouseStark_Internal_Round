from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.repositories import ProjectRepository, project_summary
from app.schemas import ProjectCreate, ProjectPatch, ProjectSummary

router = APIRouter()


@router.patch("/{project_id}")
def update_project(
    project_id: UUID,
    payload: ProjectPatch,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if project.workflow_stage == "published":
        raise HTTPException(409, "Published projects are preserved.")
    for key, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(project, key, value)
    from app.features.content_workflow.service import mark_inputs_changed

    mark_inputs_changed(session, project)
    session.commit()
    return project_summary(project)


@router.get("", response_model=list[ProjectSummary])
def list_projects(
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> list[ProjectSummary]:
    projects = ProjectRepository(session).list_owned(creator.id)
    return [project_summary(project) for project in projects]


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> ProjectSummary:
    return project_summary(ProjectRepository(session).create(creator.id, project))
