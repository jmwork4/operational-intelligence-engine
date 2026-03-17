"""Report routes — daily/weekly summaries, SLA reports, and CSV exports."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from packages.reporting.generator import ReportGenerator

from apps.api.deps import RateLimiter, get_current_tenant, get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report_data_to_dict(rd) -> dict:
    """Serialise a ReportData instance to a plain dict."""
    return {
        "title": rd.title,
        "period": rd.period,
        "generated_at": rd.generated_at.isoformat(),
        "sections": [
            {
                "title": s.title,
                "metrics": s.metrics,
                "charts_data": s.charts_data,
                "table_data": s.table_data,
            }
            for s in rd.sections
        ],
    }


def _sla_report_to_dict(sr) -> dict:
    """Serialise an SLAReport instance to a plain dict."""
    return {
        "period": sr.period,
        "on_time_rate": sr.on_time_rate,
        "avg_delay_minutes": sr.avg_delay_minutes,
        "total_deliveries": sr.total_deliveries,
        "breaches": sr.breaches,
        "by_entity": sr.by_entity,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/daily",
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def daily_summary(
    target_date: str = Query(alias="date", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict:
    """Generate a daily summary report."""
    d = date.fromisoformat(target_date)
    gen = ReportGenerator(db)
    report = await gen.generate_daily_summary(tenant_id, d)
    return _report_data_to_dict(report)


@router.get(
    "/weekly",
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def weekly_summary(
    week_start: str = Query(description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict:
    """Generate a weekly summary report."""
    d = date.fromisoformat(week_start)
    gen = ReportGenerator(db)
    report = await gen.generate_weekly_summary(tenant_id, d)
    return _report_data_to_dict(report)


@router.get(
    "/sla",
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def sla_report(
    start: str = Query(description="YYYY-MM-DD"),
    end: str = Query(description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict:
    """Generate an SLA compliance report."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    gen = ReportGenerator(db)
    report = await gen.generate_sla_report(tenant_id, s, e)
    return _sla_report_to_dict(report)


@router.get(
    "/export/events",
    dependencies=[Depends(RateLimiter(requests_per_minute=30))],
)
async def export_events(
    format: str = Query(default="csv"),
    event_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PlainTextResponse:
    """Export events as CSV."""
    filters: dict = {}
    if event_type:
        filters["event_type"] = event_type
    if entity_type:
        filters["entity_type"] = entity_type
    if entity_id:
        filters["entity_id"] = entity_id
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    gen = ReportGenerator(db)
    csv_str = await gen.export_events_csv(tenant_id, filters)
    return PlainTextResponse(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_export.csv"},
    )


@router.get(
    "/export/alerts",
    dependencies=[Depends(RateLimiter(requests_per_minute=30))],
)
async def export_alerts(
    format: str = Query(default="csv"),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PlainTextResponse:
    """Export alerts as CSV."""
    filters: dict = {}
    if severity:
        filters["severity"] = severity
    if status:
        filters["status"] = status
    if entity_type:
        filters["entity_type"] = entity_type
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    gen = ReportGenerator(db)
    csv_str = await gen.export_alerts_csv(tenant_id, filters)
    return PlainTextResponse(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts_export.csv"},
    )
