"""Owner-scoped immutable edit versions and verified FFmpeg render endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.access import get_owned_asset
from app.features.assets.router import get_storage
from app.features.assets.storage import CloudinaryStorage
from app.features.editing.models import EditRender, EditVersion
from app.features.editing.render_service import EditRenderError, render_edit_version
from app.features.editing.schemas import (
    EditRenderResponse,
    EditVersionCreate,
    EditVersionResponse,
)
from app.features.editing.service import (
    EditConflictError,
    EditValidationError,
    create_edit_version,
    get_owned_candidate,
    get_owned_edit_version,
    list_edit_versions,
)

candidate_router = APIRouter()
router = APIRouter()


@candidate_router.post(
    "/{candidate_id}/edit-versions",
    response_model=EditVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    candidate_id: UUID,
    payload: EditVersionCreate,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> EditVersion:
    candidate = get_owned_candidate(session, candidate_id, owner_id)
    asset = get_owned_asset(session, candidate.asset_id, owner_id)
    try:
        return create_edit_version(session, candidate=candidate, asset=asset, payload=payload)
    except EditConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except EditValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@candidate_router.get("/{candidate_id}/edit-versions", response_model=list[EditVersionResponse])
def get_versions(
    candidate_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[EditVersion]:
    return list_edit_versions(session, candidate_id=candidate_id, owner_id=owner_id)


@router.get("/{version_id}", response_model=EditVersionResponse)
def get_version(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> EditVersion:
    return get_owned_edit_version(session, version_id, owner_id)


@router.post(
    "/{version_id}/render",
    response_model=EditRenderResponse,
    status_code=status.HTTP_201_CREATED,
)
def render_version(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    storage: CloudinaryStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> EditRender:
    version = get_owned_edit_version(session, version_id, owner_id)
    asset = get_owned_asset(session, version.asset_id, owner_id)
    try:
        return render_edit_version(
            session, version=version, asset=asset, storage=storage, settings=settings
        )
    except EditRenderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
