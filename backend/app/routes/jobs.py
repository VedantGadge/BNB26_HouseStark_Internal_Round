import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.database import get_session
from app.features.script_creation.insight_report import build_insight_report
from app.features.script_creation.jobs import JobRepository, job_response
from app.schemas import JobResponse, JobStatus, JobType

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> JobResponse:
    job = JobRepository(session).get_owned(creator.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job_response(job)


@router.get("/{job_id}/insight-report.pdf")
def download_insight_report(
    job_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> Response:
    job = JobRepository(session).get_owned(creator.id, job_id)
    if job is None or job.type != JobType.INSIGHT_SUMMARY.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Insight report not found."
        )
    result = job.input_snapshot.get("result")
    facts = job.input_snapshot.get("facts")
    if job.status != JobStatus.COMPLETED.value or not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Insight report is not ready."
        )
    if not isinstance(facts, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Insight evidence is unavailable."
        )
    try:
        content = build_insight_report(facts, result)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="creatorai-insight-{job.id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/{job_id}/retry", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_job(
    job_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> JobResponse:
    try:
        job = JobRepository(session).requeue_failed(creator.id, job_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job_response(job)
