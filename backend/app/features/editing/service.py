"""Recipe creation, ownership-safe lookup, and optimistic edit versioning."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.clip_generation.models import ClipCandidate
from app.features.editing.models import EditVersion
from app.features.editing.schemas import (
    CaptionItem,
    CaptionStyle,
    EditRecipePayload,
    EditVersionCreate,
    EmphasisZoom,
    TitleOverlay,
)
from app.features.footage_analysis.models import TranscriptSegment


class EditConflictError(ValueError):
    pass


class EditValidationError(ValueError):
    pass


def get_owned_candidate(session: Session, candidate_id: UUID, owner_id: str) -> ClipCandidate:
    candidate = session.scalar(
        select(ClipCandidate)
        .join(Asset, ClipCandidate.asset_id == Asset.id)
        .where(ClipCandidate.id == candidate_id, Asset.owner_id == owner_id)
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clip candidate not found."
        )
    return candidate


def get_owned_edit_version(session: Session, version_id: UUID, owner_id: str) -> EditVersion:
    version = session.scalar(
        select(EditVersion)
        .join(Asset, EditVersion.asset_id == Asset.id)
        .where(EditVersion.id == version_id, Asset.owner_id == owner_id)
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit version not found.")
    return version


def list_edit_versions(session: Session, *, candidate_id: UUID, owner_id: str) -> list[EditVersion]:
    get_owned_candidate(session, candidate_id, owner_id)
    return list(
        session.scalars(
            select(EditVersion)
            .where(EditVersion.candidate_id == candidate_id)
            .order_by(EditVersion.revision.desc())
        )
    )


def create_edit_version(
    session: Session,
    *,
    candidate: ClipCandidate,
    asset: Asset,
    payload: EditVersionCreate,
) -> EditVersion:
    latest = session.scalar(
        select(EditVersion)
        .where(EditVersion.candidate_id == candidate.id)
        .order_by(EditVersion.revision.desc())
        .limit(1)
    )
    if latest is None and payload.base_version_id is not None:
        raise EditConflictError("The requested base edit version does not exist.")
    if latest is not None and payload.base_version_id != latest.id:
        raise EditConflictError("The edit has changed; reload the latest version before saving.")
    if latest is not None and payload.recipe is None:
        raise EditValidationError("A recipe is required when saving a revised edit version.")

    recipe = payload.recipe or build_assisted_recipe(session, candidate=candidate)
    validate_recipe_for_asset(recipe, asset=asset)
    version = EditVersion(
        candidate_id=candidate.id,
        asset_id=asset.id,
        revision=1 if latest is None else latest.revision + 1,
        parent_version_id=latest.id if latest is not None else None,
        author_type="assistant" if payload.recipe is None else "creator",
        recipe=recipe.model_dump(mode="json"),
    )
    session.add(version)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise EditConflictError(
            "The edit changed while saving. Reload the latest version."
        ) from error
    session.refresh(version)
    return version


def build_assisted_recipe(session: Session, *, candidate: ClipCandidate) -> EditRecipePayload:
    """Seed a useful draft from existing grounded candidate and transcript evidence."""

    source_start_ms = candidate.source_start_ms
    source_end_ms = candidate.source_end_ms
    duration_ms = source_end_ms - source_start_ms
    segments = list(
        session.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.asset_id == candidate.asset_id,
                TranscriptSegment.source_end_ms > source_start_ms,
                TranscriptSegment.source_start_ms < source_end_ms,
            )
            .order_by(TranscriptSegment.source_start_ms)
            .limit(20)
        )
    )
    captions = [
        CaptionItem(
            start_ms=max(segment.source_start_ms, source_start_ms) - source_start_ms,
            end_ms=min(segment.source_end_ms, source_end_ms) - source_start_ms,
            text=segment.text.strip()[:240],
        )
        for segment in segments
        if segment.text.strip()
        and min(segment.source_end_ms, source_end_ms)
        > max(segment.source_start_ms, source_start_ms)
    ]
    zooms = []
    if duration_ms >= 8_000:
        zoom_start_ms = min(max(duration_ms // 3, 2_000), duration_ms - 2_000)
        zooms = [
            EmphasisZoom(
                start_ms=zoom_start_ms,
                end_ms=min(zoom_start_ms + 1_800, duration_ms),
                scale=1.07,
            )
        ]
    return EditRecipePayload(
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        captions_enabled=True,
        caption_style=CaptionStyle.BOLD_HIGHLIGHT,
        captions=captions,
        title=TitleOverlay(text=candidate.hook[:140], end_ms=min(3_000, duration_ms)),
        emphasis_zooms=zooms,
    )


def validate_recipe_for_asset(recipe: EditRecipePayload, *, asset: Asset) -> None:
    if asset.kind != "video" or asset.duration_ms is None:
        raise EditValidationError("Editable recipes require an ingested video asset.")
    if asset.processing_status != "ready":
        raise EditValidationError("Only a ready video asset can be edited.")
    if recipe.source_end_ms > asset.duration_ms:
        raise EditValidationError("The edit range extends beyond the source video duration.")
    output_duration_ms = recipe.source_end_ms - recipe.source_start_ms
    timed_items = [*recipe.captions, *recipe.emphasis_zooms]
    if recipe.title is not None:
        timed_items.append(recipe.title)
    for item in timed_items:
        if item.end_ms > output_duration_ms:
            raise EditValidationError("An edit operation extends beyond the output duration.")
