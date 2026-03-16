"""Job definitions that enqueue tasks to ARQ.

Each job connects to Redis and enqueues an ARQ task.
The scheduler NEVER executes business logic directly.
"""

import logging

from arq import create_pool
from arq.connections import RedisSettings

from apps.scheduler.config import settings

logger = logging.getLogger(__name__)


def _redis_settings() -> RedisSettings:
    """Build ARQ RedisSettings from the configured REDIS_URL."""
    url = settings.REDIS_URL
    # Parse redis://host:port/db
    stripped = url.replace("redis://", "")
    host_port, _, db = stripped.partition("/")
    host, _, port = host_port.partition(":")
    return RedisSettings(
        host=host or "localhost",
        port=int(port) if port else 6379,
        database=int(db) if db else 0,
    )


async def evaluate_threshold_rules_job() -> None:
    """Enqueue threshold rule evaluation to ARQ."""
    try:
        pool = await create_pool(_redis_settings())
        await pool.enqueue_job("evaluate_threshold_rules")
        logger.info("Enqueued task: evaluate_threshold_rules")
    except Exception:
        logger.exception("Failed to enqueue evaluate_threshold_rules")


async def evaluate_composite_rules_job() -> None:
    """Enqueue composite rule evaluation to ARQ."""
    try:
        pool = await create_pool(_redis_settings())
        await pool.enqueue_job("evaluate_composite_rules")
        logger.info("Enqueued task: evaluate_composite_rules")
    except Exception:
        logger.exception("Failed to enqueue evaluate_composite_rules")


async def cleanup_expired_locks_job() -> None:
    """Enqueue lock cleanup to ARQ."""
    try:
        pool = await create_pool(_redis_settings())
        await pool.enqueue_job("cleanup_expired_locks")
        logger.info("Enqueued task: cleanup_expired_locks")
    except Exception:
        logger.exception("Failed to enqueue cleanup_expired_locks")


async def archive_old_events_job() -> None:
    """Enqueue event archival to ARQ."""
    try:
        pool = await create_pool(_redis_settings())
        await pool.enqueue_job("archive_old_events")
        logger.info("Enqueued task: archive_old_events")
    except Exception:
        logger.exception("Failed to enqueue archive_old_events")
