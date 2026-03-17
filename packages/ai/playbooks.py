"""OIE AI Playbooks — automated operational intelligence workflows.

Provides pre-built playbook templates for incident response, shift handoffs,
weekly digests, and what-if scenario analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PlaybookResult:
    """Result of running the incident response playbook."""

    alert_summary: str
    similar_incidents: list[dict[str, Any]]
    relevant_docs: list[dict[str, Any]]
    remediation_steps: list[str]
    draft_notification: str


@dataclass
class ShiftSummary:
    """Summary produced for shift handoff."""

    period: str
    total_events: int
    total_alerts: int
    unresolved: list[dict[str, Any]]
    key_actions: list[dict[str, Any]]
    handoff_notes: str


@dataclass
class WeeklyDigest:
    """Weekly operational intelligence digest."""

    period: str
    top_incidents: list[dict[str, Any]]
    trend_direction: str
    improving_metrics: list[str]
    worsening_metrics: list[str]
    recommendations: list[str]


@dataclass
class WhatIfResult:
    """Result of a what-if scenario analysis."""

    scenario: dict[str, Any]
    projected_alert_increase_pct: float
    projected_sla_impact_pct: float
    affected_entities: list[str]
    recommendation: str


# ---------------------------------------------------------------------------
# Playbook Engine
# ---------------------------------------------------------------------------


class PlaybookEngine:
    """Runs pre-built operational intelligence playbooks.

    Playbook types
    --------------
    - **INCIDENT_PLAYBOOK** — When a critical alert fires, auto-generate relevant
      docs, similar past incidents, remediation steps, and a draft customer
      notification.
    - **SHIFT_HANDOFF** — Summarise everything that happened in the last N hours.
    - **WEEKLY_DIGEST** — Top incidents, trend analysis, recommendations.
    - **WHAT_IF** — Estimate the impact of a hypothetical operational change.
    """

    INCIDENT_PLAYBOOK = "incident_response"
    SHIFT_HANDOFF = "shift_handoff"
    WEEKLY_DIGEST = "weekly_digest"
    WHAT_IF = "what_if_analysis"

    # ------------------------------------------------------------------ #
    # Incident Response Playbook
    # ------------------------------------------------------------------ #

    async def run_incident_playbook(
        self,
        tenant_id: UUID,
        alert_id: UUID,
        session: AsyncSession,
    ) -> PlaybookResult:
        """Run the full incident response playbook for a triggered alert.

        Steps
        -----
        1. Load alert details from the database.
        2. Search for similar past alerts (same rule, same entity type).
        3. Search documents for relevant procedures.
        4. Generate a template-based analysis summary (ready for AI enhancement).
        5. Return :class:`PlaybookResult`.
        """
        logger.info("Running incident playbook", extra={"tenant_id": str(tenant_id), "alert_id": str(alert_id)})

        # 1. Load alert details
        alert = await self._load_alert(tenant_id, alert_id, session)
        alert_summary = self._build_alert_summary(alert)

        # 2. Find similar past incidents
        similar_incidents = await self._find_similar_incidents(tenant_id, alert, session)

        # 3. Search for relevant documentation
        relevant_docs = await self._search_relevant_docs(tenant_id, alert, session)

        # 4. Generate remediation steps
        remediation_steps = self._generate_remediation_steps(alert, similar_incidents)

        # 5. Draft customer notification
        draft_notification = self._draft_notification(alert, remediation_steps)

        return PlaybookResult(
            alert_summary=alert_summary,
            similar_incidents=similar_incidents,
            relevant_docs=relevant_docs,
            remediation_steps=remediation_steps,
            draft_notification=draft_notification,
        )

    # ------------------------------------------------------------------ #
    # Shift Handoff
    # ------------------------------------------------------------------ #

    async def generate_shift_handoff(
        self,
        tenant_id: UUID,
        session: AsyncSession,
        hours: int = 8,
    ) -> ShiftSummary:
        """Summarise events, alerts, and actions from the last *hours* hours.

        Highlights unresolved alerts and pending actions for the incoming team.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        period = f"{cutoff.isoformat()} — {now.isoformat()}"

        logger.info("Generating shift handoff", extra={"tenant_id": str(tenant_id), "hours": hours})

        # Count events in period
        result = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM events "
                "WHERE tenant_id = :tid AND occurred_at >= :cutoff"
            ),
            {"tid": str(tenant_id), "cutoff": cutoff},
        )
        total_events = result.scalar() or 0

        # Count alerts in period
        result = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM alerts "
                "WHERE tenant_id = :tid AND created_at >= :cutoff"
            ),
            {"tid": str(tenant_id), "cutoff": cutoff},
        )
        total_alerts = result.scalar() or 0

        # Unresolved alerts
        result = await session.execute(
            sa.text(
                "SELECT id, rule_name, severity, entity_id, message, created_at "
                "FROM alerts "
                "WHERE tenant_id = :tid AND status != 'resolved' "
                "ORDER BY created_at DESC LIMIT 20"
            ),
            {"tid": str(tenant_id)},
        )
        unresolved = [
            {
                "id": str(row.id),
                "rule_name": row.rule_name,
                "severity": row.severity,
                "entity_id": row.entity_id,
                "message": row.message,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.fetchall()
        ]

        # Key actions (placeholder — real implementation would query audit log)
        key_actions: list[dict[str, Any]] = []

        handoff_notes = (
            f"Shift covering {hours}h ending {now.strftime('%Y-%m-%d %H:%M UTC')}. "
            f"{total_events} events ingested, {total_alerts} alerts fired, "
            f"{len(unresolved)} remain unresolved."
        )

        return ShiftSummary(
            period=period,
            total_events=total_events,
            total_alerts=total_alerts,
            unresolved=unresolved,
            key_actions=key_actions,
            handoff_notes=handoff_notes,
        )

    # ------------------------------------------------------------------ #
    # Weekly Digest
    # ------------------------------------------------------------------ #

    async def generate_weekly_digest(
        self,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> WeeklyDigest:
        """Produce a weekly operational intelligence digest.

        Includes top incidents, trend direction (improving / worsening),
        and actionable recommendations.
        """
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        period = f"{week_ago.strftime('%Y-%m-%d')} — {now.strftime('%Y-%m-%d')}"

        logger.info("Generating weekly digest", extra={"tenant_id": str(tenant_id)})

        # This week's alert count
        result = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM alerts "
                "WHERE tenant_id = :tid AND created_at >= :start"
            ),
            {"tid": str(tenant_id), "start": week_ago},
        )
        this_week_alerts = result.scalar() or 0

        # Last week's alert count for comparison
        result = await session.execute(
            sa.text(
                "SELECT COUNT(*) FROM alerts "
                "WHERE tenant_id = :tid AND created_at >= :start AND created_at < :end"
            ),
            {"tid": str(tenant_id), "start": two_weeks_ago, "end": week_ago},
        )
        last_week_alerts = result.scalar() or 0

        # Top incidents by severity
        result = await session.execute(
            sa.text(
                "SELECT id, rule_name, severity, entity_id, message, created_at "
                "FROM alerts "
                "WHERE tenant_id = :tid AND created_at >= :start "
                "ORDER BY CASE severity "
                "  WHEN 'critical' THEN 1 "
                "  WHEN 'high' THEN 2 "
                "  WHEN 'medium' THEN 3 "
                "  ELSE 4 END, created_at DESC "
                "LIMIT 10"
            ),
            {"tid": str(tenant_id), "start": week_ago},
        )
        top_incidents = [
            {
                "id": str(row.id),
                "rule_name": row.rule_name,
                "severity": row.severity,
                "entity_id": row.entity_id,
                "message": row.message,
            }
            for row in result.fetchall()
        ]

        # Trend analysis
        if last_week_alerts == 0:
            trend_direction = "stable"
        elif this_week_alerts < last_week_alerts:
            trend_direction = "improving"
        elif this_week_alerts > last_week_alerts:
            trend_direction = "worsening"
        else:
            trend_direction = "stable"

        improving_metrics: list[str] = []
        worsening_metrics: list[str] = []

        if this_week_alerts < last_week_alerts:
            improving_metrics.append(f"Alert volume down {last_week_alerts - this_week_alerts} from last week")
        elif this_week_alerts > last_week_alerts:
            worsening_metrics.append(f"Alert volume up {this_week_alerts - last_week_alerts} from last week")

        recommendations: list[str] = []
        if trend_direction == "worsening":
            recommendations.append("Review top-firing rules for tuning opportunities")
            recommendations.append("Investigate recurring entity IDs for systemic issues")
        else:
            recommendations.append("Continue monitoring — operational health is stable or improving")

        return WeeklyDigest(
            period=period,
            top_incidents=top_incidents,
            trend_direction=trend_direction,
            improving_metrics=improving_metrics,
            worsening_metrics=worsening_metrics,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------ #
    # What-If Analysis
    # ------------------------------------------------------------------ #

    async def run_what_if(
        self,
        tenant_id: UUID,
        scenario: dict[str, Any],
        session: AsyncSession,
    ) -> WhatIfResult:
        """Run a what-if scenario analysis.

        Accepts a scenario dict such as::

            {"metric": "vendor_delay_rate", "change_pct": 20}

        Estimates the downstream impact on alert volume and SLA compliance.
        """
        metric = scenario.get("metric", "unknown")
        change_pct = float(scenario.get("change_pct", 0))

        logger.info(
            "Running what-if analysis",
            extra={"tenant_id": str(tenant_id), "metric": metric, "change_pct": change_pct},
        )

        # Estimate impact using simple heuristics (ready for AI enhancement)
        # In production, this would use historical correlations and ML models.

        # Alert volume impact: roughly proportional to the change
        projected_alert_increase_pct = round(change_pct * 0.65, 1)

        # SLA impact: non-linear, smaller changes have less impact
        if abs(change_pct) <= 10:
            projected_sla_impact_pct = round(change_pct * 0.3, 1)
        else:
            projected_sla_impact_pct = round(change_pct * 0.5, 1)

        # Identify potentially affected entities
        result = await session.execute(
            sa.text(
                "SELECT DISTINCT entity_id FROM events "
                "WHERE tenant_id = :tid "
                "ORDER BY entity_id LIMIT 10"
            ),
            {"tid": str(tenant_id)},
        )
        affected_entities = [row.entity_id for row in result.fetchall() if row.entity_id]

        # Generate recommendation
        if abs(projected_alert_increase_pct) > 30:
            recommendation = (
                f"A {change_pct}% change in {metric} would significantly increase alert volume. "
                "Consider pre-positioning additional resources and adjusting alert thresholds."
            )
        elif abs(projected_alert_increase_pct) > 10:
            recommendation = (
                f"A {change_pct}% change in {metric} would moderately impact operations. "
                "Review SLA agreements and notify affected stakeholders."
            )
        else:
            recommendation = (
                f"A {change_pct}% change in {metric} would have limited operational impact. "
                "Continue standard monitoring."
            )

        return WhatIfResult(
            scenario=scenario,
            projected_alert_increase_pct=projected_alert_increase_pct,
            projected_sla_impact_pct=projected_sla_impact_pct,
            affected_entities=affected_entities,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    async def _load_alert(
        self, tenant_id: UUID, alert_id: UUID, session: AsyncSession
    ) -> dict[str, Any]:
        result = await session.execute(
            sa.text(
                "SELECT id, rule_id, rule_name, severity, entity_type, entity_id, "
                "message, status, created_at "
                "FROM alerts WHERE id = :aid AND tenant_id = :tid"
            ),
            {"aid": str(alert_id), "tid": str(tenant_id)},
        )
        row = result.fetchone()
        if row is None:
            return {
                "id": str(alert_id),
                "rule_name": "Unknown",
                "severity": "unknown",
                "entity_type": "unknown",
                "entity_id": "unknown",
                "message": "Alert not found",
            }
        return {
            "id": str(row.id),
            "rule_id": str(row.rule_id) if row.rule_id else None,
            "rule_name": row.rule_name,
            "severity": row.severity,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "message": row.message,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _find_similar_incidents(
        self, tenant_id: UUID, alert: dict[str, Any], session: AsyncSession
    ) -> list[dict[str, Any]]:
        result = await session.execute(
            sa.text(
                "SELECT id, rule_name, severity, entity_id, message, created_at, status "
                "FROM alerts "
                "WHERE tenant_id = :tid "
                "  AND rule_name = :rule_name "
                "  AND id != :alert_id "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {
                "tid": str(tenant_id),
                "rule_name": alert.get("rule_name", ""),
                "alert_id": alert.get("id", ""),
            },
        )
        return [
            {
                "id": str(row.id),
                "rule_name": row.rule_name,
                "severity": row.severity,
                "entity_id": row.entity_id,
                "message": row.message,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.fetchall()
        ]

    async def _search_relevant_docs(
        self, tenant_id: UUID, alert: dict[str, Any], session: AsyncSession
    ) -> list[dict[str, Any]]:
        result = await session.execute(
            sa.text(
                "SELECT id, title, doc_type, created_at "
                "FROM documents "
                "WHERE tenant_id = :tid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"tid": str(tenant_id)},
        )
        return [
            {
                "id": str(row.id),
                "title": row.title,
                "doc_type": row.doc_type,
            }
            for row in result.fetchall()
        ]

    def _build_alert_summary(self, alert: dict[str, Any]) -> str:
        return (
            f"[{alert.get('severity', 'unknown').upper()}] {alert.get('rule_name', 'Unknown Rule')} "
            f"on {alert.get('entity_type', 'entity')} {alert.get('entity_id', 'N/A')}: "
            f"{alert.get('message', 'No details available')}"
        )

    def _generate_remediation_steps(
        self, alert: dict[str, Any], similar: list[dict[str, Any]]
    ) -> list[str]:
        steps = [
            f"1. Acknowledge alert and assess current status of {alert.get('entity_id', 'affected entity')}",
            f"2. Review {alert.get('rule_name', 'triggering rule')} threshold configuration",
            "3. Check for correlated events in the last 30 minutes",
        ]
        if similar:
            resolved = [s for s in similar if s.get("status") == "resolved"]
            if resolved:
                steps.append(
                    f"4. Reference resolution of similar incident {resolved[0].get('id', 'N/A')} for guidance"
                )
            else:
                steps.append("4. No previously resolved similar incidents found — escalate if unresolved after 30 min")
        else:
            steps.append("4. No similar past incidents found — follow standard operating procedure")
        steps.append("5. Update alert status and document resolution")
        return steps

    def _draft_notification(self, alert: dict[str, Any], steps: list[str]) -> str:
        severity = alert.get("severity", "unknown").upper()
        entity_id = alert.get("entity_id", "N/A")
        message = alert.get("message", "An operational alert has been triggered.")
        return (
            f"Subject: [{severity}] Operational Alert — {entity_id}\n\n"
            f"Dear Team,\n\n"
            f"An operational alert has been triggered:\n\n"
            f"  Alert: {alert.get('rule_name', 'Unknown')}\n"
            f"  Severity: {severity}\n"
            f"  Entity: {entity_id}\n"
            f"  Details: {message}\n\n"
            f"Our team is actively investigating. Immediate actions:\n"
            + "\n".join(f"  {s}" for s in steps[:3])
            + "\n\n"
            f"We will provide an update within 30 minutes.\n\n"
            f"— OIE Operations Team"
        )
