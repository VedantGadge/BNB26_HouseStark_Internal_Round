"""Shared verified FFmpeg rendering for edit versions and platform exports."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import Settings
from app.features.assets.models import Asset
from app.features.assets.storage import CloudinaryStorage, UploadedAssetReference
from app.features.editing.models import EditRender, EditVersion
from app.features.editing.renderer import RenderCompilationError, render_recipe_to_mp4
from app.features.editing.schemas import EditRecipePayload
from app.features.footage_analysis.probe import probe_media


class EditRenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderedRecipeArtifact:
    uploaded: UploadedAssetReference
    width: int
    height: int
    duration_ms: int


def render_edit_version(
    session: Session,
    *,
    version: EditVersion,
    asset: Asset,
    storage: CloudinaryStorage,
    settings: Settings,
) -> EditRender:
    """Create one render record, render locally, verify it, then upload it."""

    recipe = EditRecipePayload.model_validate(version.recipe)
    render_id = uuid4()
    public_id = f"creatorai/edits/{version.id}/renders/{render_id}"
    render = EditRender(
        id=render_id,
        edit_version_id=version.id,
        asset_id=asset.id,
        public_id=public_id,
        processing_status="rendering",
    )
    session.add(render)
    session.commit()
    try:
        artifact = render_recipe_artifact(
            asset=asset,
            recipe=recipe,
            storage=storage,
            settings=settings,
            public_id=public_id,
        )
        render.provider_asset_id = artifact.uploaded.asset_id
        render.provider_version = artifact.uploaded.version
        render.width = artifact.width
        render.height = artifact.height
        render.duration_ms = artifact.duration_ms
        render.processing_status = "completed"
        render.processing_error = None
        session.commit()
        session.refresh(render)
        return render
    except Exception as error:
        render.processing_status = "failed"
        render.processing_error = str(error)[:1_000]
        session.commit()
        if isinstance(error, EditRenderError):
            raise
        if isinstance(error, RenderCompilationError):
            raise EditRenderError("FFmpeg could not render this edit recipe.") from error
        raise EditRenderError("The edit render failed.") from error


def render_recipe_artifact(
    *,
    asset: Asset,
    recipe: EditRecipePayload,
    storage: CloudinaryStorage,
    settings: Settings,
    public_id: str,
) -> RenderedRecipeArtifact:
    """Download, render, probe, and upload a recipe without owning persistence."""

    if asset.format is None:
        raise EditRenderError("The source asset has no downloadable format.")
    try:
        render_token = public_id.rsplit("/", 1)[-1]
        with TemporaryDirectory(prefix=f"creatorai-render-{render_token}-") as temporary_directory:
            working_directory = Path(temporary_directory)
            source_path = working_directory / f"source.{asset.format}"
            destination = working_directory / "edited.mp4"
            storage.download_original_to_path(
                public_id=asset.public_id,
                resource_type=asset.resource_type,
                asset_format=asset.format,
                destination=source_path,
            )
            source_probe = probe_media(source_path)
            render_recipe_to_mp4(
                source_path=source_path,
                destination=destination,
                recipe=recipe,
                has_audio=source_probe.has_audio,
                timeout_seconds=settings.edit_render_timeout_seconds,
            )
            probe = probe_media(destination)
            verify_render(probe, recipe=recipe)
            uploaded = storage.upload_authenticated_video_from_path(
                source_path=destination, public_id=public_id
            )
    except EditRenderError:
        raise
    except RenderCompilationError as error:
        raise EditRenderError("FFmpeg could not render this edit recipe.") from error
    except Exception as error:
        raise EditRenderError("The media render failed.") from error
    if probe.width is None or probe.height is None or probe.duration_ms is None:
        raise EditRenderError("Rendered output was missing verified media dimensions.")
    return RenderedRecipeArtifact(
        uploaded=uploaded,
        width=probe.width,
        height=probe.height,
        duration_ms=probe.duration_ms,
    )


def verify_render(probe: object, *, recipe: EditRecipePayload) -> None:
    expected_duration_ms = recipe.source_end_ms - recipe.source_start_ms
    width = getattr(probe, "width")
    height = getattr(probe, "height")
    duration_ms = getattr(probe, "duration_ms")
    video_codec = getattr(probe, "video_codec")
    if width != recipe.output.width or height != recipe.output.height:
        raise EditRenderError("Rendered output dimensions did not match the edit recipe.")
    if video_codec is None or duration_ms is None or duration_ms <= 0:
        raise EditRenderError("Rendered output is not a playable video.")
    if abs(duration_ms - expected_duration_ms) > 1_500:
        raise EditRenderError("Rendered output duration did not match the requested source range.")
