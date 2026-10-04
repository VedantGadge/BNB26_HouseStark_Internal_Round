from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.features.script_creation.jobs import IdempotencyConflictError, JobRepository
from app.models import Base
from app.repositories import ProjectRepository
from app.schemas import JobStatus, JobType, Platform, ProjectCreate


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)


def create_project(session: Session):
    return ProjectRepository(session).create(
        "creator-a",
        ProjectCreate(
            name="Queue test",
            brief="Write a creator-friendly script about a useful product.",
            target_platforms=[Platform.INSTAGRAM],
        ),
    )


def enqueue_script_job(session: Session, key: str = "request-1"):
    project = create_project(session)
    return JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.SCRIPT_GENERATION,
        idempotency_key=key,
        input_snapshot={"brief": "A useful product"},
        routing_snapshot={"default_model": "free/model"},
    )


def test_enqueue_returns_original_job_for_same_idempotency_key(session: Session) -> None:
    original = enqueue_script_job(session)
    repeated = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=original.project_id,
        job_type=JobType.SCRIPT_GENERATION,
        idempotency_key="request-1",
        input_snapshot={"brief": "A useful product"},
        routing_snapshot={"default_model": "free/model"},
    )

    assert repeated.id == original.id
    assert repeated.status == JobStatus.QUEUED.value


def test_enqueue_rejects_changed_input_for_same_idempotency_key(session: Session) -> None:
    original = enqueue_script_job(session)

    with pytest.raises(IdempotencyConflictError):
        JobRepository(session).enqueue(
            owner_id="creator-a",
            project_id=original.project_id,
            job_type=JobType.SCRIPT_GENERATION,
            idempotency_key="request-1",
            input_snapshot={"brief": "A different product"},
            routing_snapshot={"default_model": "free/model"},
        )


def test_claim_recovery_and_retry_preserve_durable_job(session: Session) -> None:
    job = enqueue_script_job(session)
    repository = JobRepository(session)

    claimed = repository.claim_next(lease_seconds=30)

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.attempt == 1

    claimed.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert repository.recover_expired_leases() == 1

    recovered = repository.get_owned("creator-a", job.id)
    assert recovered is not None
    assert recovered.status == JobStatus.QUEUED.value
    assert recovered.lease_expires_at is None

    recovered.status = JobStatus.FAILED.value
    recovered.error = "provider timeout"
    session.commit()

    retried = repository.requeue_failed("creator-a", job.id)
    assert retried is not None
    assert retried.status == JobStatus.QUEUED.value
    assert retried.error is None


def test_insight_jobs_are_claimed_before_older_media_work(session: Session) -> None:
    project = create_project(session)
    repository = JobRepository(session)
    media = repository.enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.ASSET_INGESTION,
        idempotency_key="older-media",
        input_snapshot={"asset_id": "asset-1"},
        routing_snapshot={},
    )
    insight = repository.enqueue(
        owner_id="creator-a",
        project_id=None,
        job_type=JobType.INSIGHT_SUMMARY,
        idempotency_key="newer-insight",
        input_snapshot={"facts": {"performance": []}},
        routing_snapshot={"default_model": "free/model"},
    )

    claimed = repository.claim_next(lease_seconds=30)

    assert claimed is not None and claimed.id == insight.id
    assert repository.get_owned("creator-a", media.id).status == JobStatus.QUEUED.value


def test_jobs_remain_owner_scoped(session: Session) -> None:
    job = enqueue_script_job(session)

    assert JobRepository(session).get_owned("creator-b", job.id) is None
