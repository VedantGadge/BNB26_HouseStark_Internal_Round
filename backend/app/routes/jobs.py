from fastapi import APIRouter, HTTPException, status

from app.schemas import JobResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Job persistence is not configured; cannot load job {job_id}.",
    )
