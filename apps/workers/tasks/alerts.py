"""Alert worker tasks for creating alerts and sending notifications."""

from __future__ import annotations

from uuid import UUID

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def create_alert(ctx: dict, alert_data: dict) -> dict:
    """Create and deduplicate an alert.

    Checks for existing alerts that match deduplication criteria. If a
    duplicate is found the alert is suppressed. Otherwise, persists a new
    alert and enqueues a notification task.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        alert_data: Alert payload including tenant_id, rule_id, entity_type,
            entity_id, severity, message, context, evaluation_window.

    Returns:
        dict with the alert ID and whether it was newly created or deduplicated.
    """
    rule_id = alert_data.get("rule_id", "unknown")
    logger.info("create_alert_start", rule_id=rule_id)

    try:
        from packages.common.settings import get_settings
        from packages.db.session import init_db, create_async_session_factory, create_async_engine
        from packages.domain.alert_service import AlertService

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        session_factory = create_async_session_factory(engine)

        async with session_factory() as session:
            service = AlertService(session)
            alert = await service.create_alert(
                tenant_id=UUID(str(alert_data["tenant_id"])),
                rule_id=UUID(str(alert_data["rule_id"])),
                entity_type=alert_data["entity_type"],
                entity_id=alert_data["entity_id"],
                severity=alert_data["severity"],
                message=alert_data["message"],
                context=alert_data.get("context", {}),
                evaluation_window=alert_data.get("evaluation_window"),
            )

        await engine.dispose()

        if alert is not None:
            alert_id = str(alert.id)
            is_new = True

            # Enqueue notification delivery for new alerts
            redis = ctx.get("redis")
            if redis is not None:
                from arq import create_pool

                pool = ctx.get("pool") or await create_pool(ctx.get("redis_settings"))
                await pool.enqueue_job(
                    "send_notification",
                    alert_id,
                    ["email", "slack"],
                )
            else:
                logger.warning(
                    "notification_skipped",
                    alert_id=alert_id,
                    reason="no redis in context",
                )
        else:
            alert_id = "suppressed"
            is_new = False

        logger.info(
            "create_alert_complete",
            alert_id=alert_id,
            is_new=is_new,
        )

        return {
            "status": "created" if is_new else "deduplicated",
            "alert_id": alert_id,
            "is_new": is_new,
        }

    except Exception:
        logger.exception("create_alert_failed", rule_id=rule_id)
        raise


async def send_notification(ctx: dict, alert_id: str, channels: list[str]) -> dict:
    """Send alert notifications through the specified channels.

    Currently a placeholder that logs intended notifications. Will be
    replaced with real channel-specific transports (SMTP, Slack API,
    webhook, etc.) in a future iteration.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        alert_id: Unique identifier of the alert to notify about.
        channels: List of notification channel names (e.g. ["email", "slack"]).

    Returns:
        dict with per-channel delivery results.
    """
    logger.info("send_notification_start", alert_id=alert_id, channels=channels)

    results: dict[str, str] = {}

    for channel in channels:
        try:
            logger.info(
                "notification_dispatch",
                alert_id=alert_id,
                channel=channel,
                detail=f"Would send alert {alert_id} via {channel}",
            )
            results[channel] = "sent"
            logger.info(
                "notification_sent",
                alert_id=alert_id,
                channel=channel,
            )

        except Exception:
            logger.exception(
                "notification_failed",
                alert_id=alert_id,
                channel=channel,
            )
            results[channel] = "failed"

    logger.info("send_notification_complete", alert_id=alert_id, results=results)

    return {
        "status": "completed",
        "alert_id": alert_id,
        "results": results,
    }
