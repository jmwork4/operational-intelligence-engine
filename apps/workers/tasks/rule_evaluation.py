"""Rule evaluation tasks for processing event-triggered, threshold, and composite rules."""

from __future__ import annotations

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def evaluate_event_rules(ctx: dict, event_data: dict) -> dict:
    """Evaluate event-triggered rules for an event.

    Loads active event-triggered rules from the database, matches them against
    the incoming event, and creates alerts for any rules that fire.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        event_data: The event payload to evaluate against rules.

    Returns:
        dict with evaluation results including matched rule count.
    """
    event_id = event_data.get("event_id") or event_data.get("id", "unknown")
    tenant_id = event_data.get("tenant_id", "unknown")
    logger.info("evaluate_event_rules_start", event_id=event_id)

    try:
        from uuid import UUID
        from packages.common import get_settings
        from packages.db.session import get_async_session
        from packages.rules.evaluator import RuleEvaluator

        settings = get_settings()

        async for session in get_async_session():
            evaluator = RuleEvaluator(
                session=session,
                redis_url=settings.REDIS_URL,
            )
            triggered = await evaluator.evaluate_event_rules(
                event_data=event_data,
                tenant_id=UUID(str(tenant_id)),
            )

            matched_rules = len(triggered)
            logger.info(
                "evaluate_event_rules_complete",
                event_id=event_id,
                matched_rules=matched_rules,
            )

            # Enqueue alert creation for each triggered rule
            for rule_result in triggered:
                try:
                    from arq import create_pool
                    from arq.connections import RedisSettings

                    pool = await create_pool(
                        RedisSettings.from_dsn(settings.REDIS_URL)
                    )
                    await pool.enqueue_job(
                        "create_alert",
                        {
                            "rule_id": rule_result["rule_id"],
                            "rule_name": rule_result["rule_name"],
                            "severity": rule_result["severity"],
                            "action_type": rule_result["action_type"],
                            "tenant_id": str(tenant_id),
                            "event_id": str(event_id),
                            "event_type": event_data.get("event_type"),
                            "entity_type": event_data.get("entity_type"),
                            "entity_id": event_data.get("entity_id"),
                        },
                    )
                    await pool.close()
                except Exception:
                    logger.exception(
                        "alert_enqueue_failed",
                        rule_id=rule_result["rule_id"],
                    )

            return {
                "status": "evaluated",
                "event_id": event_id,
                "matched_rules": matched_rules,
                "triggered": triggered,
            }

        return {
            "status": "error",
            "event_id": event_id,
            "matched_rules": 0,
            "error": "No session available",
        }

    except Exception:
        logger.exception("evaluate_event_rules_failed", event_id=event_id)
        raise


async def evaluate_threshold_rules(
    ctx: dict, rule_ids: list[str] | None = None
) -> dict:
    """Evaluate threshold-based rules.

    Queries aggregated metrics and compares them against configured thresholds.
    If no rule_ids are provided, evaluates all active threshold rules.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        rule_ids: Optional list of specific rule IDs to evaluate. When None,
            all active threshold rules are evaluated.

    Returns:
        dict with evaluation results including the number of rules evaluated
        and how many triggered alerts.
    """
    logger.info("evaluate_threshold_rules_start", rule_ids=rule_ids)

    try:
        from uuid import UUID
        from packages.common import get_settings
        from packages.db.session import get_async_session
        from packages.rules.evaluator import RuleEvaluator

        settings = get_settings()

        async for session in get_async_session():
            evaluator = RuleEvaluator(
                session=session,
                redis_url=settings.REDIS_URL,
            )

            uuid_rule_ids = (
                [UUID(rid) for rid in rule_ids] if rule_ids else None
            )

            triggered = await evaluator.evaluate_threshold_rules(
                rule_ids=uuid_rule_ids,
            )

            evaluated = len(uuid_rule_ids) if uuid_rule_ids else 0
            triggered_count = len(triggered)

            # Enqueue alerts for triggered threshold rules
            for rule_result in triggered:
                try:
                    from arq import create_pool
                    from arq.connections import RedisSettings

                    pool = await create_pool(
                        RedisSettings.from_dsn(settings.REDIS_URL)
                    )
                    await pool.enqueue_job("create_alert", rule_result)
                    await pool.close()
                except Exception:
                    logger.exception(
                        "threshold_alert_enqueue_failed",
                        rule_id=rule_result.get("rule_id"),
                    )

            logger.info(
                "evaluate_threshold_rules_complete",
                evaluated=evaluated,
                triggered=triggered_count,
            )

            return {
                "status": "evaluated",
                "rules_evaluated": evaluated,
                "rules_triggered": triggered_count,
                "triggered": triggered,
            }

        return {
            "status": "error",
            "rules_evaluated": 0,
            "rules_triggered": 0,
            "error": "No session available",
        }

    except Exception:
        logger.exception("evaluate_threshold_rules_failed", rule_ids=rule_ids)
        raise


async def evaluate_composite_rules(
    ctx: dict, rule_ids: list[str] | None = None
) -> dict:
    """Evaluate composite rules built from multiple sub-conditions.

    Composite rules combine multiple conditions (event patterns, thresholds,
    time-based correlations) using boolean logic. If no rule_ids are provided,
    evaluates all active composite rules.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        rule_ids: Optional list of specific rule IDs to evaluate. When None,
            all active composite rules are evaluated.

    Returns:
        dict with evaluation results including the number of rules evaluated
        and how many triggered alerts.
    """
    logger.info("evaluate_composite_rules_start", rule_ids=rule_ids)

    try:
        from uuid import UUID
        from packages.common import get_settings
        from packages.db.session import get_async_session
        from packages.rules.evaluator import RuleEvaluator

        settings = get_settings()

        async for session in get_async_session():
            evaluator = RuleEvaluator(
                session=session,
                redis_url=settings.REDIS_URL,
            )

            uuid_rule_ids = (
                [UUID(rid) for rid in rule_ids] if rule_ids else None
            )

            triggered = await evaluator.evaluate_composite_rules(
                rule_ids=uuid_rule_ids,
            )

            evaluated = len(uuid_rule_ids) if uuid_rule_ids else 0
            triggered_count = len(triggered)

            # Enqueue alerts for triggered composite rules
            for rule_result in triggered:
                try:
                    from arq import create_pool
                    from arq.connections import RedisSettings

                    pool = await create_pool(
                        RedisSettings.from_dsn(settings.REDIS_URL)
                    )
                    await pool.enqueue_job("create_alert", rule_result)
                    await pool.close()
                except Exception:
                    logger.exception(
                        "composite_alert_enqueue_failed",
                        rule_id=rule_result.get("rule_id"),
                    )

            logger.info(
                "evaluate_composite_rules_complete",
                evaluated=evaluated,
                triggered=triggered_count,
            )

            return {
                "status": "evaluated",
                "rules_evaluated": evaluated,
                "rules_triggered": triggered_count,
                "triggered": triggered,
            }

        return {
            "status": "error",
            "rules_evaluated": 0,
            "rules_triggered": 0,
            "error": "No session available",
        }

    except Exception:
        logger.exception("evaluate_composite_rules_failed", rule_ids=rule_ids)
        raise
