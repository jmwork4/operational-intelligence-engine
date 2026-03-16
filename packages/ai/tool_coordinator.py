"""Tool Coordinator — manages MCP tool execution during AI requests.

Aggregates tool definitions from registered MCP servers and executes tool
calls in parallel with per-call timeouts and structured error handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default per-tool-call timeout in seconds.
_DEFAULT_TIMEOUT: float = 5.0


class ToolCoordinator:
    """Orchestrates tool execution across multiple MCP servers.

    Parameters
    ----------
    servers:
        List of :class:`MCPServer` instances whose tools should be available.
    default_timeout:
        Default timeout (in seconds) applied to each individual tool call.
    """

    def __init__(
        self,
        servers: list[Any] | None = None,
        default_timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._servers: dict[str, Any] = {}
        self._default_timeout = default_timeout

        for server in servers or []:
            self._servers[server.name] = server

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_tools(
        self,
        tool_calls: list[dict[str, Any]],
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute *tool_calls* in parallel and return structured results.

        Each element of *tool_calls* must be a dict with keys:
        ``server``, ``tool``, ``arguments``.

        Returns a list of result dicts, one per call, each containing:
        ``tool``, ``success``, ``result``, ``error``, ``latency_ms``.
        """
        effective_timeout = timeout or self._default_timeout

        tasks = [
            self._execute_single_tool(
                server_name=tc["server"],
                tool_name=tc["tool"],
                arguments=tc.get("arguments", {}),
                timeout=effective_timeout,
            )
            for tc in tool_calls
        ]

        results = await asyncio.gather(*tasks)
        return list(results)

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Aggregate tool definitions from all registered MCP servers.

        Returns a list of tool-definition dicts suitable for passing to
        the Anthropic API ``tools`` parameter.
        """
        tools: list[dict[str, Any]] = []

        for server_name, server in self._servers.items():
            try:
                server_tools = server.list_tools()
            except Exception:
                logger.warning(
                    "Failed to list tools from server %s", server_name, exc_info=True
                )
                continue

            for tool_def in server_tools:
                # MCPServer.list_tools() returns ToolDefinition dataclasses.
                # Convert to the Anthropic tool-use format.
                tools.append(
                    {
                        "name": f"{server_name}__{tool_def.name}",
                        "description": tool_def.description or "",
                        "input_schema": tool_def.input_schema
                        if hasattr(tool_def, "input_schema") and tool_def.input_schema
                        else {"type": "object", "properties": {}},
                    }
                )

        return tools

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_single_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        """Execute a single tool call with timeout and error handling.

        Returns a structured result dict regardless of success or failure.
        """
        start = time.monotonic()

        # Locate the server.
        server = self._servers.get(server_name)
        if server is None:
            elapsed_ms = (time.monotonic() - start) * 1000
            return {
                "tool": f"{server_name}.{tool_name}",
                "success": False,
                "result": None,
                "error": f"MCP server '{server_name}' not found. "
                f"Available servers: {list(self._servers.keys())}",
                "latency_ms": round(elapsed_ms, 2),
            }

        try:
            raw_result = await asyncio.wait_for(
                server.call_tool(tool_name, arguments),
                timeout=timeout,
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            # ToolResult dataclass -> dict
            result_dict: dict[str, Any] | None = None
            if raw_result is not None:
                if hasattr(raw_result, "__dict__"):
                    result_dict = {
                        k: v
                        for k, v in raw_result.__dict__.items()
                        if not k.startswith("_")
                    }
                elif isinstance(raw_result, dict):
                    result_dict = raw_result
                else:
                    result_dict = {"value": raw_result}

            logger.debug(
                "Tool %s.%s completed in %.1fms",
                server_name,
                tool_name,
                elapsed_ms,
            )

            return {
                "tool": f"{server_name}.{tool_name}",
                "success": True,
                "result": result_dict,
                "error": None,
                "latency_ms": round(elapsed_ms, 2),
            }

        except asyncio.TimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.warning(
                "Tool %s.%s timed out after %.1fs",
                server_name,
                tool_name,
                timeout,
            )
            return {
                "tool": f"{server_name}.{tool_name}",
                "success": False,
                "result": None,
                "error": f"Tool execution timed out after {timeout}s",
                "latency_ms": round(elapsed_ms, 2),
            }

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error(
                "Tool %s.%s failed: %s",
                server_name,
                tool_name,
                exc,
                exc_info=True,
            )
            return {
                "tool": f"{server_name}.{tool_name}",
                "success": False,
                "result": None,
                "error": f"{type(exc).__name__}: {exc}",
                "latency_ms": round(elapsed_ms, 2),
            }
