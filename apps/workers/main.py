"""ARQ worker entry point for the Operational Intelligence Engine."""

import os
import asyncio

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

from arq import create_pool
from arq.connections import RedisSettings

from apps.workers.tasks import (
    process_event,
    batch_process_events,
    generate_embeddings,
    reindex_document,
    evaluate_event_rules,
    evaluate_threshold_rules,
    evaluate_composite_rules,
    create_alert,
    send_notification,
    cleanup_expired_locks,
    archive_old_events,
)


def get_redis_settings() -> RedisSettings:
    """Build RedisSettings from the REDIS_URL environment variable."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return RedisSettings.from_dsn(redis_url)


async def startup(ctx: dict) -> None:
    """Worker startup hook: initialize DB connections, logging, and shared resources."""
    logger.info("worker_startup", msg="Initializing worker resources")

    # TODO: Initialize database connection pool
    # e.g. ctx["db"] = await create_db_pool(os.environ["DATABASE_URL"])

    # TODO: Initialize any shared HTTP clients
    # e.g. ctx["http"] = aiohttp.ClientSession()

    logger.info("worker_startup_complete", msg="Worker resources initialized")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook: tear down DB connections and release resources."""
    logger.info("worker_shutdown", msg="Releasing worker resources")

    # TODO: Close database connection pool
    # e.g. await ctx["db"].close()

    # TODO: Close shared HTTP clients
    # e.g. await ctx["http"].close()

    logger.info("worker_shutdown_complete", msg="Worker resources released")


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = get_redis_settings()

    functions = [
        process_event,
        batch_process_events,
        generate_embeddings,
        reindex_document,
        evaluate_event_rules,
        evaluate_threshold_rules,
        evaluate_composite_rules,
        create_alert,
        send_notification,
        cleanup_expired_locks,
        archive_old_events,
    ]

    on_startup = startup
    on_shutdown = shutdown

    # Allow up to 5 concurrent jobs per worker process
    max_jobs = 5

    # Poll interval in seconds
    poll_delay = 0.5

    # Default job timeout (10 minutes)
    job_timeout = 600


if __name__ == "__main__":
    from arq.cli import cli

    cli()
