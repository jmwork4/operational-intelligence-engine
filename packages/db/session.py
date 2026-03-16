"""Async session management for SQLAlchemy."""

from collections.abc import AsyncGenerator
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine as _create_async_engine,
)


def create_async_engine(
    url: str,
    *,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
    echo: bool = False,
):
    """Create an async engine with sensible pool defaults."""
    return _create_async_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        echo=echo,
    )


def create_async_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Module-level defaults — initialised by the application at startup.
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(url: str, **engine_kwargs):
    """Initialise the module-level engine and session factory."""
    global _engine, _session_factory
    _engine = create_async_engine(url, **engine_kwargs)
    _session_factory = create_async_session_factory(_engine)
    return _engine


def get_async_engine():
    """Return the module-level engine (must call init_db first)."""
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_db() first.")
    return _engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async generator yielding a session — suitable for FastAPI Depends()."""
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def execute_with_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """Set the current tenant context via a PostgreSQL session variable.

    This is used alongside Row-Level Security policies so that every
    subsequent query in the session is automatically scoped to the tenant.
    """
    await session.execute(
        sa.text("SET app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
