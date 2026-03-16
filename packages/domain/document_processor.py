"""Document ingestion pipeline — download, extract text, and chunk documents."""

from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.document import Document, DocumentChunk
from packages.storage import StorageAdapter

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Downloads a document from object storage, extracts its text content,
    splits it into overlapping chunks, and persists the chunks to the database.
    """

    def __init__(self, session: AsyncSession, storage: StorageAdapter) -> None:
        self._session = session
        self._storage = storage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_document(
        self,
        document_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """Run the full ingestion pipeline for a single document.

        1. Download the file from object storage.
        2. Extract plain text from the file content.
        3. Split text into overlapping chunks.
        4. Persist :class:`DocumentChunk` records.
        5. Update the document status to ``"chunked"``.

        Returns a summary dict with *document_id*, *chunk_count*, and
        *total_tokens*.
        """
        # Fetch the document record
        result = await self._session.execute(
            sa.select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one()

        # Download file content from storage
        bucket = document.file_key.split("/")[0] if "/" in document.file_key else "oie-documents"
        key = "/".join(document.file_key.split("/")[1:]) if "/" in document.file_key else document.file_key
        content = await self._storage.download(bucket, key)

        # Extract text
        text = self._extract_text(content, document.file_type)

        # Split into chunks
        chunks = self._split_into_chunks(text)

        # Persist chunks
        total_tokens = 0
        for chunk_data in chunks:
            chunk = DocumentChunk(
                id=uuid4(),
                document_id=document_id,
                tenant_id=tenant_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
            )
            self._session.add(chunk)
            total_tokens += chunk_data["token_count"]

        # Update document status
        await self._session.execute(
            sa.update(Document)
            .where(Document.id == document_id)
            .values(status="chunked")
        )

        await self._session.flush()

        logger.info(
            "document_processed",
            document_id=str(document_id),
            chunk_count=len(chunks),
            total_tokens=total_tokens,
        )

        return {
            "document_id": str(document_id),
            "chunk_count": len(chunks),
            "total_tokens": total_tokens,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(content: bytes, file_type: str) -> str:
        """Extract plain text from raw file bytes.

        Supports ``txt``, ``pdf``, and ``docx`` file types.  For PDF files
        the bytes are decoded as UTF-8 with a lossy fallback — this is a
        simple placeholder until a proper PDF parser (e.g. PyMuPDF) is
        integrated.  DOCX extraction similarly falls back to UTF-8 decoding.
        """
        file_type_lower = file_type.lower().strip(".")

        if file_type_lower in ("txt", "text", "text/plain"):
            return content.decode("utf-8", errors="replace")

        if file_type_lower in ("pdf", "application/pdf"):
            # Simple fallback: decode bytes as text.  A real implementation
            # would use a library like PyMuPDF or pdfplumber.
            return content.decode("utf-8", errors="replace")

        if file_type_lower in (
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            # Simple fallback: decode bytes as text.  A real implementation
            # would use python-docx.
            return content.decode("utf-8", errors="replace")

        # Fallback for unknown types
        return content.decode("utf-8", errors="replace")

    @staticmethod
    def _split_into_chunks(
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[dict]:
        """Split *text* into overlapping chunks.

        Each returned dict contains:
        - ``chunk_index``: zero-based position
        - ``content``: the chunk text
        - ``token_count``: estimated token count (``len(content) // 4``)
        """
        chunks: list[dict] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            if chunk_text.strip():  # skip empty/whitespace-only chunks
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": chunk_text,
                        "token_count": len(chunk_text) // 4,
                    }
                )
                chunk_index += 1

            # Advance by (chunk_size - overlap) so consecutive chunks overlap
            start += chunk_size - overlap

        return chunks
