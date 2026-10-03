import asyncio
import logging

from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Single-concurrency worker entrypoint.

    Phase 1 wires this loop to the Neon jobs table and atomically claims one job at a
    time. It intentionally does no media work until persistence and provider services
    are configured.
    """

    settings = get_settings()
    logger.info("CreatorAI worker started in %s", settings.environment)
    while True:
        await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("CreatorAI worker stopped")
