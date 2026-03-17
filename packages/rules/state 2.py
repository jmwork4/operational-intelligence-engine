"""Composite rule state management — Redis for short windows, PostgreSQL for long."""

from __future__ import annotations

import json
from uuid import UUID

import redis.asyncio as aioredis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _redis_key(rule_id: UUID, tenant_id: UUID) -> str:
    """Build the Redis key for composite rule state."""
    return f"oie:rule_state:{tenant_id}:{rule_id}"


def _pg_table_name() -> str:
    return "rule_state"


class RuleStateManager:
    """Manages composite rule state across Redis and PostgreSQL.

    Storage strategy based on evaluation window:
    - window < 3600s (1 hour): Redis only with TTL
    - 3600s <= window < 86400s (1 day): Redis + checkpoint to PostgreSQL
    - window >= 86400s (1 day): PostgreSQL only

    Args:
        session: An async SQLAlchemy session for PostgreSQL operations.
        redis_url: Redis connection URL.
    """

    def __init__(self, session: AsyncSession, redis_url: str) -> None:
        self._session = session
        self._redis_url = redis_url

    async def _get_redis(self) -> aioredis.Redis:
        return aioredis.from_url(self._redis_url, decode_responses=True)

    # -----------------------------------------------------------------
    # Read state
    # -----------------------------------------------------------------

    async def get_state(self, rule_id: UUID, tenant_id: UUID) -> dict:
        """Load composite rule state.

        Tries Redis first, falls back to PostgreSQL if not found.

        Returns:
            A dict of state data, or an empty dict if no state exists.
        """
        # Try Redis first
        try:
            r = await self._get_redis()
            async with r:
                raw = await r.get(_redis_key(rule_id, tenant_id))
                if raw is not None:
                    return json.loads(raw)
        except Exception:
            logger.debug("redis_state_read_failed", rule_id=str(rule_id))

        # Fall back to PostgreSQL
        try:
            stmt = sa.text(
                f"SELECT state_data FROM {_pg_table_name()} "
                "WHERE rule_id = :rule_id AND tenant_id = :tenant_id"
            )
            result = await self._session.execute(
                stmt, {"rule_id": str(rule_id), "tenant_id": str(tenant_id)}
            )
            row = result.first()
            if row is not None:
                data = row[0]
                return json.loads(data) if isinstance(data, str) else data
        except Exception:
            logger.debug("pg_state_read_failed", rule_id=str(rule_id))

        return {}

    # -----------------------------------------------------------------
    # Write state
    # -----------------------------------------------------------------

    async def update_state(
        self,
        rule_id: UUID,
        tenant_id: UUID,
        state: dict,
        window_seconds: int,
    ) -> None:
        """Persist composite rule state using the appropriate storage tier.

        Args:
            rule_id: The rule this state belongs to.
            tenant_id: Owning tenant.
            state: Arbitrary state dict to persist.
            window_seconds: The rule's evaluation window; determines storage
                strategy.
        """
        serialised = json.dumps(state, default=str)

        if window_seconds < 3600:
            # Short window — Redis only with TTL
            await self._write_redis(rule_id, tenant_id, serialised, ttl=window_seconds)

        elif window_seconds < 86400:
            # Medium window — Redis + PostgreSQL checkpoint
            await self._write_redis(rule_id, tenant_id, serialised, ttl=window_seconds)
            await self._write_pg(rule_id, tenant_id, serialised)

        else:
            # Long window — PostgreSQL only
            await self._write_pg(rule_id, tenant_id, serialised)

    async def _write_redis(
        self, rule_id: UUID, tenant_id: UUID, data: str, ttl: int
    ) -> None:
        try:
            r = await self._get_redis()
            async with r:
                key = _redis_key(rule_id, tenant_id)
                await r.set(key, data, ex=max(ttl, 1))
        except Exception:
            logger.warning(
                "redis_state_write_failed",
                rule_id=str(rule_id),
                tenant_id=str(tenant_id),
            )

    async def _write_pg(
        self, rule_id: UUID, tenant_id: UUID, data: str
    ) -> None:
        try:
            stmt = sa.text(
                f"INSERT INTO {_pg_table_name()} (rule_id, tenant_id, state_data, updated_at) "
                "VALUES (:rule_id, :tenant_id, :state_data, NOW()) "
                "ON CONFLICT (rule_id, tenant_id) DO UPDATE "
                "SET state_data = :state_data, updated_at = NOW()"
            )
            await self._session.execute(
                stmt,
                {
                    "rule_id": str(rule_id),
                    "tenant_id": str(tenant_id),
                    "state_data": data,
                },
            )
            await self._session.commit()
        except Exception:
            logger.warning(
                "pg_state_write_failed",
                rule_id=str(rule_id),
                tenant_id=str(tenant_id),
            )

    # -----------------------------------------------------------------
    # Clear state
    # -----------------------------------------------------------------

    async def clear_state(self, rule_id: UUID, tenant_id: UUID) -> None:
        """Remove state for a rule from both Redis and PostgreSQL."""
        # Clear Redis
        try:
            r = await self._get_redis()
            async with r:
                await r.delete(_redis_key(rule_id, tenant_id))
        except Exception:
            logger.debug("redis_state_clear_failed", rule_id=str(rule_id))

        # Clear PostgreSQL
        try:
            stmt = sa.text(
                f"DELETE FROM {_pg_table_name()} "
                "WHERE rule_id = :rule_id AND tenant_id = :tenant_id"
            )
            await self._session.execute(
                stmt, {"rule_id": str(rule_id), "tenant_id": str(tenant_id)}
            )
            await self._session.commit()
        except Exception:
            logger.debug("pg_state_clear_failed", rule_id=str(rule_id))
