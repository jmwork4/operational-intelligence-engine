"""Root-cause analysis — event-chain correlation and causal reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

import numpy as np
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import utc_now
from packages.db.models.alert import Alert
from packages.db.models.event import Event
from packages.db.models.rule import Rule

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProbableCause:
    """A single candidate root cause for an alert."""

    event_id: UUID
    event_type: str
    description: str
    confidence: float  # 0.0 – 1.0
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class CorrelatedEvent:
    """An event correlated to a reference event."""

    event_id: UUID
    event_type: str
    entity_id: str
    correlation_score: float  # 0.0 – 1.0
    time_offset_minutes: float


@dataclass(frozen=True, slots=True)
class RootCauseReport:
    """Full root-cause analysis report for a single alert."""

    alert_id: UUID
    entity_id: str
    probable_causes: list[ProbableCause]
    event_timeline: list[dict]
    analysis_summary: str


# ------------------------------------------------------------------
# Analyzer
# ------------------------------------------------------------------


class RootCauseAnalyzer:
    """Traces alert triggers back through correlated events to find root causes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Primary analysis entry point
    # ------------------------------------------------------------------

    async def analyze(
        self,
        tenant_id: UUID,
        alert_id: UUID,
    ) -> RootCauseReport:
        """Produce a root-cause report for *alert_id*.

        Steps:
        1. Load the alert and its triggering rule.
        2. Fetch the entity's event history (last 48 h).
        3. Walk backward through correlated events.
        4. Identify the earliest anomalous event in the chain as the
           probable root cause.
        5. Score each candidate by correlation strength.
        """
        # 1. Load alert
        alert = await self._load_alert(tenant_id, alert_id)
        rule = await self._load_rule(alert.rule_id)

        logger.info(
            "root_cause_analysis_started",
            tenant_id=str(tenant_id),
            alert_id=str(alert_id),
            entity_id=alert.entity_id,
            rule_name=rule.rule_name if rule else "unknown",
        )

        # 2. Fetch event history for the entity
        since = utc_now() - timedelta(hours=48)

        event_stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.entity_id == alert.entity_id,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )
        event_result = await self._session.execute(event_stmt)
        entity_events = list(event_result.scalars().all())

        # Build the timeline
        event_timeline = _build_timeline(entity_events)

        # 3. Find correlated events (same entity + related entities)
        correlated = await self.find_correlated_events(
            tenant_id=tenant_id,
            entity_id=alert.entity_id,
            event_type=alert.entity_type,
            window_hours=48,
        )

        # 4. Identify probable causes
        probable_causes = _identify_probable_causes(
            entity_events, correlated, rule
        )

        # 5. Generate summary
        analysis_summary = _generate_summary(alert, rule, probable_causes, entity_events)

        report = RootCauseReport(
            alert_id=alert_id,
            entity_id=alert.entity_id,
            probable_causes=probable_causes,
            event_timeline=event_timeline,
            analysis_summary=analysis_summary,
        )

        logger.info(
            "root_cause_analysis_complete",
            tenant_id=str(tenant_id),
            alert_id=str(alert_id),
            probable_causes_count=len(probable_causes),
        )
        return report

    # ------------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------------

    async def find_correlated_events(
        self,
        tenant_id: UUID,
        entity_id: str,
        event_type: str,
        window_hours: int = 48,
    ) -> list[CorrelatedEvent]:
        """Find events correlated with *entity_id* within *window_hours*.

        Correlation is scored by:
        - Temporal proximity (closer events score higher).
        - Whether the event shares the same entity (direct) or is linked
          via ``payload.related_entity_id`` (indirect).
        """
        since = utc_now() - timedelta(hours=window_hours)
        now = utc_now()

        # Fetch all events for the same entity in the window
        same_entity_stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.entity_id == entity_id,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )
        same_result = await self._session.execute(same_entity_stmt)
        same_events = list(same_result.scalars().all())

        # Determine the reference time (latest event)
        reference_time = same_events[-1].occurred_at if same_events else now

        # Collect related entity IDs from payloads
        related_entity_ids: set[str] = set()
        for event in same_events:
            payload = event.payload or {}
            related = payload.get("related_entity_id")
            if related and isinstance(related, str):
                related_entity_ids.add(related)

        # Fetch events for related entities
        related_events: list[Event] = []
        if related_entity_ids:
            related_stmt = (
                sa.select(Event)
                .where(
                    Event.tenant_id == tenant_id,
                    Event.entity_id.in_(list(related_entity_ids)),
                    Event.occurred_at >= since,
                )
                .order_by(Event.occurred_at.asc())
            )
            related_result = await self._session.execute(related_stmt)
            related_events = list(related_result.scalars().all())

        # Score all events
        correlated: list[CorrelatedEvent] = []
        seen_ids: set[UUID] = set()

        all_candidate_events = same_events + related_events
        window_seconds = window_hours * 3600.0

        for event in all_candidate_events:
            if event.id in seen_ids:
                continue
            seen_ids.add(event.id)

            time_offset = (
                event.occurred_at - reference_time
            ).total_seconds() / 60.0

            # Temporal proximity score: exponential decay
            time_diff_seconds = abs(
                (event.occurred_at - reference_time).total_seconds()
            )
            temporal_score = float(
                np.exp(-time_diff_seconds / (window_seconds / 4))
            )

            # Entity proximity bonus
            entity_bonus = 0.3 if event.entity_id == entity_id else 0.1

            correlation_score = min(temporal_score + entity_bonus, 1.0)

            correlated.append(
                CorrelatedEvent(
                    event_id=event.id,
                    event_type=event.event_type,
                    entity_id=event.entity_id,
                    correlation_score=round(correlation_score, 3),
                    time_offset_minutes=round(time_offset, 2),
                )
            )

        correlated.sort(key=lambda c: c.correlation_score, reverse=True)

        logger.info(
            "correlated_events_found",
            tenant_id=str(tenant_id),
            entity_id=entity_id,
            correlated_count=len(correlated),
        )
        return correlated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_alert(self, tenant_id: UUID, alert_id: UUID) -> Alert:
        """Load an alert or raise."""
        from packages.common import ResourceNotFoundError

        stmt = sa.select(Alert).where(
            Alert.id == alert_id, Alert.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            raise ResourceNotFoundError("Alert", str(alert_id))
        return alert

    async def _load_rule(self, rule_id: UUID) -> Rule | None:
        """Load the rule that triggered the alert."""
        stmt = sa.select(Rule).where(Rule.id == rule_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _build_timeline(events: list[Event]) -> list[dict]:
    """Convert a list of events into a lightweight timeline."""
    return [
        {
            "event_id": str(event.id),
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "occurred_at": event.occurred_at.isoformat(),
            "payload_summary": _summarise_payload(event.payload),
        }
        for event in events
    ]


def _summarise_payload(payload: dict | None) -> dict:
    """Return a compact summary of a payload (top-level keys + types)."""
    if not payload:
        return {}
    summary: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, (int, float)):
            summary[key] = str(value)
        elif isinstance(value, str) and len(value) < 120:
            summary[key] = value
        else:
            summary[key] = type(value).__name__
    return summary


def _identify_probable_causes(
    entity_events: list[Event],
    correlated: list[CorrelatedEvent],
    rule: Rule | None,
) -> list[ProbableCause]:
    """Walk backward through events and find candidates for root cause.

    Heuristics:
    - Events with error-like types or anomaly indicators score higher.
    - Earlier events in the chain score higher (root cause is upstream).
    - Correlation score is factored in.
    """
    if not entity_events:
        return []

    # Build a correlation lookup
    corr_lookup: dict[UUID, float] = {
        c.event_id: c.correlation_score for c in correlated
    }

    candidates: list[ProbableCause] = []

    # Walk events in reverse chronological order
    for idx, event in enumerate(reversed(entity_events)):
        payload = event.payload or {}

        # Score by heuristic signals
        is_error = "error" in event.event_type.lower() or "fail" in event.event_type.lower()
        has_anomaly = payload.get("is_anomaly") is True or payload.get("anomaly_score", 0) > 0
        has_status_change = "status" in payload

        if not (is_error or has_anomaly or has_status_change):
            continue

        # Positional score: earlier in the chain -> higher base confidence
        position_score = min((idx + 1) / max(len(entity_events), 1) * 0.4, 0.4)

        # Correlation score contribution
        corr_score = corr_lookup.get(event.id, 0.2)

        # Signal bonus
        signal_bonus = 0.0
        if is_error:
            signal_bonus += 0.25
        if has_anomaly:
            signal_bonus += 0.2

        confidence = min(position_score + corr_score * 0.3 + signal_bonus, 1.0)

        # Build description
        description = _build_cause_description(event, rule)

        candidates.append(
            ProbableCause(
                event_id=event.id,
                event_type=event.event_type,
                description=description,
                confidence=round(confidence, 3),
                occurred_at=event.occurred_at,
            )
        )

    # Sort by confidence descending and return the top candidates
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:10]


