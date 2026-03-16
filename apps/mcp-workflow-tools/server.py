"""MCP Workflow Tools Server — exposes rule and alert management tools.

Tools
-----
- **list_active_rules** — return all enabled rules for a tenant.
- **get_rule_details** — return a single rule with its evaluation history.
- **get_alert_summary** — return alert counts by severity and status.

All queries are scoped to *tenant_id* for row-level security.
"""

from __future__ import annotations

import logging
from typing import Any

from packages.ai.mcp_base import MCPServer, ToolDefinition

logger = logging.getLogger(__name__)


class WorkflowToolsServer(MCPServer):
    """MCP server that exposes workflow and rule management tools."""

    def __init__(self, db_session_factory: Any = None) -> None:
        self._db_session_factory = db_session_factory
        super().__init__()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tools(self) -> None:
        self.register_tool(ToolDefinition(
            name="list_active_rules",
            description=(
                "Return all enabled automation rules for the tenant."
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
            handler=self._list_active_rules,
        ))

        self.register_tool(ToolDefinition(
            name="get_rule_details",
            description=(
                "Return a single rule along with its recent evaluation "
                "history."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "rule_id": {
                        "type": "string",
                        "description": "UUID of the rule to retrieve.",
                    },
                },
                "required": ["tenant_id", "rule_id"],
                "additionalProperties": False,
            },
            handler=self._get_rule_details,
        ))

        self.register_tool(ToolDefinition(
            name="get_alert_summary",
            description=(
                "Return aggregate alert counts grouped by severity and "
                "status for the tenant."
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
            handler=self._get_alert_summary,
        ))

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _list_active_rules(
        self,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Return all enabled rules for the tenant."""
        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, name, description, rule_type, conditions, "
                "actions, enabled, created_at, updated_at "
                "FROM rules "
                "WHERE tenant_id = :tenant_id AND enabled = true "
                "ORDER BY name ASC"
            )
            params = {"tenant_id": tenant_id}

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    async def _get_rule_details(
        self,
        tenant_id: str,
        rule_id: str,
    ) -> dict[str, Any]:
        """Return a rule with its recent evaluation history."""
        async with self._get_readonly_session() as session:
            # Fetch the rule itself.
            rule_query = (
                "SELECT id, name, description, rule_type, conditions, "
                "actions, enabled, created_at, updated_at "
                "FROM rules "
                "WHERE tenant_id = :tenant_id AND id = :rule_id"
            )
            rule_params = {"tenant_id": tenant_id, "rule_id": rule_id}

            rows = await session.execute(rule_query, rule_params)
            rule_rows = [dict(row) for row in rows]
            if not rule_rows:
                return {"error": f"Rule {rule_id!r} not found."}

            rule = rule_rows[0]

            # Fetch recent evaluation history.
            history_query = (
                "SELECT id, evaluated_at, matched, execution_time_ms, "
                "error_message "
                "FROM rule_evaluations "
                "WHERE tenant_id = :tenant_id AND rule_id = :rule_id "
                "ORDER BY evaluated_at DESC LIMIT 50"
            )

            history_rows = await session.execute(history_query, rule_params)
            rule["evaluation_history"] = [dict(row) for row in history_rows]

            return rule

    async def _get_alert_summary(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Return alert counts grouped by severity and status."""
        async with self._get_readonly_session() as session:
            severity_query = (
                "SELECT severity, COUNT(*) as count "
                "FROM alerts WHERE tenant_id = :tenant_id "
                "GROUP BY severity"
            )
            status_query = (
                "SELECT status, COUNT(*) as count "
                "FROM alerts WHERE tenant_id = :tenant_id "
                "GROUP BY status"
            )
            params = {"tenant_id": tenant_id}

            severity_rows = await session.execute(severity_query, params)
            by_severity = {row["severity"]: row["count"] for row in severity_rows}

            status_rows = await session.execute(status_query, params)
            by_status = {row["status"]: row["count"] for row in status_rows}

            total = sum(by_severity.values())

            return {
                "tenant_id": tenant_id,
                "total_alerts": total,
                "by_severity": by_severity,
                "by_status": by_status,
            }

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _get_readonly_session(self):
        """Return an async context manager for a read-only DB session."""
        if self._db_session_factory is None:
            raise RuntimeError(
                "WorkflowToolsServer requires a db_session_factory. "
                "Pass one when constructing the server."
            )
        return self._db_session_factory()
