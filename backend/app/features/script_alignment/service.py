"""Deterministic, source-grounded baseline for mapping script beats to speech evidence."""

import re
from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.features.footage_analysis.models import TranscriptSegment
from app.features.script_alignment.models import ScriptAlignment

_TOKEN = re.compile(r"[a-z0-9']+")
_STOPWORDS = {"a", "and", "are", "for", "how", "i", "is", "it", "of", "the", "to", "you"}


def replace_alignments(
    session: Session,
    *,
    asset: Asset,
    script_text: str,
    transcript_segments: Sequence[TranscriptSegment],
) -> list[ScriptAlignment]:
    if not transcript_segments:
        raise ValueError("Footage must have transcript evidence before script alignment.")
    beats = _script_beats(script_text)
    if not beats:
        raise ValueError("The script did not contain a usable hook or beat.")
    session.execute(delete(ScriptAlignment).where(ScriptAlignment.asset_id == asset.id))
    saved: list[ScriptAlignment] = []
    for beat in beats:
        score, candidate = max(
            ((_score(beat, segment.text), segment) for segment in transcript_segments),
            key=lambda item: item[0],
        )
        if score <= 0:
            continue
        saved.append(
            ScriptAlignment(
                asset_id=asset.id,
                source_start_ms=candidate.source_start_ms,
                source_end_ms=candidate.source_end_ms,
                script_beat=beat,
                evidence_text=candidate.text,
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
