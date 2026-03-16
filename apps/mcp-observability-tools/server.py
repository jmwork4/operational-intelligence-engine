"""MCP Observability Tools Server — exposes system health and metrics tools.

Tools
-----
- **get_system_health** — health status of all backend services.
- **get_ingestion_stats** — ingestion rate and hourly event counts.
- **get_rule_performance** — rule evaluation timing and trigger rates.

The ``get_system_health`` tool does **not** require a tenant_id because it
reports infrastructure-level status.  The other tools are scoped to
*tenant_id* for row-level security.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.ai.mcp_base import MCPServer, ToolDefinition

logger = logging.getLogger(__name__)


class ObservabilityToolsServer(MCPServer):
    """MCP server that exposes system health and observability tools."""

    def __init__(
        self,
        db_session_factory: Any = None,
        redis_client: Any = None,
        storage_client: Any = None,
    ) -> None:
        self._db_session_factory = db_session_factory
        self._redis_client = redis_client
        self._storage_client = storage_client
        super().__init__()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tools(self) -> None:
        self.register_tool(ToolDefinition(
            name="get_system_health",
            description=(
                "Return the health status of all backend services including "
                "database, Redis, and object storage."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            handler=self._get_system_health,
        ))

        self.register_tool(ToolDefinition(
            name="get_ingestion_stats",
            description=(
                "Return ingestion rate and event counts broken down by hour "
                "for the specified time window."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look back (default 24).",
                    },
                },
                "required": ["tenant_id"],
                "additionalProperties": False,
            },
            handler=self._get_ingestion_stats,
        ))

        self.register_tool(ToolDefinition(
            name="get_rule_performance",
            description=(
                "Return rule evaluation performance metrics including average "
                "evaluation time and trigger rates."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                },
                "required": ["tenant_id"],
                "additionalProperties": False,
            },
            handler=self._get_rule_performance,
        ))

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _get_system_health(self) -> dict[str, Any]:
        """Check health of DB, Redis, and storage services."""
        health: dict[str, Any] = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "services": {},
        }

        # Database health
        try:
            if self._db_session_factory is not None:
                async with self._db_session_factory() as session:
                    await session.execute("SELECT 1")
                health["services"]["database"] = {
                    "status": "healthy",
                    "latency_ms": None,
                }
            else:
                health["services"]["database"] = {
                    "status": "not_configured",
                }
        except Exception as exc:
            health["services"]["database"] = {
                "status": "unhealthy",
                "error": str(exc),
            }

        # Redis health
        try:
            if self._redis_client is not None:
                await self._redis_client.ping()
                health["services"]["redis"] = {
                    "status": "healthy",
                }
            else:
                health["services"]["redis"] = {
                    "status": "not_configured",
                }
        except Exception as exc:
            health["services"]["redis"] = {
                "status": "unhealthy",
                "error": str(exc),
            }

        # Storage health
        try:
            if self._storage_client is not None:
                await self._storage_client.health_check()
                health["services"]["storage"] = {
                    "status": "healthy",
                }
            else:
                health["services"]["storage"] = {
                    "status": "not_configured",
                }
        except Exception as exc:
            health["services"]["storage"] = {
                "status": "unhealthy",
                "error": str(exc),
            }

        # Overall status
        statuses = [
            svc["status"] for svc in health["services"].values()
        ]
        if all(s == "healthy" for s in statuses):
            health["overall"] = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            health["overall"] = "degraded"
        else:
            health["overall"] = "unknown"

        return health

    async def _get_ingestion_stats(
        self,
        tenant_id: str,
        hours: int = 24,
    ) -> dict[str, Any]:
        """Return ingestion rate and event counts by hour."""
        hours = min(int(hours), 168)  # Cap at 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with self._get_readonly_session() as session:
            # Hourly event counts
            hourly_query = (
                "SELECT date_trunc('hour', created_at) as hour, "
                "COUNT(*) as count "
                "FROM events "
                "WHERE tenant_id = :tenant_id AND created_at >= :cutoff "
                "GROUP BY hour ORDER BY hour ASC"
            )
            params = {"tenant_id": tenant_id, "cutoff": cutoff}

            rows = await session.execute(hourly_query, params)
            hourly = [
                {"hour": row["hour"].isoformat(), "count": row["count"]}
                for row in rows
            ]

            # Total and rate
            total_query = (
                "SELECT COUNT(*) as total FROM events "
                "WHERE tenant_id = :tenant_id AND created_at >= :cutoff"
            )
            total_rows = await session.execute(total_query, params)
            total_list = [dict(row) for row in total_rows]
            total = total_list[0]["total"] if total_list else 0

            events_per_hour = round(total / max(hours, 1), 2)

            return {
                "tenant_id": tenant_id,
                "hours": hours,
                "total_events": total,
                "events_per_hour": events_per_hour,
                "hourly_breakdown": hourly,
            }

    async def _get_rule_performance(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Return rule evaluation stats: average eval time and trigger rates."""
        async with self._get_readonly_session() as session:
            query = (
                "SELECT r.id as rule_id, r.name as rule_name, "
                "COUNT(re.id) as total_evaluations, "
                "SUM(CASE WHEN re.matched THEN 1 ELSE 0 END) as total_matches, "
                "AVG(re.execution_time_ms) as avg_execution_time_ms, "
                "MAX(re.evaluated_at) as last_evaluated_at "
                "FROM rules r "
                "LEFT JOIN rule_evaluations re "
                "  ON r.id = re.rule_id AND re.tenant_id = :tenant_id "
                "WHERE r.tenant_id = :tenant_id AND r.enabled = true "
                "GROUP BY r.id, r.name "
                "ORDER BY total_evaluations DESC"
            )
            params = {"tenant_id": tenant_id}

            rows = await session.execute(query, params)
            rules = []
            total_evals = 0
            total_matches = 0
            total_time = 0.0
            count_with_time = 0

            for row in rows:
                row_dict = dict(row)
                evals = row_dict.get("total_evaluations", 0)
                matches = row_dict.get("total_matches", 0)
                avg_time = row_dict.get("avg_execution_time_ms", 0.0)

                trigger_rate = round(
                    (matches / evals * 100) if evals > 0 else 0.0, 2
                )

                rules.append({
                    "rule_id": str(row_dict["rule_id"]),
                    "rule_name": row_dict["rule_name"],
                    "total_evaluations": evals,
                    "total_matches": matches,
                    "trigger_rate_pct": trigger_rate,
                    "avg_execution_time_ms": round(avg_time, 2) if avg_time else 0.0,
                    "last_evaluated_at": (
                        row_dict["last_evaluated_at"].isoformat()
                        if row_dict.get("last_evaluated_at")
                        else None
                    ),
                })

                total_evals += evals
                total_matches += matches
                if avg_time and evals > 0:
                    total_time += avg_time * evals
                    count_with_time += evals

            overall_avg_time = (
                round(total_time / count_with_time, 2)
                if count_with_time > 0
                else 0.0
            )
            overall_trigger_rate = (
                round(total_matches / total_evals * 100, 2)
                if total_evals > 0
                else 0.0
            )

            return {
                "tenant_id": tenant_id,
                "total_rules": len(rules),
                "total_evaluations": total_evals,
                "overall_avg_execution_time_ms": overall_avg_time,
                "overall_trigger_rate_pct": overall_trigger_rate,
                "rules": rules,
            }

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _get_readonly_session(self):
        """Return an async context manager for a read-only DB session."""
        if self._db_session_factory is None:
            raise RuntimeError(
                "ObservabilityToolsServer requires a db_session_factory. "
                "Pass one when constructing the server."
            )
        return self._db_session_factory()
