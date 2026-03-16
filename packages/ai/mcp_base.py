"""MCP Base — shared base classes for Model Context Protocol tool servers.

Provides :class:`ToolDefinition` and :class:`ToolResult` dataclasses plus an
:class:`MCPServer` abstract base that each tool server inherits.  The base
class handles tool registration, schema listing, and safe execution (all
exceptions are caught and returned as structured :class:`ToolResult` errors
so the server never crashes).
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ToolDefinition:
    """Metadata and handler for a single MCP tool."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema dict
    handler: Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class ToolResult:
    """Structured result returned by every tool invocation."""

    success: bool
    data: dict[str, Any] | list[Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# MCPServer base class
# ---------------------------------------------------------------------------

class MCPServer:
    """Base class for MCP tool servers.

    Subclasses should call :meth:`register_tool` in their ``__init__`` to
    populate the server's tool catalogue.  The AI copilot calls
    :meth:`list_tools` to discover available tools and :meth:`execute_tool`
    to invoke them.
    """

    def __init__(self) -> None:
        self.tools: dict[str, ToolDefinition] = {}
        self.register_tools()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tools(self) -> None:
        """Override in subclasses to register tools via :meth:`register_tool`."""

    def register_tool(self, definition: ToolDefinition) -> None:
        """Add a :class:`ToolDefinition` to this server's catalogue."""
        if definition.name in self.tools:
            logger.warning(
                "Tool %r is already registered — overwriting.", definition.name
            )
        self.tools[definition.name] = definition
        logger.debug("Registered MCP tool: %s", definition.name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Return JSON-serialisable tool schemas suitable for an LLM tool list."""
        return [
            {
                "name": defn.name,
                "description": defn.description,
                "parameters": defn.parameters,
            }
            for defn in self.tools.values()
        ]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        """Invoke the tool identified by *name* with the supplied *arguments*.

        This method **never raises**.  Any exception thrown by the handler is
        caught and returned inside a :class:`ToolResult` with ``success=False``
        and a descriptive ``error`` string.
        """
        defn = self.tools.get(name)
        if defn is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {name!r}. Available: {list(self.tools.keys())}",
            )

        try:
            result = await defn.handler(**arguments)
            return ToolResult(success=True, data=result)
        except Exception:
            tb = traceback.format_exc()
            logger.exception("Tool %r raised an exception", name)
            return ToolResult(
                success=False,
                error=f"Tool {name!r} failed: {tb}",
            )
