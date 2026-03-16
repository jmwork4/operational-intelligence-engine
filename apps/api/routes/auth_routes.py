"""Auth routes — login and registration."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import ResourceNotFoundError, ValidationError
from packages.db.models.user import User
from packages.schemas import TokenResponse, UserCreate, UserResponse

from apps.api.auth import create_access_token, hash_password, verify_password
from apps.api.deps import get_current_tenant, get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


class _LoginRequest:
    """Simple container parsed from JSON body (not a Pydantic schema so we
    keep the schemas package free of auth-specific request types)."""

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password


# We use a plain Pydantic model inline since the schemas package doesn't
# expose a LoginRequest.
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password, receive a JWT."""
    stmt = sa.select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise ValidationError("Invalid email or password")

    if not user.is_active:
        raise ValidationError("User account is deactivated")

    # Update last_login timestamp.
    user.last_login = datetime.now(UTC)
    await db.commit()

    token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "role": user.role,
        }
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant),
) -> UserResponse:
    """Register a new user within the current tenant.

    Requires an existing JWT (i.e. an admin or existing user must invite
    the new user).
    """
    # Check for duplicate email within this tenant.
    exists_stmt = sa.select(User).where(
        User.email == body.email, User.tenant_id == tenant_id
    )
    exists_result = await db.execute(exists_stmt)
    if exists_result.scalar_one_or_none() is not None:
        raise ValidationError(f"A user with email {body.email} already exists in this tenant")

    user = User(
        tenant_id=tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
