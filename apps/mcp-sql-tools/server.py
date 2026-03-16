"""MCP SQL Tools Server — exposes database query tools to the AI copilot.

Tools
-----
- **query_events** — query the events table with flexible filters.
- **query_alerts** — query alerts with severity/status/entity filters.
- **get_event_stats** — aggregate event counts by type for a time range.
- **get_entity_history** — return the event timeline for a specific entity.

All queries use read-only database sessions and are scoped to *tenant_id*
for row-level security.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from packages.ai.mcp_base import MCPServer, ToolDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_time_range(time_range: str) -> datetime:
    """Convert a human-friendly time range string to a UTC cutoff datetime.

    Supported formats: ``"1h"``, ``"24h"``, ``"7d"``, ``"30d"``.
    """
    unit = time_range[-1]
    value = int(time_range[:-1])
    now = datetime.now(timezone.utc)
    if unit == "h":
        return now - timedelta(hours=value)
    if unit == "d":
        return now - timedelta(days=value)
    raise ValueError(f"Unsupported time_range format: {time_range!r}")


# ---------------------------------------------------------------------------
# SQL Tools MCP Server
# ---------------------------------------------------------------------------

class SQLToolsServer(MCPServer):
    """MCP server that exposes SQL query tools for events and alerts."""

    def __init__(self, db_session_factory: Any = None) -> None:
        self._db_session_factory = db_session_factory
        super().__init__()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tools(self) -> None:
        self.register_tool(ToolDefinition(
            name="query_events",
            description=(
                "Query the events table with optional filters. Returns a list "
                "of event records matching the criteria."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters for the query.",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Filter by event type.",
                            },
                            "entity_id": {
                                "type": "string",
                                "description": "Filter by entity ID.",
                            },
                            "date_range": {
                                "type": "string",
                                "description": "Time range such as '1h', '24h', '7d', '30d'.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default 100).",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["tenant_id"],
                "additionalProperties": False,
            },
            handler=self._query_events,
        ))

        self.register_tool(ToolDefinition(
            name="query_alerts",
            description=(
                "Query alerts with optional severity, status, and entity filters."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters for the query.",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "description": "Filter by alert severity.",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["open", "acknowledged", "resolved"],
                                "description": "Filter by alert status.",
                            },
                            "entity_id": {
                                "type": "string",
                                "description": "Filter by related entity ID.",
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["tenant_id"],
                "additionalProperties": False,
            },
            handler=self._query_alerts,
        ))

        self.register_tool(ToolDefinition(
            name="get_event_stats",
            description=(
                "Return aggregate event counts grouped by event type for a "
                "given time range."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "time_range": {
                        "type": "string",
                        "description": "Time range such as '1h', '24h', '7d', '30d'.",
                    },
                },
                "required": ["tenant_id", "time_range"],
                "additionalProperties": False,
            },
            handler=self._get_event_stats,
        ))

        self.register_tool(ToolDefinition(
            name="get_entity_history",
            description=(
                "Return the full event timeline for a specific entity, "
                "ordered chronologically."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Type of entity (e.g. 'user', 'device', 'service').",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Unique identifier for the entity.",
                    },
                },
                "required": ["tenant_id", "entity_type", "entity_id"],
                "additionalProperties": False,
            },
            handler=self._get_entity_history,
        ))

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _query_events(
        self,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query events table with optional filters."""
        filters = filters or {}
        limit = min(int(filters.get("limit", 100)), 1000)

        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, event_type, entity_id, payload, created_at "
                "FROM events WHERE tenant_id = :tenant_id"
            )
            params: dict[str, Any] = {"tenant_id": tenant_id}

            if filters.get("event_type"):
                query += " AND event_type = :event_type"
                params["event_type"] = filters["event_type"]

            if filters.get("entity_id"):
                query += " AND entity_id = :entity_id"
                params["entity_id"] = filters["entity_id"]

            if filters.get("date_range"):
                cutoff = _parse_time_range(filters["date_range"])
                query += " AND created_at >= :cutoff"
                params["cutoff"] = cutoff

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    async def _query_alerts(
        self,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query alerts with optional severity/status/entity filters."""
        filters = filters or {}

        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, severity, status, entity_id, rule_id, message, "
                "created_at, acknowledged_at, resolved_at "
                "FROM alerts WHERE tenant_id = :tenant_id"
            )
            params: dict[str, Any] = {"tenant_id": tenant_id}

            if filters.get("severity"):
                query += " AND severity = :severity"
                params["severity"] = filters["severity"]

            if filters.get("status"):
                query += " AND status = :status"
                params["status"] = filters["status"]

            if filters.get("entity_id"):
                query += " AND entity_id = :entity_id"
                params["entity_id"] = filters["entity_id"]

            query += " ORDER BY created_at DESC LIMIT 200"

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    async def _get_event_stats(
        self,
        tenant_id: str,
        time_range: str,
    ) -> dict[str, Any]:
        """Return event counts grouped by event type for the time range."""
        cutoff = _parse_time_range(time_range)

        async with self._get_readonly_session() as session:
            query = (
                "SELECT event_type, COUNT(*) as count "
                "FROM events "
                "WHERE tenant_id = :tenant_id AND created_at >= :cutoff "
                "GROUP BY event_type ORDER BY count DESC"
            )
            params = {"tenant_id": tenant_id, "cutoff": cutoff}

            rows = await session.execute(query, params)
            by_type = {row["event_type"]: row["count"] for row in rows}
            total = sum(by_type.values())

            return {
                "tenant_id": tenant_id,
                "time_range": time_range,
                "total_events": total,
                "by_type": by_type,
            }

    async def _get_entity_history(
        self,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Return the event timeline for a specific entity."""
        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, event_type, payload, created_at "
                "FROM events "
                "WHERE tenant_id = :tenant_id "
                "  AND entity_type = :entity_type "
                "  AND entity_id = :entity_id "
                "ORDER BY created_at ASC"
            )
            params = {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _get_readonly_session(self):
        """Return an async context manager for a read-only DB session.

        If no session factory was provided at construction time a
        ``RuntimeError`` is raised with a descriptive message.
        """
        if self._db_session_factory is None:
            raise RuntimeError(
                "SQLToolsServer requires a db_session_factory. "
                "Pass one when constructing the server."
            )
        return self._db_session_factory()
