"""Compatibility imports; analysis persistence belongs to the footage-analysis feature."""

from app.features.footage_analysis.persistence import (
    replace_transcript_segments,
    replace_visual_observations,
)

__all__ = ["replace_transcript_segments", "replace_visual_observations"]
