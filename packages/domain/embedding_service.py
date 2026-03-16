"""Embedding generation pipeline — create and store vector embeddings for document chunks."""

from __future__ import annotations

import hashlib
import math
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.document import Document, DocumentChunk, Embedding

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536
MODEL_NAME = "placeholder-v1"


class EmbeddingService:
    """Generates vector embeddings for document chunks and persists them.

    Uses a deterministic hash-based placeholder embedding until a real
    embedding model (e.g. OpenAI ``text-embedding-3-small``) is integrated.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_embeddings(
        self,
        document_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """Generate and store embeddings for every chunk of *document_id*.

        Returns a summary dict with *document_id*, *embedding_count*, and
        *model_name*.
        """
        # Load all chunks for the document
        result = await self._session.execute(
            sa.select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()

        if not chunks:
            logger.warning(
                "no_chunks_found",
                document_id=str(document_id),
            )
            return {
                "document_id": str(document_id),
                "embedding_count": 0,
                "model_name": MODEL_NAME,
            }

        # Generate and persist an embedding for each chunk
        for chunk in chunks:
            vector = self._generate_embedding(chunk.content)
            embedding = Embedding(
                id=uuid4(),
                chunk_id=chunk.id,
                tenant_id=tenant_id,
                embedding=vector,
                model_name=MODEL_NAME,
            )
            self._session.add(embedding)

        # Update document status
        await self._session.execute(
            sa.update(Document)
            .where(Document.id == document_id)
            .values(status="indexed")
        )

        await self._session.flush()

        logger.info(
            "embeddings_generated",
            document_id=str(document_id),
            embedding_count=len(chunks),
            model_name=MODEL_NAME,
        )

        return {
            "document_id": str(document_id),
            "embedding_count": len(chunks),
            "model_name": MODEL_NAME,
        }

    async def reindex_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """Delete existing embeddings for *document_id* and regenerate them.

        Returns the same summary dict as :meth:`generate_embeddings`.
        """
        # Find all chunk IDs belonging to this document
        chunk_result = await self._session.execute(
            sa.select(DocumentChunk.id).where(
                DocumentChunk.document_id == document_id
            )
        )
        chunk_ids = [row[0] for row in chunk_result.all()]

        # Delete existing embeddings for those chunks
        if chunk_ids:
            await self._session.execute(
                sa.delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids))
            )

        logger.info(
            "existing_embeddings_deleted",
            document_id=str(document_id),
            deleted_chunk_count=len(chunk_ids),
        )

        # Re-generate embeddings
        result = await self.generate_embeddings(document_id, tenant_id)
        return result

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
        iterations_needed = math.ceil(EMBEDDING_DIM / 64)  # SHA-512 -> 64 bytes

        for i in range(iterations_needed):
            h = hashlib.sha512(f"{i}:{text}".encode("utf-8")).digest()
            # Each byte -> a float in [-1, 1]
            for byte_val in h:
                if len(vector) >= EMBEDDING_DIM:
                    break
                vector.append((byte_val / 127.5) - 1.0)

        # Normalise to unit length
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector
