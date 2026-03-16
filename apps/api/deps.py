"""FastAPI dependency injection helpers."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import (
    RateLimitExceededError,
    TenantAccessDeniedError,
    TenantContext,
    get_settings,
)
from packages.db.session import execute_with_tenant, get_async_session
from packages.storage import StorageAdapter, get_storage_adapter

from apps.api.auth import verify_token

_bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session scoped to a single request."""
    async for session in get_async_session():
        yield session


# ---------------------------------------------------------------------------
# Current tenant
# ---------------------------------------------------------------------------

async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Extract ``tenant_id`` from the JWT and set RLS context on the session.

    Returns the tenant UUID so downstream dependencies can use it directly.
    """
    try:
        payload = verify_token(credentials.credentials)
    except Exception as exc:
        raise TenantAccessDeniedError("Invalid or expired token") from exc

    raw_tenant = payload.get("tenant_id")
    if raw_tenant is None:
        raise TenantAccessDeniedError("Token does not contain tenant_id")

    tenant_id = UUID(str(raw_tenant))
    TenantContext.set_tenant(tenant_id)
    await execute_with_tenant(db, tenant_id)
    return tenant_id


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Decode the JWT and return a user info dict.

    The dict contains at minimum ``user_id``, ``tenant_id``, ``email``, and
    ``role`` as extracted from the token claims.
    """
    try:
        payload = verify_token(credentials.credentials)
    except Exception as exc:
        raise TenantAccessDeniedError("Invalid or expired token") from exc

    return {
        "user_id": payload.get("sub"),
        "tenant_id": payload.get("tenant_id"),
        "email": payload.get("email"),
        "role": payload.get("role"),
    }


# ---------------------------------------------------------------------------
# Object storage
# ---------------------------------------------------------------------------

async def get_storage() -> StorageAdapter:
    """Return a configured :class:`StorageAdapter` instance."""
    settings = get_settings()
    return get_storage_adapter(
        provider="minio",
        endpoint_url=settings.S3_ENDPOINT_URL,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        region=settings.S3_REGION,
    )


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Dependency that enforces per-tenant, per-endpoint rate limits via Redis.

    Usage::

        @router.get("/", dependencies=[Depends(RateLimiter(requests_per_minute=60))])
        async def list_items(...): ...
    """

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute

    async def __call__(
        self,
        request: Request,
        tenant_id: UUID = Depends(get_current_tenant),
    ) -> None:
        """Check the Redis counter for the current tenant + endpoint + minute bucket.

        Raises :class:`RateLimitExceededError` when the limit is breached.
        """
        settings = get_settings()
        minute_bucket = int(time.time()) // 60
        endpoint = request.url.path
        key = f"rate_limit:{tenant_id}:{endpoint}:{minute_bucket}"

        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            async with r:
                current = await r.incr(key)
                if current == 1:
                    await r.expire(key, 60)

                if current > self.requests_per_minute:
                    raise RateLimitExceededError(
                        f"Rate limit of {self.requests_per_minute} requests/minute exceeded"
                    )
        except RateLimitExceededError:
            raise
        except Exception:
            # If Redis is unavailable, allow the request through rather than
            # blocking all traffic.
            pass
