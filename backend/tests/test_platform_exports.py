from uuid import uuid4

from app.features.editing.models import EditVersion
from app.features.editing.schemas import EditRecipePayload, TitleOverlay
from app.features.platform_exports.schemas import PlatformExportCreate, PlatformExportPreset
from app.features.platform_exports.service import derive_platform_recipe


def test_platform_presets_create_independent_safe_recipe_snapshots() -> None:
    version = EditVersion(
        id=uuid4(),
        candidate_id=uuid4(),
        asset_id=uuid4(),
        revision=2,
        author_type="creator",
        recipe=EditRecipePayload(
            source_start_ms=2_000,
            source_end_ms=12_000,
            title=TitleOverlay(text="A strong hook"),
        ).model_dump(mode="json"),
    )

    square = derive_platform_recipe(version, preset=PlatformExportPreset.INSTAGRAM_FEED)
    landscape = derive_platform_recipe(version, preset=PlatformExportPreset.YOUTUBE_VIDEO)

    assert (square.output.width, square.output.height) == (1080, 1080)
    assert (square.output.safe_top_px, square.output.safe_bottom_px) == (80, 130)
    assert (landscape.output.width, landscape.output.height) == (1920, 1080)
    assert (landscape.output.safe_top_px, landscape.output.safe_bottom_px) == (70, 100)
    assert square.source_start_ms == landscape.source_start_ms == 2_000
    assert square.title is not None and landscape.title is not None


def test_platform_export_metadata_normalizes_hashtags() -> None:
    request = PlatformExportCreate(
        preset=PlatformExportPreset.TIKTOK,
        supporting_copy="A creator-ready caption.",
        hashtags=[" #Writing ", "creatorai"],
    )

    assert request.hashtags == ["Writing", "creatorai"]
