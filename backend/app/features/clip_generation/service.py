from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.clip_generation.models import ClipCandidate
from app.features.script_alignment.models import ScriptAlignment


def generate_candidates(
    session: Session,
    *,
    asset: Asset,
    alignments: Sequence[ScriptAlignment],
    max_candidates: int,
    min_duration_ms: int,
    max_duration_ms: int,
) -> list[ClipCandidate]:
    if min_duration_ms > max_duration_ms:
        raise ValueError("min_duration_ms must not exceed max_duration_ms.")
    if not alignments:
        raise ValueError("Generate script alignments before generating clip candidates.")
    session.execute(delete(ClipCandidate).where(ClipCandidate.asset_id == asset.id))
    ranked = sorted(alignments, key=lambda alignment: alignment.confidence, reverse=True)
    candidates: list[ClipCandidate] = []
    for alignment in ranked:
        start_ms, end_ms = _bounded_window(
            alignment.source_start_ms,
            alignment.source_end_ms,
            asset.duration_ms,
            min_duration_ms,
            max_duration_ms,
        )
        if any(
            _overlaps(start_ms, end_ms, item.source_start_ms, item.source_end_ms)
            for item in candidates
        ):
            continue
        candidates.append(
            ClipCandidate(
                asset_id=asset.id,
                source_start_ms=start_ms,
                source_end_ms=end_ms,
                hook=alignment.script_beat,
                transcript_text=alignment.evidence_text,
                score=alignment.confidence,
                reasons=["script-alignment", "timestamped-transcript-evidence"],
            )
        )
        if len(candidates) >= max_candidates:
            break
    session.add_all(candidates)
    session.commit()
    return candidates


def _bounded_window(
    start_ms: int,
    end_ms: int,
    duration_ms: int | None,
    min_duration_ms: int,
    max_duration_ms: int,
) -> tuple[int, int]:
    center = (start_ms + end_ms) // 2
    length = min(max(end_ms - start_ms, min_duration_ms), max_duration_ms)
    start = max(center - length // 2, 0)
    end = start + length
    if duration_ms is not None and end > duration_ms:
        end = duration_ms
        start = max(end - length, 0)
    return start, end


def _overlaps(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end
