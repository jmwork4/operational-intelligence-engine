"""Tenant management routes."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import ResourceNotFoundError, TenantAccessDeniedError
from packages.db.models.tenant import Tenant
from packages.schemas import TenantCreate, TenantResponse

from apps.api.deps import RateLimiter, get_current_tenant, get_current_user, get_db

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_per_minute=10))],
)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> TenantResponse:
    """Create a new tenant. Restricted to admin users."""
    if user.get("role") != "admin":
        raise TenantAccessDeniedError("Only admin users can create tenants")

    tenant = Tenant(
        name=body.name,
        slug=body.slug,
        plan_tier=body.plan_tier,
        is_active=True,
        settings={},
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_tenant_id: UUID = Depends(get_current_tenant),
) -> TenantResponse:
    """Get tenant details. Users can only view their own tenant."""
    if tenant_id != current_tenant_id:
        raise TenantAccessDeniedError("Cannot access another tenant's details")

    stmt = sa.select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise ResourceNotFoundError("Tenant", str(tenant_id))

    return TenantResponse.model_validate(tenant)
