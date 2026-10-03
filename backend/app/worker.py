import asyncio
import logging
from contextlib import nullcontext

from langgraph.checkpoint.postgres import PostgresSaver

from app.config import get_settings
from app.database import get_session_factory
from app.features.assets.router import get_storage
from app.features.media_workflow.service import MediaWorkflowService
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import OpenRouterProvider
from app.features.script_creation.service import ScriptCreationService
from app.schemas import JobType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Single-concurrency worker entrypoint.

    Claims a single durable job at a time and lets the workflow persist its terminal state.
    """

    settings = get_settings()
    logger.info("CreatorAI worker started in %s", settings.environment)
    while True:
        if settings.database_url:
            with get_session_factory(settings)() as session:
                recovered = JobRepository(session).recover_expired_leases()
                if recovered:
                    logger.warning("Recovered %s expired job lease(s)", recovered)
                job = JobRepository(session).claim_next(max(settings.worker_lease_seconds, 900))
                if job is not None:
                    try:
                        if job.type in {
                            JobType.ASSET_INGESTION,
                            JobType.CLIP_GENERATION,
                            JobType.MEDIA_EXPORT,
                        }:
                            connection_url = settings.database_url.replace(
                                "postgresql+psycopg://", "postgresql://", 1
                            )
                            checkpoint_context = (
                                PostgresSaver.from_conn_string(connection_url)
                                if job.type == JobType.CLIP_GENERATION
                                else nullcontext(None)
                            )
                            with checkpoint_context as saver:
                                if saver is not None:
                                    saver.setup()
                                MediaWorkflowService(
                                    session, settings, get_storage(settings), saver
                                ).execute(job)
                        else:
                            ScriptCreationService(
                                session, OpenRouterProvider(settings)
                            ).execute_claimed_job(job)
                    except Exception as error:
                        session.rollback()
                        job.status, job.stage, job.error = "failed", "failed", str(error)[:1000]
                        job.lease_expires_at = None
                        session.commit()
                        logger.exception("Job %s failed", job.id)
        await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("CreatorAI worker stopped")
