from collections import defaultdict
from datetime import UTC
from statistics import median
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.features.assets.models import Asset
from app.features.clip_generation.models import ClipCandidate
from app.features.content_workflow.service import owned_project
from app.features.editing.models import EditRender, EditVersion
from app.features.media_workflow.schemas import PerformanceInput
from app.models import PerformanceSnapshot, Project, Publication

router = APIRouter()


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


@router.post("/publications/{publication_id}/performance", status_code=201)
def save_performance(
    publication_id: UUID,
    payload: PerformanceInput,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    record = session.scalar(
        select(Publication)
        .join(Project)
        .where(Publication.id == publication_id, Project.owner_id == creator.id)
    )
    if record is None:
        raise HTTPException(404, "Publication not found.")
    if record.status != "published":
        raise HTTPException(409, "Confirm publication before entering performance.")
    if utc(payload.observed_at) < utc(record.published_at):
        raise HTTPException(422, "Observation cannot precede the actual publication.")
    snapshot = PerformanceSnapshot(publication_id=record.id, **payload.model_dump())
    session.add(snapshot)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "This observation already exists.") from error
    return {"id": str(snapshot.id), "source": snapshot.source}


@router.get("/projects/{project_id}/insights")
def insights(
    project_id: UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
):
    project = owned_project(session, creator.id, project_id)
    assets = list(session.scalars(select(Asset).where(Asset.project_id == project.id)))
    candidates = list(
        session.scalars(select(ClipCandidate).join(Asset).where(Asset.project_id == project.id))
    )
    versions = list(
        session.scalars(select(EditVersion).join(Asset).where(Asset.project_id == project.id))
    )
    exports = list(
        session.scalars(
            select(EditRender)
            .join(Asset)
            .where(Asset.project_id == project.id, EditRender.processing_status == "completed")
        )
    )
    publications = list(
        session.scalars(select(Publication).where(Publication.project_id == project.id))
    )
    pub_by_id = {p.id: p for p in publications}
    observations = list(
        session.scalars(
            select(PerformanceSnapshot)
            .join(Publication)
            .where(Publication.project_id == project.id)
            .order_by(PerformanceSnapshot.observed_at.desc())
        )
    )
    # Cumulative observations are never added: use latest per publication and window.
    latest = {}
    for observation in observations:
        latest.setdefault(
            (observation.publication_id, observation.reporting_window_days), observation
        )
    comparisons = []
    groups = defaultdict(list)
    for observation in latest.values():
        pub = pub_by_id[observation.publication_id]
        complete_counts = all(
            v is not None for v in (observation.likes, observation.comments, observation.shares)
        )
        rate = (
            (observation.likes + observation.comments + observation.shares) / observation.views
            if complete_counts and observation.views > 0
            else None
        )
        row = {
            "publication_id": str(pub.id),
            "snapshot_id": str(observation.id),
            "platform": pub.platform,
            "reporting_window_days": observation.reporting_window_days,
            "observed_at": utc(observation.observed_at).isoformat(),
            "source": observation.source,
            "views": observation.views,
            "engagement_rate": rate,
            "title": pub.supporting_copy.get("title"),
        }
        comparisons.append(row)
        groups[(pub.platform, observation.reporting_window_days)].append(row)
    recommendations = []
    for (platform, window), rows in groups.items():
        rated = [r for r in rows if r["engagement_rate"] is not None]
        best = max(rated, key=lambda r: r["engagement_rate"]) if rated else None
        recommendations.append(
            {
                "platform": platform,
                "reporting_window_days": window,
                "sample_size": len(rows),
                "evidence_snapshot_ids": [r["snapshot_id"] for r in rows],
                "message": (
                    f"Review the hook and format of '{best['title'] or best['publication_id']}', "
                    f"which has the highest entered engagement rate in this comparable group."
                    if best and len(rated) > 1
                    else "Enter complete metrics for more posts to compare hooks and formats."
                ),
                "limitation": "Small observational sample; this does not establish causation."
                if len(rows) < 3
                else "Observed performance association, not a causal prediction.",
            }
        )
    assets_by_id = {a.id: a for a in assets}
    elapsed = [
        (utc(r.created_at) - utc(assets_by_id[r.asset_id].created_at)).total_seconds()
        for r in exports
    ]
    return {
        "project_id": str(project.id),
        "production": {
            "projects_completed": int(project.workflow_stage == "published"),
            "source_minutes_processed": sum(
                (a.duration_ms or 0) / 60000 for a in assets if a.processing_status == "ready"
            ),
            "clips_produced": len(candidates),
            "exports_completed": len(exports),
            "clips_per_source": len(candidates) / len(assets) if assets else None,
            "revision_count": sum(v.revision > 1 for v in versions),
            "median_upload_to_export_seconds": median(elapsed) if elapsed else None,
        },
        "performance": comparisons,
        "recommendations": recommendations,
        "missing_data": [] if comparisons else ["No sourced performance observations yet."],
    }
