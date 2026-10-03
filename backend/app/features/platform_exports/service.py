"""Derive platform-safe recipe snapshots and persist their verified exports."""

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.features.assets.models import Asset
from app.features.assets.storage import CloudinaryStorage
from app.features.editing.models import EditVersion
from app.features.editing.render_service import EditRenderError, render_recipe_artifact
from app.features.editing.schemas import EditRecipePayload, OutputCanvas
from app.features.platform_exports.models import PlatformExport
from app.features.platform_exports.presets import PRESETS
from app.features.platform_exports.schemas import PlatformExportCreate, PlatformExportPreset


class PlatformExportError(RuntimeError):
    pass


def get_owned_platform_export(
    session: Session, export_id: UUID, owner_id: str
) -> PlatformExport:
    export = session.scalar(
        select(PlatformExport)
        .join(Asset, PlatformExport.asset_id == Asset.id)
        .where(PlatformExport.id == export_id, Asset.owner_id == owner_id)
    )
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Platform export not found."
        )
    return export


def list_platform_exports(
    session: Session, *, edit_version_id: UUID, owner_id: str
) -> list[PlatformExport]:
    _get_owned_version_asset(session, edit_version_id=edit_version_id, owner_id=owner_id)
    return list(
        session.scalars(
            select(PlatformExport)
            .where(PlatformExport.edit_version_id == edit_version_id)
            .order_by(PlatformExport.created_at.desc())
        )
    )


def create_platform_export(
    session: Session,
    *,
    version: EditVersion,
    asset: Asset,
    payload: PlatformExportCreate,
    storage: CloudinaryStorage,
    settings: Settings,
) -> PlatformExport:
    definition = PRESETS[payload.preset]
    recipe = derive_platform_recipe(version, preset=payload.preset)
    export_id = uuid4()
    public_id = f"creatorai/platform-exports/{version.id}/{payload.preset.value}/{export_id}"
    export = PlatformExport(
        id=export_id,
        edit_version_id=version.id,
        asset_id=asset.id,
        preset=payload.preset.value,
        platform=definition.platform,
        derived_recipe=recipe.model_dump(mode="json"),
        supporting_copy=payload.supporting_copy,
        hashtags=payload.hashtags,
        public_id=public_id,
        processing_status="rendering",
    )
    session.add(export)
    session.commit()
    try:
        artifact = render_recipe_artifact(
            asset=asset,
            recipe=recipe,
            storage=storage,
            settings=settings,
            public_id=public_id,
        )
        export.provider_asset_id = artifact.uploaded.asset_id
        export.provider_version = artifact.uploaded.version
        export.width = artifact.width
        export.height = artifact.height
        export.duration_ms = artifact.duration_ms
        export.processing_status = "completed"
        export.processing_error = None
        session.commit()
        session.refresh(export)
        return export
    except Exception as error:
        export.processing_status = "failed"
        export.processing_error = str(error)[:1_000]
        session.commit()
        if isinstance(error, PlatformExportError):
            raise
        if isinstance(error, EditRenderError):
            raise PlatformExportError("FFmpeg could not create this platform export.") from error
        raise PlatformExportError("The platform export failed.") from error


def derive_platform_recipe(
    version: EditVersion, *, preset: PlatformExportPreset
) -> EditRecipePayload:
    """Snapshot one edit version with only preset-owned output and safe-zone changes."""

    base_recipe = EditRecipePayload.model_validate(version.recipe)
    definition = PRESETS[preset]
    canvas = OutputCanvas(
        width=definition.width,
        height=definition.height,
        safe_top_px=definition.safe_top_px,
        safe_bottom_px=definition.safe_bottom_px,
    )
    return base_recipe.model_copy(update={"output": canvas}, deep=True)


def _get_owned_version_asset(
    session: Session, *, edit_version_id: UUID, owner_id: str
) -> tuple[EditVersion, Asset]:
    result = session.execute(
        select(EditVersion, Asset)
        .join(Asset, EditVersion.asset_id == Asset.id)
        .where(EditVersion.id == edit_version_id, Asset.owner_id == owner_id)
    ).one_or_none()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit version not found.")
    return result


def get_owned_version_asset(
    session: Session, *, edit_version_id: UUID, owner_id: str
) -> tuple[EditVersion, Asset]:
    """Public owner-scoped lookup shared by the platform-export router."""

    return _get_owned_version_asset(session, edit_version_id=edit_version_id, owner_id=owner_id)
