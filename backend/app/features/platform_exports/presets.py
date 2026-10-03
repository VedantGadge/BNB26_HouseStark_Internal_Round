"""Small, explicit export presets instead of unbounded per-platform configuration."""

from dataclasses import dataclass

from app.features.platform_exports.schemas import PlatformExportPreset


@dataclass(frozen=True)
class PresetDefinition:
    platform: str
    width: int
    height: int
    safe_top_px: int
    safe_bottom_px: int


PRESETS: dict[PlatformExportPreset, PresetDefinition] = {
    PlatformExportPreset.INSTAGRAM_REEL: PresetDefinition("instagram", 1080, 1920, 220, 360),
    PlatformExportPreset.TIKTOK: PresetDefinition("tiktok", 1080, 1920, 180, 380),
    PlatformExportPreset.YOUTUBE_SHORT: PresetDefinition("youtube", 1080, 1920, 160, 280),
    PlatformExportPreset.INSTAGRAM_FEED: PresetDefinition("instagram", 1080, 1080, 80, 130),
    PlatformExportPreset.LINKEDIN_FEED: PresetDefinition("linkedin", 1080, 1080, 80, 130),
    PlatformExportPreset.YOUTUBE_VIDEO: PresetDefinition("youtube", 1920, 1080, 70, 100),
}