def _build_cause_description(event: Event, rule: Rule | None) -> str:
    """Generate a human-readable description for a probable cause."""
    payload = event.payload or {}
    parts: list[str] = [f"Event '{event.event_type}' on entity '{event.entity_id}'"]

    error_msg = payload.get("error_message") or payload.get("error")
    if error_msg:
        parts.append(f"with error: {error_msg}")

    if payload.get("is_anomaly"):
        parts.append("flagged as anomalous")

    status = payload.get("status")
    if status:
        parts.append(f"status changed to '{status}'")

    if rule:
        parts.append(f"(rule: {rule.rule_name})")

    return "; ".join(parts)


def _generate_summary(
    alert: Alert,
    rule: Rule | None,
    causes: list[ProbableCause],
    events: list[Event],
) -> str:
    """Produce a natural-language analysis summary."""
    rule_desc = f" triggered by rule '{rule.rule_name}'" if rule else ""
    header = (
        f"Root-cause analysis for alert on entity '{alert.entity_id}'"
        f" (type: {alert.entity_type}){rule_desc}."
    )

    if not causes:
        return f"{header} No clear root cause identified from {len(events)} events in the 48-hour window."

    top = causes[0]
    return (
        f"{header} "
        f"Most likely cause: {top.description} "
        f"(confidence {top.confidence:.0%}, occurred at {top.occurred_at.isoformat()}). "
        f"Analyzed {len(events)} events; identified {len(causes)} potential cause(s)."
    )
