from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.access import get_owned_asset
from app.features.clip_generation.models import ClipCandidate
from app.features.clip_generation.schemas import ClipCandidateResponse, ClipGenerationCreate
from app.features.clip_generation.service import generate_candidates
from app.features.script_alignment.models import ScriptAlignment

router = APIRouter()


@router.post("/{asset_id}/clip-candidates", response_model=list[ClipCandidateResponse])
def create_clip_candidates(
    asset_id: UUID,
    payload: ClipGenerationCreate,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[ClipCandidate]:
    asset = get_owned_asset(session, asset_id, owner_id)
    alignments = list(
        session.scalars(
            select(ScriptAlignment)
            .where(ScriptAlignment.asset_id == asset.id)
            .order_by(ScriptAlignment.confidence.desc())
        )
    )
    try:
        return generate_candidates(
            session,
            asset=asset,
            alignments=alignments,
            max_candidates=payload.max_candidates,
            min_duration_ms=payload.min_duration_ms,
            max_duration_ms=payload.max_duration_ms,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.get("/{asset_id}/clip-candidates", response_model=list[ClipCandidateResponse])
def list_clip_candidates(
    asset_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[ClipCandidate]:
    asset = get_owned_asset(session, asset_id, owner_id)
    return list(
        session.scalars(
            select(ClipCandidate)
            .where(ClipCandidate.asset_id == asset.id)
            .order_by(ClipCandidate.score.desc())
        )
    )
