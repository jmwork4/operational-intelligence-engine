"""Event processor — orchestrates event ingestion, streaming, and rule evaluation."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.types import RuleType
from packages.db.models.event import Event
from packages.db.models.rule import Rule
from packages.events.stream import EventStream
from packages.rules.evaluator import RuleEvaluator
from packages.rules.expression_parser import ExpressionParser, ExpressionValidationError

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes ingested events: streams to Redis, evaluates rules, enqueues alerts.

    Args:
        session: An async SQLAlchemy session.
        redis_url: Redis connection URL.
    """

    def __init__(self, session: AsyncSession, redis_url: str) -> None:
        self._session = session
        self._redis_url = redis_url
        self._stream = EventStream(redis_url)
        self._rule_evaluator = RuleEvaluator(session, redis_url)

    async def process_event(
        self, event_id: UUID, tenant_id: UUID
    ) -> dict:
        """Process a single event end-to-end.

        1. Load the event from the database.
        2. Append it to the tenant's Redis stream.
        3. Find matching event-triggered rules.
        4. Evaluate each rule's condition expression against the event payload.
        5. For matched rules, enqueue ``create_alert`` via ARQ.

        Args:
            event_id: Primary key of the event in the database.
            tenant_id: Tenant that owns the event.

        Returns:
            A dict summarising the processing result, including the number
            of rules matched and any alert jobs enqueued.
        """
        # 1. Load event from DB
        stmt = sa.select(Event).where(
            Event.id == event_id, Event.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        event = result.scalar_one_or_none()

        if event is None:
            logger.warning(
                "event_not_found",
                event_id=str(event_id),
                tenant_id=str(tenant_id),
            )
            return {
                "status": "error",
                "event_id": str(event_id),
                "error": "Event not found",
            }

        # Build event data dict
        event_data = {
            "id": str(event.id),
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "source_system": event.source_system,
            "payload": event.payload or {},
            "metadata": event.metadata_ or {},
            "occurred_at": str(event.occurred_at),
        }

        # 2. Append to Redis stream
        try:
            stream_id = await self._stream.append(tenant_id, event_data)
        except Exception:
            logger.warning(
                "event_stream_append_failed",
                event_id=str(event_id),
            )
            stream_id = None

        # 3 & 4. Evaluate event-triggered rules
        triggered_rules = await self._rule_evaluator.evaluate_event_rules(
            event_data, tenant_id
        )

        # 5. Enqueue alert creation for triggered rules
        alerts_enqueued = 0
        for rule_result in triggered_rules:
            try:
                from arq import create_pool
                from arq.connections import RedisSettings

                pool = await create_pool(RedisSettings.from_dsn(self._redis_url))
                await pool.enqueue_job(
                    "create_alert",
                    {
                        "rule_id": rule_result["rule_id"],
                        "rule_name": rule_result["rule_name"],
                        "severity": rule_result["severity"],
                        "action_type": rule_result["action_type"],
                        "tenant_id": str(tenant_id),
                        "event_id": str(event_id),
                        "event_type": event.event_type,
                        "entity_type": event.entity_type,
                        "entity_id": event.entity_id,
                    },
                )
                await pool.close()
                alerts_enqueued += 1
            except Exception:
                logger.exception(
                    "alert_enqueue_failed",
                    rule_id=rule_result["rule_id"],
                    event_id=str(event_id),
                )

        logger.info(
            "event_processed",
            event_id=str(event_id),
            stream_id=stream_id,
            rules_matched=len(triggered_rules),
            alerts_enqueued=alerts_enqueued,
        )

        return {
            "status": "processed",
            "event_id": str(event_id),
            "stream_id": stream_id,
            "rules_matched": len(triggered_rules),
            "alerts_enqueued": alerts_enqueued,
            "triggered_rules": triggered_rules,
        }
