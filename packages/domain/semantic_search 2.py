"""Semantic search over document embeddings using pgvector cosine distance."""

from __future__ import annotations

import hashlib
import math
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536


class SemanticSearch:
    """Performs semantic similarity search against stored document embeddings.

    Queries use the pgvector ``<=>`` (cosine distance) operator.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        tenant_id: UUID,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """Search for document chunks most similar to *query*.

        Args:
            query: Natural-language search text.
            tenant_id: Tenant scope for row-level filtering.
            limit: Maximum number of results to return.
            similarity_threshold: Minimum cosine similarity (0-1) to include.

        Returns:
            List of dicts with *chunk_id*, *document_id*, *document_title*,
            *content*, and *similarity_score*, ordered by descending similarity.
        """
        query_vector = self._generate_embedding(query)
        vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

        sql = sa.text(
            """
            SELECT e.id,
                   dc.id        AS chunk_id,
                   dc.document_id,
                   dc.content,
                   dc.chunk_index,
                   d.title      AS document_title,
                   1 - (e.embedding <=> :query_vector::vector) AS similarity
            FROM   embeddings e
            JOIN   document_chunks dc ON e.chunk_id = dc.id
            JOIN   documents d        ON dc.document_id = d.id
            WHERE  e.tenant_id = :tenant_id
              AND  1 - (e.embedding <=> :query_vector::vector) >= :threshold
            ORDER  BY e.embedding <=> :query_vector::vector
            LIMIT  :limit
            """
        )

        result = await self._session.execute(
            sql,
            {
                "query_vector": vector_literal,
                "tenant_id": str(tenant_id),
                "threshold": similarity_threshold,
                "limit": limit,
            },
        )

        rows = result.mappings().all()

        logger.info(
            "semantic_search_complete",
            query_length=len(query),
            tenant_id=str(tenant_id),
            result_count=len(rows),
        )

        return [
            {
                "chunk_id": str(row["chunk_id"]),
                "document_id": str(row["document_id"]),
                "document_title": row["document_title"],
                "content": row["content"],
                "similarity_score": float(row["similarity"]),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_embedding(text: str) -> list[float]:
        """Generate a deterministic 1536-dimensional unit vector from *text*.

        Uses SHA-512 hashing (repeated with different salts) to fill the
        vector, then normalises to unit length.  This is a placeholder — a
        real implementation would call an embedding API.
        """
        vector: list[float] = []
        iterations_needed = math.ceil(EMBEDDING_DIM / 64)

        for i in range(iterations_needed):
            h = hashlib.sha512(f"{i}:{text}".encode("utf-8")).digest()
            for byte_val in h:
                if len(vector) >= EMBEDDING_DIM:
                    break
                vector.append((byte_val / 127.5) - 1.0)

        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector
