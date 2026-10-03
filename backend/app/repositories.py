import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Project
from app.schemas import ProjectCreate, ProjectSummary


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, owner_id: str, payload: ProjectCreate) -> Project:
        project = Project(
            owner_id=owner_id,
            name=payload.name,
            brief=payload.brief,
            audience=payload.audience,
            tone=payload.tone,
            target_platforms=[platform.value for platform in payload.target_platforms],
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def list_owned(self, owner_id: str) -> list[Project]:
        statement: Select[tuple[Project]] = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc(), Project.id.desc())
        )
        return list(self.session.scalars(statement))

    def get_owned(self, owner_id: str, project_id: uuid.UUID) -> Project | None:
        statement: Select[tuple[Project]] = select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
        )
        return self.session.scalar(statement)


def project_summary(project: Project) -> ProjectSummary:
    return ProjectSummary(
        id=str(project.id),
        name=project.name,
        workflow_stage=project.workflow_stage,
    )
