"""Owner-scoped APIs for rendering platform-specific edit-version exports."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.router import get_storage
from app.features.assets.storage import CloudinaryStorage
from app.features.platform_exports.models import PlatformExport
from app.features.platform_exports.schemas import PlatformExportCreate, PlatformExportResponse
from app.features.platform_exports.service import (
    PlatformExportError,
    create_platform_export,
    get_owned_platform_export,
    get_owned_version_asset,
    list_platform_exports,
)

version_router = APIRouter()
router = APIRouter()


@version_router.post(
    "/{version_id}/platform-exports",
    response_model=PlatformExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_export(
    version_id: UUID,
    payload: PlatformExportCreate,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    storage: CloudinaryStorage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> PlatformExport:
    version, asset = get_owned_version_asset(
        session, edit_version_id=version_id, owner_id=owner_id
    )
    try:
        return create_platform_export(
            session,
            version=version,
            asset=asset,
            payload=payload,
            storage=storage,
            settings=settings,
        )
    except PlatformExportError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@version_router.get("/{version_id}/platform-exports", response_model=list[PlatformExportResponse])
def get_exports(
    version_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[PlatformExport]:
    return list_platform_exports(session, edit_version_id=version_id, owner_id=owner_id)


@router.get("/{export_id}", response_model=PlatformExportResponse)
def get_export(
    export_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> PlatformExport:
    return get_owned_platform_export(session, export_id, owner_id)
