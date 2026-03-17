"""Anomaly detection — statistical baseline learning and real-time anomaly flagging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

import numpy as np
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import utc_now
from packages.db.models.event import Event

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
class BaselineProfile:
    """Statistical baseline for a given entity-type / metric pair."""

    entity_type: str
    metric: str
    mean: float
    std_dev: float
    min: float
    max: float
    percentiles: dict[str, float]  # p5, p25, p50, p75, p95
    sample_count: int
    computed_at: datetime


@dataclass(frozen=True, slots=True)
class Anomaly:
    """A single anomalous data point detected against a baseline."""

    event_id: UUID
    metric: str
    value: float
    expected_min: float
    expected_max: float
    deviation_score: float
    severity: str  # low | medium | high | critical
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class VolumeAnomaly:
    """Anomalous event-volume spike or drop."""

    event_type: str
    current_count: int
    expected_count: float
    deviation_pct: float
    direction: str  # spike | drop


# ------------------------------------------------------------------
# Detector
# ------------------------------------------------------------------


class AnomalyDetector:
    """Learns statistical baselines from historical events and detects anomalies."""

    # In-memory baseline cache keyed by (tenant_id, entity_type, metric).
    _baselines: dict[tuple[UUID, str, str], BaselineProfile]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._baselines = {}

    # ------------------------------------------------------------------
    # Baseline learning
    # ------------------------------------------------------------------

    async def learn_baseline(
        self,
        tenant_id: UUID,
        entity_type: str,
        metric: str,
        lookback_days: int = 30,
    ) -> BaselineProfile:
        """Build a statistical baseline from historical event payloads.

        The *metric* is expected to be a numeric key present in ``Event.payload``.
        """
        since = utc_now() - timedelta(days=lookback_days)

        stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.entity_type == entity_type,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )

        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        values = _extract_metric_values(events, metric)

        if len(values) == 0:
            logger.warning(
                "baseline_no_data",
                tenant_id=str(tenant_id),
                entity_type=entity_type,
                metric=metric,
            )
            profile = BaselineProfile(
                entity_type=entity_type,
                metric=metric,
                mean=0.0,
                std_dev=0.0,
                min=0.0,
                max=0.0,
                percentiles={"p5": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0},
                sample_count=0,
                computed_at=utc_now(),
            )
            self._baselines[(tenant_id, entity_type, metric)] = profile
            return profile

        arr = np.array(values, dtype=np.float64)

        profile = BaselineProfile(
            entity_type=entity_type,
            metric=metric,
            mean=float(np.mean(arr)),
            std_dev=float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
            min=float(np.min(arr)),
            max=float(np.max(arr)),
            percentiles={
                "p5": float(np.percentile(arr, 5)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
                "p95": float(np.percentile(arr, 95)),
            },
            sample_count=len(arr),
            computed_at=utc_now(),
        )

        self._baselines[(tenant_id, entity_type, metric)] = profile

        logger.info(
            "baseline_computed",
            tenant_id=str(tenant_id),
            entity_type=entity_type,
            metric=metric,
            mean=profile.mean,
            std_dev=profile.std_dev,
            sample_count=profile.sample_count,
        )
        return profile

    # ------------------------------------------------------------------
    # Point-anomaly detection
    # ------------------------------------------------------------------

    async def detect_anomalies(
        self,
        tenant_id: UUID,
        entity_type: str,
        metric: str,
        window_hours: int = 24,
    ) -> list[Anomaly]:
        """Detect metric-value anomalies in recent events.

        Values more than 2 standard deviations from the baseline mean are
        flagged.  Severity is assigned by deviation magnitude:
        - >4 sigma  -> critical
        - >3 sigma  -> high
        - >2.5 sigma -> medium
        - >2 sigma  -> low
        """
        profile = self._baselines.get((tenant_id, entity_type, metric))
        if profile is None:
            logger.info(
                "detect_anomalies_learning_baseline",
                tenant_id=str(tenant_id),
                entity_type=entity_type,
                metric=metric,
            )
            profile = await self.learn_baseline(tenant_id, entity_type, metric)

        if profile.sample_count == 0 or profile.std_dev == 0.0:
            logger.warning(
                "detect_anomalies_insufficient_baseline",
                tenant_id=str(tenant_id),
                entity_type=entity_type,
                metric=metric,
            )
            return []

        since = utc_now() - timedelta(hours=window_hours)

        stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.entity_type == entity_type,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )

        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        expected_min = profile.mean - 2 * profile.std_dev
        expected_max = profile.mean + 2 * profile.std_dev

        anomalies: list[Anomaly] = []

        for event in events:
            value = _extract_single_metric(event, metric)
            if value is None:
                continue

            deviation_score = abs(value - profile.mean) / profile.std_dev

            if deviation_score <= 2.0:
                continue

            severity = _severity_from_deviation(deviation_score)

            anomalies.append(
                Anomaly(
                    event_id=event.id,
                    metric=metric,
                    value=value,
                    expected_min=expected_min,
                    expected_max=expected_max,
                    deviation_score=round(deviation_score, 3),
                    severity=severity,
                    detected_at=utc_now(),
                )
            )

        logger.info(
            "anomalies_detected",
            tenant_id=str(tenant_id),
            entity_type=entity_type,
            metric=metric,
            window_hours=window_hours,
            count=len(anomalies),
        )
        return anomalies

    # ------------------------------------------------------------------
    # Volume-anomaly detection
    # ------------------------------------------------------------------

    async def detect_volume_anomaly(
        self,
        tenant_id: UUID,
        event_type: str,
        window_hours: int = 24,
    ) -> VolumeAnomaly | None:
        """Compare current event volume to historical average.

        Returns a ``VolumeAnomaly`` when the current window's count deviates
        by more than 40 % from the historical per-window average (computed
        over the preceding 30 days).
        """
        now = utc_now()
        window_start = now - timedelta(hours=window_hours)
        history_start = now - timedelta(days=30)

        # Current window count
        current_stmt = (
            sa.select(sa.func.count())
            .select_from(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.event_type == event_type,
                Event.occurred_at >= window_start,
            )
        )
        current_result = await self._session.execute(current_stmt)
        current_count: int = current_result.scalar() or 0

        # Historical count (last 30 days)
        hist_stmt = (
            sa.select(sa.func.count())
            .select_from(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.event_type == event_type,
                Event.occurred_at >= history_start,
                Event.occurred_at < window_start,
            )
        )
        hist_result = await self._session.execute(hist_stmt)
        hist_count: int = hist_result.scalar() or 0

        # Compute expected count per window
        history_span_hours = max(
            (window_start - history_start).total_seconds() / 3600, 1.0
        )
        windows_in_history = history_span_hours / max(window_hours, 1)
        expected_count = hist_count / max(windows_in_history, 1.0)

        if expected_count == 0:
            logger.info(
                "volume_anomaly_no_history",
                tenant_id=str(tenant_id),
                event_type=event_type,
            )
            return None

        deviation_pct = ((current_count - expected_count) / expected_count) * 100.0

        if abs(deviation_pct) <= 40.0:
            return None

        direction = "spike" if deviation_pct > 0 else "drop"

        anomaly = VolumeAnomaly(
            event_type=event_type,
            current_count=current_count,
            expected_count=round(expected_count, 2),
            deviation_pct=round(deviation_pct, 2),
            direction=direction,
        )

        logger.warning(
            "volume_anomaly_detected",
            tenant_id=str(tenant_id),
            event_type=event_type,
            direction=direction,
            deviation_pct=round(deviation_pct, 2),
            current_count=current_count,
            expected_count=round(expected_count, 2),
        )
        return anomaly


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _extract_metric_values(events: list[Event], metric: str) -> list[float]:
    """Pull numeric *metric* values from event payloads."""
    values: list[float] = []
    for event in events:
        val = _extract_single_metric(event, metric)
        if val is not None:
            values.append(val)
    return values


def _extract_single_metric(event: Event, metric: str) -> float | None:
    """Return the float value for *metric* in a single event's payload."""
    payload = event.payload or {}
    raw = payload.get(metric)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _severity_from_deviation(score: float) -> str:
    """Map a deviation score to a severity label."""
    if score > 4.0:
        return "critical"
    if score > 3.0:
        return "high"
    if score > 2.5:
        return "medium"
    return "low"
