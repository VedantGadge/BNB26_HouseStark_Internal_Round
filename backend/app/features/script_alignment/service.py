"""Deterministic, source-grounded baseline for mapping script beats to speech evidence."""

import re
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.features.script_alignment.models import ScriptAlignment

_TOKEN = re.compile(r"[a-z0-9']+")
_STOPWORDS = {"a", "and", "are", "for", "how", "i", "is", "it", "of", "the", "to", "you"}


def replace_alignments(
    session: Session,
    *,
    asset: Asset,
    script_text: str,
    transcript_segments: Sequence[TranscriptSegment],
    visual_observations: Sequence[VisualObservation] = (),
    script_version_id: UUID | None = None,
    sections: Sequence[dict] | None = None,
    semantic_matches: dict | None = None,
) -> list[ScriptAlignment]:
    if asset.processing_status != "ready":
        raise ValueError("Analyze the asset before script alignment.")
    if not transcript_segments and not visual_observations:
        raise ValueError("Footage must have transcript or visual evidence before alignment.")
    beats = sections or [{"id": None, "text": text} for text in _script_beats(script_text)]
    if not beats:
        raise ValueError("The script did not contain a usable hook or beat.")
    session.execute(delete(ScriptAlignment).where(ScriptAlignment.asset_id == asset.id))
    saved: list[ScriptAlignment] = []
    for section in beats:
        beat = section["text"]
        evidence = [
            (_score(beat, segment.text), segment, "transcript") for segment in transcript_segments
        ] + [
            (_score(beat, observation.description), observation, "visual")
            for observation in visual_observations
        ]
        score, candidate, kind = max(evidence, key=lambda item: item[0])
        semantic = semantic_matches.get(section["id"]) if semantic_matches is not None else None
        if semantic is not None:
            score = semantic.confidence
            if semantic.evidence_id:
                _, candidate, kind = next(
                    item for item in evidence if str(item[1].id) == semantic.evidence_id
                )
        start = candidate.source_start_ms if score else 0
        end = candidate.source_end_ms if score else 0
        if score and end == start:
            end = min(start + 2_000, asset.duration_ms or start + 2_000)
        visuals = [
            {
                "id": str(v.id),
                "description": v.description,
                "source_start_ms": v.source_start_ms,
                "frame_references": v.frame_references,
            }
            for v in visual_observations
            if score and start <= v.source_start_ms <= end
        ]
        saved.append(
            ScriptAlignment(
                asset_id=asset.id,
                script_version_id=script_version_id,
                section_id=section.get("id"),
                match_status=semantic.status
                if semantic
                else ("unmatched" if not score else "matched" if score >= 0.5 else "partial"),
                visual_evidence=visuals,
                source_start_ms=start,
                source_end_ms=end,
                script_beat=beat,
                evidence_text=(candidate.text if kind == "transcript" else candidate.description)
                if score
                else "No supporting source evidence found.",
                confidence=score,
            )
        )
    session.add_all(saved)
    session.commit()
    return saved


def _script_beats(script_text: str) -> list[str]:
    candidates = re.split(r"(?:\r?\n)+|(?<=[.!?])\s+", script_text.strip())
    return [candidate.strip() for candidate in candidates if candidate.strip()][:30]


def _score(beat: str, evidence: str) -> float:
    beat_tokens = _tokens(beat)
    evidence_tokens = _tokens(evidence)
    if not beat_tokens or not evidence_tokens:
        return 0.0
    return round(len(beat_tokens & evidence_tokens) / len(beat_tokens), 3)


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(text.lower()) if token not in _STOPWORDS}
