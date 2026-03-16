"""Alert routes — query and manage alerts."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import AlertStatus, ResourceNotFoundError, utc_now
from packages.db.models.alert import Alert
from packages.domain.alert_service import AlertService
from packages.schemas import AlertAcknowledge, AlertResponse, PaginatedResponse

from apps.api.deps import RateLimiter, get_current_tenant, get_current_user, get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "/",
    response_model=PaginatedResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def list_alerts(
    severity: str | None = Query(default=None),
    alert_status: str | None = Query(default=None, alias="status"),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    rule_id: UUID | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PaginatedResponse:
    """List alerts with optional filters."""
    stmt = sa.select(Alert).where(Alert.tenant_id == tenant_id)
    count_stmt = (
        sa.select(sa.func.count())
        .select_from(Alert)
        .where(Alert.tenant_id == tenant_id)
    )

    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
        count_stmt = count_stmt.where(Alert.severity == severity)
    if alert_status is not None:
        stmt = stmt.where(Alert.status == alert_status)
        count_stmt = count_stmt.where(Alert.status == alert_status)
    if entity_type is not None:
        stmt = stmt.where(Alert.entity_type == entity_type)
        count_stmt = count_stmt.where(Alert.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Alert.entity_id == entity_id)
        count_stmt = count_stmt.where(Alert.entity_id == entity_id)
    if rule_id is not None:
        stmt = stmt.where(Alert.rule_id == rule_id)
        count_stmt = count_stmt.where(Alert.rule_id == rule_id)
    if from_date is not None:
        stmt = stmt.where(Alert.created_at >= from_date)
        count_stmt = count_stmt.where(Alert.created_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Alert.created_at <= to_date)
        count_stmt = count_stmt.where(Alert.created_at <= to_date)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return PaginatedResponse(
        items=[AlertResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> AlertResponse:
    """Get a single alert by ID."""
    stmt = sa.select(Alert).where(Alert.id == alert_id, Alert.tenant_id == tenant_id)
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if alert is None:
        raise ResourceNotFoundError("Alert", str(alert_id))

    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
) -> AlertResponse:
    """Acknowledge an alert."""
    service = AlertService(db)
    alert = await service.acknowledge_alert(
        alert_id=alert_id,
        tenant_id=tenant_id,
        user_id=UUID(str(user["user_id"])),
    )
    return AlertResponse.model_validate(alert)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def resolve_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> AlertResponse:
    """Resolve an alert."""
    service = AlertService(db)
    alert = await service.resolve_alert(alert_id=alert_id, tenant_id=tenant_id)
    return AlertResponse.model_validate(alert)
