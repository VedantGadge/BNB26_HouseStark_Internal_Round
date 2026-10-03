from fastapi import APIRouter, HTTPException, status

from app.schemas import ProjectCreate, ProjectSummary

router = APIRouter()


def persistence_not_configured() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Project persistence is not configured yet. "
            "Complete the Neon repository in Phase 1."
        ),
    )


@router.get("", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    raise persistence_not_configured()


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
def create_project(_project: ProjectCreate) -> ProjectSummary:
    raise persistence_not_configured()
