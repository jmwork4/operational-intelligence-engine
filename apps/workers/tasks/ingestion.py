"""Ingestion worker tasks for processing incoming events."""

from __future__ import annotations

import os

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def process_event(ctx: dict, event_data: dict) -> dict:
    """Process a single ingested event.

    Creates an EventProcessor and delegates to it. The processor handles
    loading the event from the database, appending to the Redis stream,
    evaluating matching rules, and enqueueing alert creation.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        event_data: Raw event payload containing at minimum ``event_id``
            and ``tenant_id``.

    Returns:
        dict with processing result and the assigned event ID.
    """
    event_id = event_data.get("event_id") or event_data.get("id", "unknown")
    tenant_id = event_data.get("tenant_id", "unknown")
    logger.info("process_event_start", event_id=event_id, tenant_id=tenant_id)

    try:
        from uuid import UUID
        from packages.common import get_settings
        from packages.db.session import get_async_session
        from packages.events.processor import EventProcessor

        settings = get_settings()

        async for session in get_async_session():
            processor = EventProcessor(
                session=session,
                redis_url=settings.REDIS_URL,
            )
            result = await processor.process_event(
                event_id=UUID(str(event_id)),
                tenant_id=UUID(str(tenant_id)),
            )
            logger.info("process_event_complete", event_id=event_id, result=result)
            return result

        return {"status": "error", "event_id": event_id, "error": "No session available"}

    except Exception:
        logger.exception("process_event_failed", event_data=event_data)
        raise


async def batch_process_events(ctx: dict, events: list[dict]) -> dict:
    """Process a batch of ingested events.

    Iterates over a list of raw events, processing each one individually.
    Failures on individual events are captured without aborting the batch.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        events: List of raw event payloads to process.

    Returns:
        dict with counts of processed and failed events.
    """
    logger.info("batch_process_events_start", batch_size=len(events))

    processed = 0
    failed = 0
    results: list[dict] = []

    for event_data in events:
        try:
            result = await process_event(ctx, event_data)
            results.append(result)
            processed += 1
        except Exception:
            logger.exception(
                "batch_event_failed",
                event_id=event_data.get("event_id", event_data.get("id", "unknown")),
            )
            failed += 1

    logger.info(
        "batch_process_events_complete",
        processed=processed,
        failed=failed,
    )

    return {
        "status": "completed",
        "processed": processed,
        "failed": failed,
        "results": results,
    }
