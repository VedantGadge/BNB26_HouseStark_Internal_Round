import asyncio
import logging

from app.config import get_settings
from app.database import get_session_factory
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import OpenRouterProvider
from app.features.script_creation.service import ScriptCreationService

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
                job = JobRepository(session).claim_next(settings.worker_lease_seconds)
                if job is not None:
                    service = ScriptCreationService(session, OpenRouterProvider(settings))
                    service.execute_claimed_job(job)
        await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("CreatorAI worker stopped")
