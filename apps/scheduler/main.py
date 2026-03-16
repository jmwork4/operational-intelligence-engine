"""Scheduler entry point.

Configures APScheduler with a PostgreSQL job store and registers
scheduled jobs that enqueue work to ARQ.  The scheduler itself
never executes business logic.
"""

import asyncio
import logging
import signal

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apps.scheduler.config import settings
from apps.scheduler.jobs import (
    archive_old_events_job,
    cleanup_expired_locks_job,
    evaluate_composite_rules_job,
    evaluate_threshold_rules_job,
)

logger = logging.getLogger(__name__)


def _sync_database_url(url: str) -> str:
    """Convert an async DATABASE_URL to a sync one for SQLAlchemy job store.

    Replaces ``postgresql+asyncpg://`` or ``asyncpg://`` with
    ``postgresql://`` so the synchronous SQLAlchemy driver can connect.
    """
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("asyncpg://", "postgresql://")
    return url


def create_scheduler() -> AsyncIOScheduler:
    """Build and configure the APScheduler instance."""
    job_store_url = _sync_database_url(settings.DATABASE_URL)

    jobstores = {
        "default": SQLAlchemyJobStore(url=job_store_url),
    }

    scheduler = AsyncIOScheduler(jobstores=jobstores)

    # -- Interval jobs -------------------------------------------------------
    scheduler.add_job(
        evaluate_threshold_rules_job,
        "interval",
        seconds=settings.THRESHOLD_EVAL_INTERVAL_SECONDS,
        id="evaluate_threshold_rules",
        replace_existing=True,
    )

    scheduler.add_job(
        evaluate_composite_rules_job,
        "interval",
        seconds=settings.COMPOSITE_EVAL_INTERVAL_SECONDS,
        id="evaluate_composite_rules",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_expired_locks_job,
        "interval",
        seconds=settings.LOCK_CLEANUP_INTERVAL_SECONDS,
        id="cleanup_expired_locks",
        replace_existing=True,
    )

    # -- Cron job ------------------------------------------------------------
    scheduler.add_job(
        archive_old_events_job,
        "cron",
        hour=settings.EVENT_ARCHIVE_HOUR,
        id="archive_old_events",
        replace_existing=True,
    )

    return scheduler


def main() -> None:
    """Start the scheduler and block until terminated."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting OIE Scheduler")
    scheduler = create_scheduler()
    scheduler.start()

    loop = asyncio.get_event_loop()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("Received %s, shutting down scheduler", sig.name)
        scheduler.shutdown(wait=False)
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown, sig)

    logger.info("Scheduler running — press Ctrl+C to stop")

    try:
        loop.run_forever()
    finally:
        loop.close()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
