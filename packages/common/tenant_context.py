from __future__ import annotations

import contextvars
from contextlib import contextmanager
from uuid import UUID

_current_tenant_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


class TenantContext:
    @staticmethod
    def set_tenant(tenant_id: UUID) -> contextvars.Token[UUID | None]:
        return _current_tenant_id.set(tenant_id)

    @staticmethod
    def get_tenant() -> UUID:
        tenant_id = _current_tenant_id.get()
        if tenant_id is None:
            raise RuntimeError("No tenant set in current context")
        return tenant_id

    @staticmethod
    def get_tenant_or_none() -> UUID | None:
        return _current_tenant_id.get()

    @staticmethod
    def clear_tenant() -> None:
        _current_tenant_id.set(None)

    @staticmethod
    def rls_set_statement(tenant_id: UUID) -> str:
        return f"SET app.current_tenant_id = '{tenant_id}'"

    @staticmethod
    @contextmanager
    def scoped(tenant_id: UUID):
        token = TenantContext.set_tenant(tenant_id)
        try:
            yield
        finally:
            _current_tenant_id.reset(token)
