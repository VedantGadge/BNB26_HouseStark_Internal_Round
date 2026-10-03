"""Durable queue access for AI script-creation operations."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Job
from app.schemas import JobResponse, JobStatus, JobType


class IdempotencyConflictError(Exception):
    """An idempotency key was reused with different immutable input."""


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        owner_id: str,
        project_id: uuid.UUID | None,
        job_type: JobType,
        idempotency_key: str,
        input_snapshot: dict,
        routing_snapshot: dict,
        idempotency_payload: dict | None = None,
    ) -> Job:
        payload_hash = self._payload_hash(idempotency_payload or input_snapshot, routing_snapshot)
        existing = self.find_by_idempotency(owner_id, job_type, idempotency_key)
        if existing is not None:
            if existing.payload_hash != payload_hash:
                raise IdempotencyConflictError
            return existing

        job = Job(
            owner_id=owner_id,
            project_id=project_id,
            type=job_type.value,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            input_snapshot=input_snapshot,
            routing_snapshot=routing_snapshot,
        )
        self.session.add(job)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.find_by_idempotency(owner_id, job_type, idempotency_key)
            if existing is not None and existing.payload_hash == payload_hash:
                return existing
            raise IdempotencyConflictError from None
        self.session.refresh(job)
        return job

    def get_owned(self, owner_id: str, job_id: uuid.UUID) -> Job | None:
        return self.session.scalar(select(Job).where(Job.id == job_id, Job.owner_id == owner_id))

    def requeue_failed(self, owner_id: str, job_id: uuid.UUID) -> Job | None:
        job = self.get_owned(owner_id, job_id)
        if job is None:
            return None
        if job.type not in {job_type.value for job_type in JobType}:
            raise ValueError("This job type cannot be retried by the script worker")
        if job.status != JobStatus.FAILED.value:
            raise ValueError("Only failed jobs can be retried")
        job.status = JobStatus.QUEUED.value
        job.stage = "awaiting_worker"
        job.error = None
        job.claimed_at = None
        job.lease_expires_at = None
        self.session.commit()
        self.session.refresh(job)
        return job

    def claim_next(self, lease_seconds: int) -> Job | None:
        statement = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED.value)
            .order_by(Job.created_at.asc(), Job.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = self.session.scalar(statement)
        if job is None:
            return None

        now = datetime.now(UTC)
        job.status = JobStatus.RUNNING.value
        job.stage = "claimed"
        job.attempt += 1
        job.claimed_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.commit()
        self.session.refresh(job)
        return job

    def recover_expired_leases(self) -> int:
        now = datetime.now(UTC)
        expired_jobs = list(
            self.session.scalars(
                select(Job).where(
                    Job.status == JobStatus.RUNNING.value,
                    Job.lease_expires_at.is_not(None),
                    Job.lease_expires_at < now,
                )
            )
        )
        for job in expired_jobs:
            job.status = JobStatus.QUEUED.value
            job.stage = "awaiting_worker"
            job.claimed_at = None
            job.lease_expires_at = None
        if expired_jobs:
            self.session.commit()
        return len(expired_jobs)

    def find_by_idempotency(
        self,
        owner_id: str,
        job_type: JobType,
        idempotency_key: str,
    ) -> Job | None:
        return self.session.scalar(
            select(Job).where(
                Job.owner_id == owner_id,
                Job.type == job_type.value,
                Job.idempotency_key == idempotency_key,
            )
        )

    @staticmethod
    def _payload_hash(input_snapshot: dict, routing_snapshot: dict) -> str:
        payload = {"input": input_snapshot, "routing": routing_snapshot}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def job_response(job: Job) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        status=JobStatus(job.status),
        stage=job.stage,
        error=job.error,
        conversation_id=job.input_snapshot.get("conversation_id"),
    )
