"""Report generation service — daily/weekly summaries, SLA reports, and CSV exports."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import utc_now
from packages.db.models.alert import Alert
from packages.db.models.event import Event


# ---------------------------------------------------------------------------
# Report data models
# ---------------------------------------------------------------------------


@dataclass
class ReportSection:
    """A single section within a report."""

    title: str
    metrics: dict = field(default_factory=dict)
    charts_data: list[dict] = field(default_factory=list)
    table_data: list[dict] = field(default_factory=list)


@dataclass
class ReportData:
    """Top-level report container."""

    title: str
    period: str
    generated_at: datetime = field(default_factory=utc_now)
    sections: list[ReportSection] = field(default_factory=list)


@dataclass
class SLAReport:
    """SLA compliance report."""

    period: str
    on_time_rate: float
    avg_delay_minutes: float
    total_deliveries: int
    breaches: int
    by_entity: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generates reports and CSV exports from the OIE database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Daily summary
    # ------------------------------------------------------------------

    async def generate_daily_summary(
        self, tenant_id: UUID, target_date: date
    ) -> ReportData:
        """Generate a daily summary report.

        Includes total events, events by type, alerts generated, alerts
        resolved, and the top entities by event count.
        """
        day_start = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        # Total events
        total_events_q = (
            sa.select(sa.func.count())
            .select_from(Event)
            .where(
                Event.tenant_id == tenant_id,
                Event.created_at >= day_start,
                Event.created_at < day_end,
            )
        )
        total_events = (await self._session.execute(total_events_q)).scalar_one_or_none() or 0

        # Events by type
        by_type_q = (
            sa.select(Event.event_type, sa.func.count())
            .where(
                Event.tenant_id == tenant_id,
                Event.created_at >= day_start,
                Event.created_at < day_end,
            )
            .group_by(Event.event_type)
            .order_by(sa.func.count().desc())
            .limit(10)
        )
        by_type_rows = (await self._session.execute(by_type_q)).all()
        events_by_type = {row[0]: row[1] for row in by_type_rows}

        # Alerts generated
        alerts_generated_q = (
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.created_at >= day_start,
                Alert.created_at < day_end,
            )
        )
        alerts_generated = (await self._session.execute(alerts_generated_q)).scalar_one_or_none() or 0

        # Alerts resolved
        alerts_resolved_q = (
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.resolved_at >= day_start,
                Alert.resolved_at < day_end,
            )
        )
        alerts_resolved = (await self._session.execute(alerts_resolved_q)).scalar_one_or_none() or 0

        # Top entities
        top_entities_q = (
            sa.select(Event.entity_id, Event.entity_type, sa.func.count().label("cnt"))
            .where(
                Event.tenant_id == tenant_id,
                Event.created_at >= day_start,
                Event.created_at < day_end,
            )
            .group_by(Event.entity_id, Event.entity_type)
            .order_by(sa.text("cnt DESC"))
            .limit(5)
        )
        top_entity_rows = (await self._session.execute(top_entities_q)).all()
        top_entities = [
            {"entity_id": r[0], "entity_type": r[1], "count": r[2]}
            for r in top_entity_rows
        ]

        return ReportData(
            title=f"Daily Summary — {target_date.isoformat()}",
            period=target_date.isoformat(),
            sections=[
                ReportSection(
                    title="Overview",
                    metrics={
                        "total_events": total_events,
                        "alerts_generated": alerts_generated,
                        "alerts_resolved": alerts_resolved,
                    },
                ),
                ReportSection(
                    title="Events by Type",
                    metrics=events_by_type,
                    charts_data=[
                        {"type": k, "count": v} for k, v in events_by_type.items()
                    ],
                ),
                ReportSection(
                    title="Top Entities",
                    table_data=top_entities,
                ),
            ],
        )

    # ------------------------------------------------------------------
    # Weekly summary
    # ------------------------------------------------------------------

    async def generate_weekly_summary(
        self, tenant_id: UUID, week_start: date
    ) -> ReportData:
        """Generate a weekly summary report.

        Includes daily trends, top rules triggered, and SLA compliance rate.
        """
        start_dt = datetime(
            week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc
        )
        end_dt = start_dt + timedelta(days=7)

        # Day-over-day event counts
        daily_counts: list[dict] = []
        for offset in range(7):
            d_start = start_dt + timedelta(days=offset)
            d_end = d_start + timedelta(days=1)
            cnt_q = (
                sa.select(sa.func.count())
                .select_from(Event)
                .where(
                    Event.tenant_id == tenant_id,
                    Event.created_at >= d_start,
                    Event.created_at < d_end,
                )
            )
            cnt = (await self._session.execute(cnt_q)).scalar_one_or_none() or 0
            daily_counts.append({
                "date": (week_start + timedelta(days=offset)).isoformat(),
                "events": cnt,
            })

        # Top rules triggered
        top_rules_q = (
            sa.select(Alert.rule_id, sa.func.count().label("cnt"))
            .where(
                Alert.tenant_id == tenant_id,
                Alert.created_at >= start_dt,
                Alert.created_at < end_dt,
            )
            .group_by(Alert.rule_id)
            .order_by(sa.text("cnt DESC"))
            .limit(10)
        )
        top_rules_rows = (await self._session.execute(top_rules_q)).all()
        top_rules = [
            {"rule_id": str(r[0]), "count": r[1]} for r in top_rules_rows
        ]

        # SLA compliance (alerts resolved within 60 min target)
        total_alerts_q = (
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.created_at >= start_dt,
                Alert.created_at < end_dt,
            )
        )
        total_alerts = (await self._session.execute(total_alerts_q)).scalar_one_or_none() or 0

        resolved_q = (
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.created_at >= start_dt,
                Alert.created_at < end_dt,
                Alert.resolved_at.isnot(None),
            )
        )
        resolved = (await self._session.execute(resolved_q)).scalar_one_or_none() or 0

        sla_rate = (resolved / total_alerts * 100) if total_alerts > 0 else 100.0

        return ReportData(
            title=f"Weekly Summary — {week_start.isoformat()}",
            period=f"{week_start.isoformat()} to {(week_start + timedelta(days=6)).isoformat()}",
            sections=[
                ReportSection(
                    title="Weekly Trends",
                    charts_data=daily_counts,
                    metrics={
                        "total_alerts": total_alerts,
                        "resolved_alerts": resolved,
                        "sla_compliance_rate": round(sla_rate, 1),
                    },
                ),
                ReportSection(
                    title="Top Rules Triggered",
                    table_data=top_rules,
                ),
            ],
        )

    # ------------------------------------------------------------------
    # SLA report
    # ------------------------------------------------------------------

    async def generate_sla_report(
        self, tenant_id: UUID, period_start: date, period_end: date
    ) -> SLAReport:
        """Generate an SLA compliance report for the given period."""
        start_dt = datetime(
            period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc
        )
        end_dt = datetime(
            period_end.year, period_end.month, period_end.day, tzinfo=timezone.utc
        ) + timedelta(days=1)

        # All alerts in period
        alerts_q = sa.select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.created_at >= start_dt,
            Alert.created_at < end_dt,
        )
        result = await self._session.execute(alerts_q)
        alerts = list(result.scalars().all())

        total = len(alerts)
        breaches = 0
        delays: list[float] = []
        entity_stats: dict[str, dict] = {}

        sla_target = 60.0  # minutes

        for alert in alerts:
            created = alert.created_at
            resolved = getattr(alert, "resolved_at", None)

            if resolved and created:
                delay = (resolved - created).total_seconds() / 60
                delays.append(delay)
                if delay > sla_target:
                    breaches += 1
            elif created:
                # Unresolved — check elapsed time
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                elapsed = (utc_now() - created).total_seconds() / 60
                if elapsed > sla_target:
                    breaches += 1
                delays.append(elapsed)

            # Per-entity tracking
            eid = getattr(alert, "entity_id", "unknown")
            if eid not in entity_stats:
                entity_stats[eid] = {"entity_id": eid, "total": 0, "breaches": 0}
            entity_stats[eid]["total"] += 1
            if (resolved and created and (resolved - created).total_seconds() / 60 > sla_target):
                entity_stats[eid]["breaches"] += 1

        avg_delay = sum(delays) / len(delays) if delays else 0.0
        on_time = ((total - breaches) / total * 100) if total > 0 else 100.0

        # Sort entities by breaches descending
        by_entity = sorted(entity_stats.values(), key=lambda e: e["breaches"], reverse=True)

        return SLAReport(
            period=f"{period_start.isoformat()} to {period_end.isoformat()}",
            on_time_rate=round(on_time, 1),
            avg_delay_minutes=round(avg_delay, 1),
            total_deliveries=total,
            breaches=breaches,
            by_entity=by_entity[:10],
        )

    # ------------------------------------------------------------------
    # CSV exports
    # ------------------------------------------------------------------

    async def export_events_csv(
        self, tenant_id: UUID, filters: dict
    ) -> str:
        """Export filtered events as a CSV string."""
        stmt = sa.select(Event).where(Event.tenant_id == tenant_id)

        if filters.get("event_type"):
            stmt = stmt.where(Event.event_type == filters["event_type"])
        if filters.get("entity_type"):
            stmt = stmt.where(Event.entity_type == filters["entity_type"])
        if filters.get("entity_id"):
            stmt = stmt.where(Event.entity_id == filters["entity_id"])
        if filters.get("from_date"):
            stmt = stmt.where(Event.created_at >= filters["from_date"])
        if filters.get("to_date"):
            stmt = stmt.where(Event.created_at <= filters["to_date"])

        stmt = stmt.order_by(Event.created_at.desc()).limit(
            int(filters.get("limit", 10000))
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "event_type", "entity_type", "entity_id",
            "payload", "created_at",
        ])
        for row in rows:
            writer.writerow([
                str(row.id),
                str(row.tenant_id),
                row.event_type,
                row.entity_type,
                row.entity_id,
                str(getattr(row, "payload", "")),
                str(row.created_at),
            ])
        return output.getvalue()

    async def export_alerts_csv(
        self, tenant_id: UUID, filters: dict
    ) -> str:
        """Export filtered alerts as a CSV string."""
        stmt = sa.select(Alert).where(Alert.tenant_id == tenant_id)

        if filters.get("severity"):
            stmt = stmt.where(Alert.severity == filters["severity"])
        if filters.get("status"):
            stmt = stmt.where(Alert.status == filters["status"])
        if filters.get("entity_type"):
            stmt = stmt.where(Alert.entity_type == filters["entity_type"])
        if filters.get("from_date"):
            stmt = stmt.where(Alert.created_at >= filters["from_date"])
        if filters.get("to_date"):
            stmt = stmt.where(Alert.created_at <= filters["to_date"])

        stmt = stmt.order_by(Alert.created_at.desc()).limit(
            int(filters.get("limit", 10000))
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "rule_id", "entity_type", "entity_id",
            "severity", "status", "message", "created_at", "resolved_at",
        ])
        for row in rows:
            writer.writerow([
                str(row.id),
                str(row.tenant_id),
                str(row.rule_id),
                row.entity_type,
                row.entity_id,
                row.severity,
                row.status,
                row.message,
                str(row.created_at),
                str(getattr(row, "resolved_at", "")),
            ])
        return output.getvalue()
