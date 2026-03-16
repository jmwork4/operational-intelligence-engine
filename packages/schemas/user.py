"""User and authentication schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=255, description="User full name"
    )
    role: str = Field(default="member", description="User role within the tenant")


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: EmailStr | None = Field(default=None)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserResponse(BaseModel):
    """Schema returned when reading a user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime


class TokenResponse(BaseModel):
    """Schema returned after successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
