from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.repositories import ProjectRepository, project_summary
from app.schemas import ProjectCreate, ProjectSummary

router = APIRouter()


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
