"""Compatibility imports; vision contracts belong to the footage-analysis feature."""

from app.features.footage_analysis.vision import (
    UnconfiguredVisionProvider,
    VisionNotConfigured,
    VisionProvider,
    VisualObservationResult,
)

__all__ = [
    "UnconfiguredVisionProvider",
    "VisionNotConfigured",
    "VisionProvider",
    "VisualObservationResult",
]
