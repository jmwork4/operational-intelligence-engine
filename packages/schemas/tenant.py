"""Tenant schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly tenant identifier",
    )
    plan_tier: str = Field(default="basic", description="Subscription plan tier")


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan_tier: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    settings: dict | None = Field(default=None)


class TenantResponse(BaseModel):
    """Schema returned when reading a tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan_tier: str
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime
