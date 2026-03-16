"""Redis stream operations for event data."""

from __future__ import annotations

import json
from uuid import UUID

import redis.asyncio as aioredis

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _stream_key(tenant_id: UUID) -> str:
    """Build the Redis stream key for a tenant's events."""
    return f"oie:events:{tenant_id}"


class EventStream:
    """Manages Redis stream operations for event data.

    Args:
        redis_url: Redis connection URL (e.g. ``redis://localhost:6379/0``).
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url

    async def _get_redis(self) -> aioredis.Redis:
        return aioredis.from_url(self._redis_url, decode_responses=True)

    async def append(self, tenant_id: UUID, event_data: dict) -> str:
        """Append an event to the tenant's Redis stream.

        Args:
            tenant_id: The tenant that owns the event.
            event_data: Event data dict to store in the stream.

        Returns:
            The Redis stream message ID (e.g. ``"1234567890-0"``).
        """
        r = await self._get_redis()
        async with r:
            key = _stream_key(tenant_id)
            # Serialise the event data as a single JSON field so that
            # nested structures are preserved.
            stream_data = {"data": json.dumps(event_data, default=str)}
            message_id: str = await r.xadd(key, stream_data)  # type: ignore[assignment]
            logger.debug(
                "event_stream_append",
                tenant_id=str(tenant_id),
                message_id=message_id,
            )
            return message_id

    async def read_latest(
        self, tenant_id: UUID, count: int = 10
    ) -> list[dict]:
        """Read the most recent events from the tenant's stream.

        Args:
            tenant_id: The tenant whose stream to read.
            count: Maximum number of messages to return.

        Returns:
            A list of event data dicts, most recent first.
        """
        r = await self._get_redis()
        async with r:
            key = _stream_key(tenant_id)
            # XREVRANGE returns newest first
            messages = await r.xrevrange(key, count=count)
            return [self._parse_message(msg) for msg in messages]

    async def read_range(
        self, tenant_id: UUID, start: str, end: str
    ) -> list[dict]:
        """Read events within a stream ID range.

        Args:
            tenant_id: The tenant whose stream to read.
            start: Start stream ID (inclusive), e.g. ``"1234567890-0"`` or ``"-"``.
            end: End stream ID (inclusive), e.g. ``"1234567899-0"`` or ``"+"``.

        Returns:
            A list of event data dicts in chronological order.
        """
        r = await self._get_redis()
        async with r:
            key = _stream_key(tenant_id)
            messages = await r.xrange(key, min=start, max=end)
            return [self._parse_message(msg) for msg in messages]

    @staticmethod
    def _parse_message(message: tuple) -> dict:
        """Parse a Redis stream message tuple into a dict."""
        message_id, fields = message
        raw = fields.get("data", "{}")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            data = {"raw": raw}
        data["_stream_id"] = message_id
        return data
