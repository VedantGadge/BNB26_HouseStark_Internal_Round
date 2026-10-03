"""Persist provider results after source-clock validation."""

from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.features.footage_analysis.transcription import TranscriptSegmentResult
from app.features.footage_analysis.vision import VisualObservationResult


def replace_transcript_segments(
    session: Session, *, asset: Asset, segments: Sequence[TranscriptSegmentResult]
) -> list[TranscriptSegment]:
    for segment in segments:
        _validate_time_range(
            asset,
            segment.source_start_ms,
            segment.source_end_ms,
            "Transcript segment",
        )
        if not segment.text.strip():
            raise ValueError("Transcript segment text must not be blank.")
    session.execute(delete(TranscriptSegment).where(TranscriptSegment.asset_id == asset.id))
    persisted = [
        TranscriptSegment(
            asset_id=asset.id,
            source_start_ms=segment.source_start_ms,
            source_end_ms=segment.source_end_ms,
            text=segment.text.strip(),
            word_timings=segment.word_timings,
        )
        for segment in segments
    ]
    session.add_all(persisted)
    return persisted


def replace_visual_observations(
    session: Session, *, asset: Asset, observations: Sequence[VisualObservationResult]
) -> list[VisualObservation]:
    for observation in observations:
        _validate_time_range(
            asset,
            observation.source_start_ms,
            observation.source_end_ms,
            "Visual observation",
            allow_point=True,
        )
        if not observation.description.strip():
            raise ValueError("Visual observation description must not be blank.")
        if observation.confidence is not None and not 0 <= observation.confidence <= 1:
            raise ValueError("Visual observation confidence must be between zero and one.")
    session.execute(delete(VisualObservation).where(VisualObservation.asset_id == asset.id))
    persisted = [
        VisualObservation(
            asset_id=asset.id,
            source_start_ms=observation.source_start_ms,
            source_end_ms=observation.source_end_ms,
            frame_references=observation.frame_references,
            description=observation.description.strip(),
            confidence=observation.confidence,
        )
        for observation in observations
    ]
    session.add_all(persisted)
    return persisted


def _validate_time_range(
    asset: Asset, start_ms: int, end_ms: int, label: str, *, allow_point: bool = False
) -> None:
    if start_ms < 0 or end_ms < start_ms or (not allow_point and end_ms == start_ms):
        raise ValueError(f"{label} has an invalid source time range.")
    if asset.duration_ms is not None and end_ms > asset.duration_ms:
        raise ValueError(f"{label} extends beyond the source asset duration.")
