"""Rule routes — CRUD for alerting / automation rules."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import ResourceNotFoundError
from packages.db.models.rule import Rule
from packages.schemas import PaginatedResponse, RuleCreate, RuleResponse, RuleUpdate

from apps.api.deps import RateLimiter, get_current_tenant, get_db

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.post(
    "/",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> RuleResponse:
    """Create a new alerting rule."""
    rule = Rule(
        tenant_id=tenant_id,
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        trigger_event=body.trigger_event,
        condition_expression=body.condition_expression,
        evaluation_window=body.evaluation_window,
        severity=body.severity,
        action_type=body.action_type,
        enabled=body.enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.get(
    "/",
    response_model=PaginatedResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def list_rules(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PaginatedResponse:
    """List all rules for the current tenant."""
    count_stmt = (
        sa.select(sa.func.count())
        .select_from(Rule)
        .where(Rule.tenant_id == tenant_id)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        sa.select(Rule)
        .where(Rule.tenant_id == tenant_id)
        .order_by(Rule.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return PaginatedResponse(
        items=[RuleResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> RuleResponse:
    """Get a single rule by ID."""
    stmt = sa.select(Rule).where(Rule.id == rule_id, Rule.tenant_id == tenant_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise ResourceNotFoundError("Rule", str(rule_id))

    return RuleResponse.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=RuleResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def update_rule(
    rule_id: UUID,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> RuleResponse:
    """Update an existing rule (partial update)."""
    stmt = sa.select(Rule).where(Rule.id == rule_id, Rule.tenant_id == tenant_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise ResourceNotFoundError("Rule", str(rule_id))

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> None:
    """Soft-delete a rule by setting ``enabled=False``."""
    stmt = sa.select(Rule).where(Rule.id == rule_id, Rule.tenant_id == tenant_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()

    if rule is None:
        raise ResourceNotFoundError("Rule", str(rule_id))

    rule.enabled = False
    await db.commit()
