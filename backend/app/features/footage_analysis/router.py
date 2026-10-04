"""Owner-scoped footage-analysis retrieval endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.dependencies import get_current_owner_id
from app.features.assets.access import get_owned_asset
from app.features.footage_analysis.models import TranscriptSegment, VisualObservation
from app.features.footage_analysis.schemas import AssetAnalysisResponse

router = APIRouter()


@router.get("/{asset_id}/analysis", response_model=AssetAnalysisResponse)
def get_asset_analysis(
    asset_id: UUID,
    session: Session = Depends(get_db_session),
    owner_id: str = Depends(get_current_owner_id),
) -> AssetAnalysisResponse:
    asset = get_owned_asset(session, asset_id, owner_id)
    transcript_segments = list(
        session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.asset_id == asset.id)
            .order_by(TranscriptSegment.source_start_ms)
        )
    )
    visual_observations = list(
        session.scalars(
            select(VisualObservation)
            .where(VisualObservation.asset_id == asset.id)
            .order_by(VisualObservation.source_start_ms)
        )
    )
    return AssetAnalysisResponse(
        asset_id=asset.id,
        processing_status=asset.processing_status,
        processing_error=asset.processing_error,
        duration_ms=asset.duration_ms,
        transcript_segments=transcript_segments,
        visual_observations=visual_observations,
        updated_at=asset.updated_at,
    )
