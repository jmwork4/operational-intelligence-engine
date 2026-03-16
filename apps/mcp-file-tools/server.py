"""MCP File Tools Server — exposes document search and retrieval tools.

Tools
-----
- **search_documents** — semantic search across ingested documents.
- **get_document_chunks** — retrieve all chunks for a specific document.
- **list_documents** — list documents with optional status filter.

All queries are scoped to *tenant_id* for row-level security.
"""

from __future__ import annotations

import logging
from typing import Any

from packages.ai.mcp_base import MCPServer, ToolDefinition

logger = logging.getLogger(__name__)


class FileToolsServer(MCPServer):
    """MCP server that exposes document search and retrieval tools."""

    def __init__(
        self,
        db_session_factory: Any = None,
        semantic_search_fn: Any = None,
    ) -> None:
        self._db_session_factory = db_session_factory
        self._semantic_search_fn = semantic_search_fn
        super().__init__()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def register_tools(self) -> None:
        self.register_tool(ToolDefinition(
            name="search_documents",
            description=(
                "Perform a semantic search across ingested documents and "
                "return the most relevant results."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural-language search query.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 10).",
                    },
                },
                "required": ["tenant_id", "query"],
                "additionalProperties": False,
            },
            handler=self._search_documents,
        ))

        self.register_tool(ToolDefinition(
            name="get_document_chunks",
            description=(
                "Return all chunks for a specific document, ordered by "
                "chunk index."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "UUID of the document.",
                    },
                },
                "required": ["tenant_id", "document_id"],
                "additionalProperties": False,
            },
            handler=self._get_document_chunks,
        ))

        self.register_tool(ToolDefinition(
            name="list_documents",
            description=(
                "List documents for the tenant with an optional status filter."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant UUID for RLS scoping.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processing", "ready", "error"],
                        "description": "Optional status to filter by.",
                    },
                },
                "required": ["tenant_id"],
                "additionalProperties": False,
            },
            handler=self._list_documents,
        ))

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _search_documents(
        self,
        tenant_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search via the domain semantic_search module."""
        limit = min(int(limit), 50)

        if self._semantic_search_fn is None:
            raise RuntimeError(
                "FileToolsServer requires a semantic_search_fn. "
                "Pass one when constructing the server."
            )

        results = await self._semantic_search_fn(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
        )

        return [
            {
                "document_id": str(r.get("document_id", "")),
                "chunk_id": str(r.get("chunk_id", "")),
                "text": r.get("text", ""),
                "relevance_score": r.get("relevance_score", 0.0),
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ]

    async def _get_document_chunks(
        self,
        tenant_id: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """Return all chunks belonging to a document."""
        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, chunk_index, text, embedding_status, metadata "
                "FROM document_chunks "
                "WHERE tenant_id = :tenant_id AND document_id = :document_id "
                "ORDER BY chunk_index ASC"
            )
            params = {"tenant_id": tenant_id, "document_id": document_id}

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    async def _list_documents(
        self,
        tenant_id: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List documents, optionally filtered by processing status."""
        async with self._get_readonly_session() as session:
            query = (
                "SELECT id, filename, status, mime_type, size_bytes, "
                "chunk_count, created_at, updated_at "
                "FROM documents WHERE tenant_id = :tenant_id"
            )
            params: dict[str, Any] = {"tenant_id": tenant_id}

            if status is not None:
                query += " AND status = :status"
                params["status"] = status

            query += " ORDER BY created_at DESC LIMIT 200"

            rows = await session.execute(query, params)
            return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _get_readonly_session(self):
        """Return an async context manager for a read-only DB session."""
        if self._db_session_factory is None:
            raise RuntimeError(
                "FileToolsServer requires a db_session_factory. "
                "Pass one when constructing the server."
            )
        return self._db_session_factory()
