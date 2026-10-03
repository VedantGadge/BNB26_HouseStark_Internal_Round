"""Derive platform-safe recipe snapshots and persist their verified exports."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.features.assets.models import Asset
from app.features.assets.storage import CloudinaryStorage
from app.features.editing.models import EditVersion
from app.features.editing.render_service import render_edit_version
from app.features.editing.schemas import EditRecipePayload, OutputCanvas
from app.features.platform_exports.models import PlatformExport
from app.features.platform_exports.presets import PRESETS
from app.features.platform_exports.schemas import PlatformExportCreate, PlatformExportPreset


class PlatformExportError(RuntimeError):
    pass


def platform_recipe(version, *, preset, platform, fit):
    """Named Yash presets are canonical; retain generic aspect-ratio API aliases."""
    aliases = {
        "vertical": {"tiktok": "tiktok", "youtube": "youtube_short"}.get(
            platform, "instagram_reel"
        ),
        "square": "linkedin_feed" if platform == "linkedin" else "instagram_feed",
        "landscape": "youtube_video",
    }
    selected = PlatformExportPreset(aliases.get(preset, preset))
    recipe = derive_platform_recipe(version, preset=selected)
    recipe.output.fit = fit
    return selected, recipe


def record_verified_export(session, *, render, preset):
    """One platform-variant record references one authoritative rendered artifact."""
    existing = session.get(PlatformExport, render.id)
    if existing:
        return existing
    record = PlatformExport(
        id=render.id,
        render_id=render.id,
        edit_version_id=render.edit_version_id,
        asset_id=render.asset_id,
        preset=str(preset),
        platform=render.platform,
        derived_recipe=render.recipe_snapshot,
        supporting_copy=render.supporting_copy.get("caption"),
        hashtags=render.supporting_copy.get("hashtags", []),
        public_id=render.public_id,
        provider_asset_id=render.provider_asset_id,
        provider_version=render.provider_version,
        format=render.format,
        width=render.width,
        height=render.height,
        duration_ms=render.duration_ms,
        processing_status=render.processing_status,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_owned_platform_export(session: Session, export_id: UUID, owner_id: str) -> PlatformExport:
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
    recipe = derive_platform_recipe(version, preset=payload.preset)
    recipe.output.fit = payload.fit
    render = render_edit_version(
        session,
        version=version,
        asset=asset,
        storage=storage,
        settings=settings,
        preset_name=payload.preset.value,
        platform=PRESETS[payload.preset].platform,
        supporting_copy={
            "title": payload.title,
            "caption": payload.supporting_copy,
            "hashtags": payload.hashtags,
        },
        recipe_override=recipe,
    )
    return record_verified_export(session, render=render, preset=payload.preset)


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
