"""Embedding worker tasks for generating and managing vector embeddings."""

from __future__ import annotations

from uuid import UUID

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def generate_embeddings(ctx: dict, document_id: str) -> dict:
    """Generate embeddings for document chunks.

    Loads the document, splits it into chunks, generates vector embeddings
    for each chunk, and stores them in the vector database.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        document_id: Unique identifier of the document to embed.

    Returns:
        dict with the document ID and number of chunks embedded.
    """
    logger.info("generate_embeddings_start", document_id=document_id)

    try:
        from packages.common.settings import get_settings
        from packages.db.session import init_db, create_async_session_factory
        from packages.storage import get_storage_adapter
        from packages.domain.document_processor import DocumentProcessor
        from packages.domain.embedding_service import EmbeddingService

        settings = get_settings()
        doc_uuid = UUID(document_id)

        # Initialise database session
        engine = init_db(settings.DATABASE_URL)
        session_factory = create_async_session_factory(engine)

        async with session_factory() as session:
            # Determine tenant_id from the document record
            import sqlalchemy as sa
            from packages.db.models.document import Document

            result = await session.execute(
                sa.select(Document).where(Document.id == doc_uuid)
            )
            document = result.scalar_one()
            tenant_id = document.tenant_id

            # Step 1: Process document (download, extract text, chunk)
            async with get_storage_adapter(
                "minio",
                endpoint_url=settings.S3_ENDPOINT_URL,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                region=settings.S3_REGION,
            ) as storage:
                processor = DocumentProcessor(session, storage)
                process_result = await processor.process_document(doc_uuid, tenant_id)

            # Step 2: Generate embeddings
            embedding_service = EmbeddingService(session)
            embed_result = await embedding_service.generate_embeddings(doc_uuid, tenant_id)

            await session.commit()

        chunk_count = process_result["chunk_count"]

        logger.info(
            "generate_embeddings_complete",
            document_id=document_id,
            chunk_count=chunk_count,
            embedding_count=embed_result["embedding_count"],
        )

        return {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": chunk_count,
            "embedding_count": embed_result["embedding_count"],
            "model_name": embed_result["model_name"],
        }

    except Exception:
        logger.exception("generate_embeddings_failed", document_id=document_id)
        raise


async def reindex_document(ctx: dict, document_id: str) -> dict:
    """Regenerate all embeddings for a document.

    Deletes existing embeddings for the document and regenerates them from
    scratch. Useful when the embedding model changes or document content is
    updated.

    Args:
        ctx: ARQ context containing redis connection and shared resources.
        document_id: Unique identifier of the document to reindex.

    Returns:
        dict with the document ID and number of chunks reindexed.
    """
    logger.info("reindex_document_start", document_id=document_id)

    try:
        from packages.common.settings import get_settings
        from packages.db.session import init_db, create_async_session_factory
        from packages.domain.embedding_service import EmbeddingService

        settings = get_settings()
        doc_uuid = UUID(document_id)

        # Initialise database session
        engine = init_db(settings.DATABASE_URL)
        session_factory = create_async_session_factory(engine)

        async with session_factory() as session:
            # Determine tenant_id from the document record
            import sqlalchemy as sa
            from packages.db.models.document import Document

            result = await session.execute(
                sa.select(Document).where(Document.id == doc_uuid)
            )
            document = result.scalar_one()
            tenant_id = document.tenant_id

            # Reindex: delete old embeddings and regenerate
            embedding_service = EmbeddingService(session)
            embed_result = await embedding_service.reindex_document(doc_uuid, tenant_id)

            await session.commit()

        logger.info("reindex_document_complete", document_id=document_id)

        return {
            "status": "reindexed",
            "document_id": document_id,
            "chunk_count": embed_result["embedding_count"],
            "model_name": embed_result["model_name"],
        }

    except Exception:
        logger.exception("reindex_document_failed", document_id=document_id)
        raise
