from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.access import get_owned_asset
from app.features.footage_analysis.models import TranscriptSegment
from app.features.script_alignment.models import ScriptAlignment
from app.features.script_alignment.schemas import ScriptAlignmentCreate, ScriptAlignmentResponse
from app.features.script_alignment.service import replace_alignments

router = APIRouter()


@router.post("/{asset_id}/script-alignments", response_model=list[ScriptAlignmentResponse])
def create_script_alignments(
    asset_id: UUID,
    payload: ScriptAlignmentCreate,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[ScriptAlignment]:
    asset = get_owned_asset(session, asset_id, owner_id)
    transcript_segments = list(
        session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.asset_id == asset.id)
            .order_by(TranscriptSegment.source_start_ms)
        )
    )
    try:
        return replace_alignments(
            session,
            asset=asset,
            script_text=payload.script_text,
            transcript_segments=transcript_segments,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.get("/{asset_id}/script-alignments", response_model=list[ScriptAlignmentResponse])
def list_script_alignments(
    asset_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> list[ScriptAlignment]:
    asset = get_owned_asset(session, asset_id, owner_id)
    return list(
        session.scalars(select(ScriptAlignment).where(ScriptAlignment.asset_id == asset.id))
    )
