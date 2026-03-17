"""Predictive engine — SLA breach forecasting, delay prediction, and risk scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

import numpy as np
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import AlertStatus, utc_now
from packages.db.models.alert import Alert
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
class SLAPrediction:
    """Prediction of an upcoming SLA breach for a specific entity."""

    entity_id: str
    entity_type: str
    predicted_completion: datetime
    sla_deadline: datetime
    breach_probability: float
    contributing_factors: list[str]


@dataclass(frozen=True, slots=True)
class DelayPrediction:
    """Prediction that an entity is trending toward a delay threshold breach."""

    entity_id: str
    entity_type: str
    current_delay_minutes: float
    predicted_delay_minutes: float
    confidence: float
    trend_direction: str  # increasing | stable | decreasing


@dataclass(frozen=True, slots=True)
class EntityRisk:
    """Composite risk score for an operational entity."""

    entity_id: str
    entity_type: str
    risk_score: float  # 0-100
    factors: list[str]
    alert_count: int
    anomaly_count: int


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------


class PredictiveEngine:
    """Forecasts SLA breaches, delays, and entity-level risk."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # SLA breach prediction
    # ------------------------------------------------------------------

    async def predict_sla_breach(
        self,
        tenant_id: UUID,
        entity_id: str,
        entity_type: str,
    ) -> SLAPrediction | None:
        """Predict whether *entity_id* will breach its SLA.

        The method inspects the entity's recent event history, extracts
        ``progress_pct``, ``elapsed_minutes``, and ``sla_deadline`` from
        payloads, then projects completion time via linear extrapolation.
        """
        since = utc_now() - timedelta(hours=72)

        stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.entity_type == entity_type,
                Event.entity_id == entity_id,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )

        result = await self._session.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            logger.info(
                "sla_prediction_no_events",
                tenant_id=str(tenant_id),
                entity_id=entity_id,
            )
            return None

        # Extract progress data points: (elapsed_minutes, progress_pct)
        data_points: list[tuple[float, float]] = []
        sla_deadline: datetime | None = None

        for event in events:
            payload = event.payload or {}
            elapsed = payload.get("elapsed_minutes")
            progress = payload.get("progress_pct")
            deadline_raw = payload.get("sla_deadline")

            if elapsed is not None and progress is not None:
                try:
                    data_points.append((float(elapsed), float(progress)))
                except (TypeError, ValueError):
                    continue

            if deadline_raw is not None and sla_deadline is None:
                try:
                    if isinstance(deadline_raw, str):
                        sla_deadline = datetime.fromisoformat(deadline_raw)
                    elif isinstance(deadline_raw, datetime):
                        sla_deadline = deadline_raw
                except (TypeError, ValueError):
                    pass

        if len(data_points) < 2 or sla_deadline is None:
            logger.info(
                "sla_prediction_insufficient_data",
                tenant_id=str(tenant_id),
                entity_id=entity_id,
                data_points=len(data_points),
            )
            return None

        # Linear regression: progress_pct = a * elapsed_minutes + b
        elapsed_arr = np.array([dp[0] for dp in data_points], dtype=np.float64)
        progress_arr = np.array([dp[1] for dp in data_points], dtype=np.float64)

        coeffs = np.polyfit(elapsed_arr, progress_arr, deg=1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])

        if slope <= 0:
            # Progress stalled or regressing — breach very likely
            contributing_factors = [
                "Progress rate is zero or negative",
                f"Current progress slope: {slope:.4f}%/min",
            ]
            return SLAPrediction(
                entity_id=entity_id,
                entity_type=entity_type,
                predicted_completion=sla_deadline + timedelta(hours=24),
                sla_deadline=sla_deadline,
                breach_probability=0.95,
                contributing_factors=contributing_factors,
            )

        # Time to reach 100 %
        current_elapsed = float(elapsed_arr[-1])
        current_progress = float(slope * current_elapsed + intercept)
        remaining_pct = max(100.0 - current_progress, 0.0)
        minutes_to_complete = remaining_pct / slope

        predicted_completion = utc_now() + timedelta(minutes=minutes_to_complete)

        if predicted_completion <= sla_deadline:
            return None  # On track

        # Compute breach probability heuristic
        margin_minutes = (predicted_completion - sla_deadline).total_seconds() / 60.0
        total_window = max(
            (sla_deadline - events[0].occurred_at).total_seconds() / 60.0, 1.0
        )
        breach_probability = min(margin_minutes / total_window + 0.5, 0.99)

        contributing_factors = [
            f"Current progress rate: {slope:.4f}%/min",
            f"Predicted completion exceeds SLA by {margin_minutes:.0f} minutes",
            f"Based on {len(data_points)} data points",
        ]

        prediction = SLAPrediction(
            entity_id=entity_id,
            entity_type=entity_type,
            predicted_completion=predicted_completion,
            sla_deadline=sla_deadline,
            breach_probability=round(breach_probability, 3),
            contributing_factors=contributing_factors,
        )

        logger.warning(
            "sla_breach_predicted",
            tenant_id=str(tenant_id),
            entity_id=entity_id,
            breach_probability=prediction.breach_probability,
            margin_minutes=round(margin_minutes, 1),
        )
        return prediction

    # ------------------------------------------------------------------
    # Delay prediction
    # ------------------------------------------------------------------

    async def predict_delay(
        self,
        tenant_id: UUID,
        entity_type: str,
        lookback_hours: int = 48,
    ) -> list[DelayPrediction]:
        """Identify entities with worsening delay trends.

        Scans events with a ``delay_minutes`` payload field, groups by
        entity, and fits a linear trend.  Entities whose projected delay
        exceeds 1.5x current delay are returned.
        """
        since = utc_now() - timedelta(hours=lookback_hours)

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

        # Group delay readings by entity
        entity_delays: dict[str, list[tuple[float, float]]] = {}

        for event in events:
            payload = event.payload or {}
            delay = payload.get("delay_minutes")
            if delay is None:
                continue
            try:
                delay_val = float(delay)
            except (TypeError, ValueError):
                continue

            offset_minutes = (
                event.occurred_at - since
            ).total_seconds() / 60.0

            entity_delays.setdefault(event.entity_id, []).append(
                (offset_minutes, delay_val)
            )

        predictions: list[DelayPrediction] = []

        for entity_id, points in entity_delays.items():
            if len(points) < 2:
                continue

            times = np.array([p[0] for p in points], dtype=np.float64)
            delays = np.array([p[1] for p in points], dtype=np.float64)

            coeffs = np.polyfit(times, delays, deg=1)
            slope = float(coeffs[0])

            current_delay = float(delays[-1])
            # Project forward by the same lookback window
            projected = float(np.polyval(coeffs, times[-1] + lookback_hours * 60))

            if slope > 0 and projected > current_delay * 1.5:
                trend_direction = "increasing"
            elif slope < 0:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"

            # Only report entities trending toward breach
            if trend_direction != "increasing":
                continue

            # Confidence based on R-squared
            residuals = delays - np.polyval(coeffs, times)
            ss_res = float(np.sum(residuals**2))
            ss_tot = float(np.sum((delays - np.mean(delays)) ** 2))
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            confidence = max(min(r_squared, 1.0), 0.0)

            predictions.append(
                DelayPrediction(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    current_delay_minutes=round(current_delay, 2),
                    predicted_delay_minutes=round(max(projected, 0.0), 2),
                    confidence=round(confidence, 3),
                    trend_direction=trend_direction,
                )
            )

        predictions.sort(key=lambda p: p.predicted_delay_minutes, reverse=True)

        logger.info(
            "delay_predictions_computed",
            tenant_id=str(tenant_id),
            entity_type=entity_type,
            entities_analyzed=len(entity_delays),
            predictions_count=len(predictions),
        )
        return predictions

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    async def get_risk_scores(
        self,
        tenant_id: UUID,
    ) -> list[EntityRisk]:
        """Compute composite risk scores for all entities with recent activity.

        The score (0-100) blends:
        - Active alert count (weight 40)
        - Recent anomaly indicators in payloads (weight 30)
        - Delay trend severity (weight 30)
        """
        since = utc_now() - timedelta(hours=48)

        # 1. Gather recent events per entity
        event_stmt = (
            sa.select(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.occurred_at >= since,
            )
            .order_by(Event.occurred_at.asc())
        )
        event_result = await self._session.execute(event_stmt)
        events = list(event_result.scalars().all())

        entity_events: dict[tuple[str, str], list[Event]] = {}
        for event in events:
            key = (event.entity_id, event.entity_type)
            entity_events.setdefault(key, []).append(event)

        # 2. Active alert counts per entity
        alert_stmt = (
            sa.select(Alert.entity_id, Alert.entity_type, sa.func.count())
            .where(
                Alert.tenant_id == tenant_id,
                Alert.status == AlertStatus.ACTIVE,
            )
            .group_by(Alert.entity_id, Alert.entity_type)
        )
        alert_result = await self._session.execute(alert_stmt)
        alert_counts: dict[tuple[str, str], int] = {
            (row[0], row[1]): row[2] for row in alert_result.all()
        }

        # 3. Score each entity
        risk_scores: list[EntityRisk] = []

        for (entity_id, entity_type), evts in entity_events.items():
            factors: list[str] = []
            alert_count = alert_counts.get((entity_id, entity_type), 0)

            # Alert component (0-40)
            alert_score = min(alert_count * 10.0, 40.0)
            if alert_count > 0:
                factors.append(f"{alert_count} active alert(s)")

            # Anomaly component (0-30): count events flagged with anomaly
            anomaly_count = 0
            for evt in evts:
                payload = evt.payload or {}
                if payload.get("is_anomaly") or payload.get("anomaly_score", 0) > 0:
                    anomaly_count += 1
            anomaly_score = min(anomaly_count * 6.0, 30.0)
            if anomaly_count > 0:
                factors.append(f"{anomaly_count} anomalous event(s)")

            # Delay component (0-30): average delay_minutes
            delay_values: list[float] = []
            for evt in evts:
                payload = evt.payload or {}
                delay = payload.get("delay_minutes")
                if delay is not None:
                    try:
                        delay_values.append(float(delay))
                    except (TypeError, ValueError):
                        continue

            delay_score = 0.0
            if delay_values:
                avg_delay = float(np.mean(delay_values))
                # Scale: 60 min delay -> 30 points
                delay_score = min((avg_delay / 60.0) * 30.0, 30.0)
                if avg_delay > 0:
                    factors.append(f"Average delay {avg_delay:.1f} min")

            composite = round(alert_score + anomaly_score + delay_score, 1)
            composite = min(composite, 100.0)

            risk_scores.append(
                EntityRisk(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    risk_score=composite,
                    factors=factors,
                    alert_count=alert_count,
                    anomaly_count=anomaly_count,
                )
            )

        risk_scores.sort(key=lambda r: r.risk_score, reverse=True)

        logger.info(
            "risk_scores_computed",
            tenant_id=str(tenant_id),
            entities_scored=len(risk_scores),
        )
        return risk_scores
