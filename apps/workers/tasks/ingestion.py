"""Ingestion worker tasks for processing incoming events."""

from __future__ import annotations

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def process_event(ctx: dict, event_data: dict) -> dict:
    """Process a single ingested event.

    Validates, normalises, and persists an incoming event, then triggers
    downstream rule evaluation.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        event_data: Raw event payload to process.

    Returns:
        dict with processing result and the assigned event ID.
    """
    logger.info("process_event_start", event_type=event_data.get("type"))

    try:
        # TODO: Validate event schema
        # TODO: Normalise event fields (timestamps, identifiers, etc.)
        # TODO: Persist event to database
        # TODO: Enqueue rule evaluation for the new event

        event_id = event_data.get("id", "unknown")
        logger.info("process_event_complete", event_id=event_id)

        return {"status": "processed", "event_id": event_id}

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

    for event_data in events:
        try:
            await process_event(ctx, event_data)
            processed += 1
        except Exception:
            logger.exception(
                "batch_event_failed",
                event_id=event_data.get("id", "unknown"),
            )
            failed += 1

    logger.info(
        "batch_process_events_complete",
        processed=processed,
        failed=failed,
    )

    return {"status": "completed", "processed": processed, "failed": failed}
