"""Tenant middleware — sets TenantContext from the JWT on every request."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, MutableMapping
from uuid import UUID

from packages.common import TenantContext

from apps.api.auth import verify_token

Scope = MutableMapping[str, Any]
Receive = Callable[..., Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Paths that do not require authentication or tenant context.
_AUTH_FREE_PATHS: set[str] = {
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
}

_AUTH_FREE_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/",
)


def _is_auth_free(path: str) -> bool:
    if path in _AUTH_FREE_PATHS:
        return True
    for prefix in _AUTH_FREE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class TenantMiddleware:
    """ASGI middleware that extracts ``tenant_id`` from the JWT bearer token
    and sets :class:`TenantContext` for the request scope.

    Auth-free paths (health check, login, docs) are skipped.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if _is_auth_free(path):
            await self.app(scope, receive, send)
            return

        # Attempt to extract tenant_id from the Authorization header.
        headers = dict(scope.get("headers", []))
        auth_header: bytes | None = headers.get(b"authorization")

        if auth_header is not None:
            try:
                token = auth_header.decode("latin-1").removeprefix("Bearer ").strip()
                payload = verify_token(token)
                raw_tenant = payload.get("tenant_id")
                if raw_tenant is not None:
                    tenant_id = UUID(str(raw_tenant))
                    TenantContext.set_tenant(tenant_id)
            except Exception:
                # If the token is invalid the downstream dependency (get_current_tenant)
                # will raise the proper 403.  The middleware is best-effort.
                pass

        try:
            await self.app(scope, receive, send)
        finally:
            TenantContext.clear_tenant()
