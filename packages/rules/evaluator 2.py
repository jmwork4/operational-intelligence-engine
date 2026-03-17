"""Rule evaluator — loads rules from the database and evaluates them."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import redis.asyncio as aioredis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.types import RuleType
from packages.db.models.event import Event
from packages.db.models.rule import Rule
from packages.rules.expression_parser import ExpressionParser, ExpressionValidationError
from packages.rules.state import RuleStateManager

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _build_event_context(event_data: dict) -> dict[str, object]:
    """Flatten an event payload dict into dot-notation keys.

    For example::

        {"delay_minutes": 45, "vendor_priority": "high"}

    becomes::

        {"event.delay_minutes": 45, "event.vendor_priority": "high"}

    Top-level event fields (event_type, entity_type, etc.) are also included.
    """
    context: dict[str, object] = {}

    # Top-level event fields
    for key in ("event_type", "entity_type", "entity_id", "source_system"):
        if key in event_data:
            context[f"event.{key}"] = event_data[key]

    # Flatten payload
    payload = event_data.get("payload") or {}
    for key, value in payload.items():
        context[f"event.{key}"] = value

    # Flatten metadata
    metadata = event_data.get("metadata") or event_data.get("metadata_") or {}
    for key, value in metadata.items():
        context[f"meta.{key}"] = value

    return context


class RuleEvaluator:
    """Evaluates rules against events and aggregated metrics.

    Args:
        session: An async SQLAlchemy session.
        redis_url: Redis connection URL (e.g. ``redis://localhost:6379/0``).
    """

    def __init__(self, session: AsyncSession, redis_url: str) -> None:
        self._session = session
        self._redis_url = redis_url
        self._parser = ExpressionParser()

    # -----------------------------------------------------------------
    # Event-triggered rules
    # -----------------------------------------------------------------

    async def evaluate_event_rules(
        self, event_data: dict, tenant_id: UUID
    ) -> list[dict]:
        """Evaluate all active event-triggered rules for a given event.

        Args:
            event_data: Dict representation of the event (must include
                ``event_type`` and ``payload``).
            tenant_id: Tenant that owns the event.

        Returns:
            A list of dicts, one per triggered rule, containing
            ``rule_id``, ``rule_name``, ``severity``, and ``action_type``.
        """
        event_type = event_data.get("event_type", "")

        # Load matching rules
        stmt = (
            sa.select(Rule)
            .where(
                Rule.tenant_id == tenant_id,
                Rule.rule_type == RuleType.EVENT_TRIGGERED,
                Rule.enabled.is_(True),
                Rule.trigger_event == event_type,
            )
        )
        result = await self._session.execute(stmt)
        rules = result.scalars().all()

        if not rules:
            logger.debug(
                "no_matching_event_rules",
                event_type=event_type,
                tenant_id=str(tenant_id),
            )
            return []

        # Build context from event payload
        context = _build_event_context(event_data)

        triggered: list[dict] = []

        for rule in rules:
            try:
                matched = self._parser.evaluate(rule.condition_expression, context)
            except ExpressionValidationError as exc:
                logger.warning(
                    "rule_expression_error",
                    rule_id=str(rule.id),
                    rule_name=rule.rule_name,
                    error=str(exc),
                )
                continue

            if matched:
                logger.info(
                    "rule_triggered",
                    rule_id=str(rule.id),
                    rule_name=rule.rule_name,
                    severity=rule.severity,
                )
                triggered.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.rule_name,
                    "severity": rule.severity,
                    "action_type": rule.action_type,
                    "tenant_id": str(tenant_id),
                    "event_type": event_type,
                })

        return triggered

    # -----------------------------------------------------------------
    # Threshold rules
    # -----------------------------------------------------------------

    async def evaluate_threshold_rules(
        self,
        tenant_id: UUID | None = None,
        rule_ids: list[UUID] | None = None,
    ) -> list[dict]:
        """Evaluate threshold-based rules.

        Loads active threshold rules, queries events within each rule's
        evaluation window, and checks whether the count or aggregated
        value breaches the threshold defined in the condition expression.

        Args:
            tenant_id: Optionally restrict to a single tenant.
            rule_ids: Optionally restrict to specific rule IDs.

        Returns:
            A list of dicts for each breached threshold.
        """
        stmt = sa.select(Rule).where(
            Rule.rule_type == RuleType.THRESHOLD,
            Rule.enabled.is_(True),
        )
        if tenant_id is not None:
            stmt = stmt.where(Rule.tenant_id == tenant_id)
        if rule_ids:
            stmt = stmt.where(Rule.id.in_(rule_ids))

        result = await self._session.execute(stmt)
        rules = result.scalars().all()

        triggered: list[dict] = []

        for rule in rules:
            window_seconds = rule.evaluation_window or 3600
            window_start = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

            # Query events within the evaluation window
            event_stmt = (
                sa.select(sa.func.count())
                .select_from(Event)
                .where(
                    Event.tenant_id == rule.tenant_id,
                    Event.occurred_at >= window_start,
                )
            )
            if rule.trigger_event:
                event_stmt = event_stmt.where(Event.event_type == rule.trigger_event)

            count_result = await self._session.execute(event_stmt)
            event_count = count_result.scalar_one()

            # Build a context with the aggregate values
            context: dict[str, object] = {
                "event.count": event_count,
                "threshold.count": event_count,
                "threshold.window_seconds": window_seconds,
            }

            try:
                breached = self._parser.evaluate(rule.condition_expression, context)
            except ExpressionValidationError as exc:
                logger.warning(
                    "threshold_rule_expression_error",
                    rule_id=str(rule.id),
                    error=str(exc),
                )
                continue

            if breached:
                logger.info(
                    "threshold_breached",
                    rule_id=str(rule.id),
                    rule_name=rule.rule_name,
                    event_count=event_count,
                    window_seconds=window_seconds,
                )
                triggered.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.rule_name,
                    "severity": rule.severity,
                    "action_type": rule.action_type,
                    "tenant_id": str(rule.tenant_id),
                    "event_count": event_count,
                    "window_seconds": window_seconds,
                })

        return triggered

    # -----------------------------------------------------------------
    # Composite rules
    # -----------------------------------------------------------------

    async def evaluate_composite_rules(
        self,
        tenant_id: UUID | None = None,
        rule_ids: list[UUID] | None = None,
    ) -> list[dict]:
        """Evaluate composite rules that correlate multiple conditions.

        For each composite rule, loads state from Redis (for windows < 1 hr)
        or PostgreSQL (for longer windows), checks whether all correlated
        conditions are met within the window, and returns triggered results.

        Args:
            tenant_id: Optionally restrict to a single tenant.
            rule_ids: Optionally restrict to specific rule IDs.

        Returns:
            A list of dicts for each triggered composite rule.
        """
        stmt = sa.select(Rule).where(
            Rule.rule_type == RuleType.COMPOSITE,
            Rule.enabled.is_(True),
        )
        if tenant_id is not None:
            stmt = stmt.where(Rule.tenant_id == tenant_id)
        if rule_ids:
            stmt = stmt.where(Rule.id.in_(rule_ids))

        result = await self._session.execute(stmt)
        rules = result.scalars().all()

        state_mgr = RuleStateManager(
            session=self._session, redis_url=self._redis_url
        )

        triggered: list[dict] = []

        for rule in rules:
            window_seconds = rule.evaluation_window or 3600
            rule_tenant_id = rule.tenant_id

            # Load current composite state
            state = await state_mgr.get_state(rule.id, rule_tenant_id)

            # The condition_expression for composite rules encodes
            # sub-condition references. Build context from state.
            context: dict[str, object] = {}
            conditions_met = state.get("conditions_met", {})
            for cond_key, cond_val in conditions_met.items():
                context[cond_key] = cond_val

            # Also include aggregate counts
            context["composite.conditions_total"] = state.get("conditions_total", 0)
            context["composite.conditions_met_count"] = sum(
                1 for v in conditions_met.values() if v
            )

            try:
                matched = self._parser.evaluate(rule.condition_expression, context)
            except ExpressionValidationError as exc:
                logger.warning(
                    "composite_rule_expression_error",
                    rule_id=str(rule.id),
                    error=str(exc),
                )
                continue

            if matched:
                logger.info(
                    "composite_rule_triggered",
                    rule_id=str(rule.id),
                    rule_name=rule.rule_name,
                )
                triggered.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.rule_name,
                    "severity": rule.severity,
                    "action_type": rule.action_type,
                    "tenant_id": str(rule_tenant_id),
                    "window_seconds": window_seconds,
                })

                # Clear state after firing
                await state_mgr.clear_state(rule.id, rule_tenant_id)

        return triggered
