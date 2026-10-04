"""Owner-scoped APIs for rendering platform-specific edit-version exports."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.media_workflow.router import Key, enqueue
from app.features.media_workflow.schemas import ExportRequest
from app.features.platform_exports.models import PlatformExport
from app.features.platform_exports.presets import PRESETS
from app.features.platform_exports.schemas import PlatformExportCreate, PlatformExportResponse
from app.features.platform_exports.service import (
    get_owned_platform_export,
    get_owned_version_asset,
    list_platform_exports,
)
from app.schemas import JobResponse, JobType

version_router = APIRouter()
router = APIRouter()


@version_router.post(
    "/{version_id}/platform-exports",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_export(
    version_id: UUID,
    payload: PlatformExportCreate,
    idempotency_key: Key,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    creator: AuthenticatedCreator = Depends(get_current_creator),
) -> JobResponse:
    version, asset = get_owned_version_asset(session, edit_version_id=version_id, owner_id=owner_id)
    title = payload.title or ((version.recipe.get("title") or {}).get("text") or "Short clip")
    request = ExportRequest(
        edit_version_id=version.id,
        preset=payload.preset.value,
        platform=PRESETS[payload.preset].platform,
        title=title[:160],
        caption=payload.supporting_copy or title,
        hashtags=payload.hashtags,
        fit=payload.fit,
    )
    return enqueue(
        session,
        creator,
        asset.project_id,
        JobType.MEDIA_EXPORT,
        idempotency_key,
        request.model_dump(mode="json"),
    )


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
