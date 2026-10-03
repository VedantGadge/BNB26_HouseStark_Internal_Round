"""Compatibility imports; transcription contracts belong to the footage-analysis feature."""

from app.features.footage_analysis.transcription import (
    TranscriptionNotConfigured,
    TranscriptionProvider,
    TranscriptSegmentResult,
    UnconfiguredTranscriptionProvider,
)

__all__ = [
    "TranscriptSegmentResult",
    "TranscriptionNotConfigured",
    "TranscriptionProvider",
    "UnconfiguredTranscriptionProvider",
]
