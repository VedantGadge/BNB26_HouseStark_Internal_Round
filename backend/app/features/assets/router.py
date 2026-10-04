"""Owner-scoped Cloudinary upload, verification, and asset-library endpoints."""

from uuid import UUID, uuid4

import cloudinary.exceptions
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.access import get_owned_asset, get_owned_project
from app.features.assets.models import Asset
from app.features.assets.schemas import (
    AssetProcessingStatus,
    AssetResponse,
    AssetUploadComplete,
    AssetUploadSession,
    AssetUploadSessionCreate,
)
from app.features.assets.storage import CloudinaryStorage
from app.features.script_creation.jobs import JobRepository
from app.schemas import JobType

router = APIRouter()
project_router = APIRouter()


def get_storage(settings: Settings = Depends(get_settings)) -> CloudinaryStorage:
    if not all(
        [
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudinary storage is not configured.",
        )
    return CloudinaryStorage(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )


@project_router.post(
    "/{project_id}/assets/upload-session",
    response_model=AssetUploadSession,
    status_code=status.HTTP_201_CREATED,
)
def create_upload_session(
    project_id: UUID,
    payload: AssetUploadSessionCreate,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    storage: CloudinaryStorage = Depends(get_storage),
) -> AssetUploadSession:
    get_owned_project(session, project_id, owner_id)
    asset_id = uuid4()
    resource_type = "image" if payload.kind.value == "image" else "video"
    public_id = f"creatorai/projects/{project_id}/assets/{asset_id}"
    asset = Asset(
        id=asset_id,
        project_id=project_id,
        owner_id=owner_id,
        kind=payload.kind.value,
        public_id=public_id,
        resource_type=resource_type,
        delivery_type="authenticated",
        tags=payload.tags,
        processing_status=AssetProcessingStatus.UPLOADING.value,
    )
    session.add(asset)
    session.commit()
    return AssetUploadSession(
        asset_id=asset_id,
        **storage.create_upload_session(public_id=public_id, resource_type=resource_type),
    )


@router.post("/{asset_id}/complete", response_model=AssetResponse)
def complete_upload(
    asset_id: UUID,
    payload: AssetUploadComplete,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    storage: CloudinaryStorage = Depends(get_storage),
) -> Asset:
    asset = get_owned_asset(session, asset_id, owner_id)
    if asset.processing_status != AssetProcessingStatus.UPLOADING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This asset upload has already been completed or cannot be completed.",
        )
    try:
        provider_asset = storage.get_asset_metadata(
            public_id=asset.public_id, resource_type=asset.resource_type
        )
    except cloudinary.exceptions.Error as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cloudinary could not verify the uploaded asset.",
        ) from error
    if (
        provider_asset.get("asset_id") != payload.provider_asset_id
        or str(provider_asset.get("version")) != payload.provider_version
        or provider_asset.get("public_id") != asset.public_id
        or provider_asset.get("resource_type") != asset.resource_type
        or provider_asset.get("type") != asset.delivery_type
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cloudinary completion metadata did not match the authorized upload.",
        )
    asset.provider_asset_id = provider_asset["asset_id"]
    asset.provider_version = str(provider_asset["version"])
    asset.format = provider_asset.get("format")
    asset.byte_size = provider_asset.get("bytes")
    asset.width = provider_asset.get("width")
    asset.height = provider_asset.get("height")
    duration_seconds = provider_asset.get("duration")
    asset.duration_ms = (
        round(float(duration_seconds) * 1000) if duration_seconds is not None else None
    )
    asset.processing_status = AssetProcessingStatus.UPLOADED.value
    JobRepository(session).enqueue(
        owner_id=owner_id,
        project_id=asset.project_id,
        job_type=JobType.ASSET_INGESTION,
        idempotency_key=f"ingest:{asset.id}",
        input_snapshot={"asset_id": str(asset.id)},
        routing_snapshot={},
    )
    session.refresh(asset)
    return asset


@router.get("/{asset_id}/delivery")
def asset_delivery(
    asset_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
    storage: CloudinaryStorage = Depends(get_storage),
) -> dict:
    asset = get_owned_asset(session, asset_id, owner_id)
    if not asset.format or asset.processing_status == "uploading":
        raise HTTPException(409, "Finish uploading this asset before playback.")
    return {
        "url": storage.delivery_url(
            public_id=asset.public_id, resource_type=asset.resource_type, asset_format=asset.format
        ),
        "expires_in": 300,
    }


@project_router.get("/{project_id}/assets", response_model=list[AssetResponse])
def list_assets(
    project_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[Asset]:
    get_owned_project(session, project_id, owner_id)
    return list(
        session.scalars(
            select(Asset)
            .where(Asset.project_id == project_id, Asset.owner_id == owner_id)
            .order_by(Asset.created_at.desc())
        )
    )
