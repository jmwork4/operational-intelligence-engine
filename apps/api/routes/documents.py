"""Document routes — upload, list, delete, and semantic search."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import ResourceNotFoundError, generate_uuid
from packages.db.models.document import Document
from packages.schemas import (
    DocumentResponse,
    PaginatedResponse,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from packages.storage import StorageAdapter

from apps.api.deps import RateLimiter, get_current_tenant, get_db, get_storage

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_per_minute=30))],
)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
    storage: StorageAdapter = Depends(get_storage),
) -> DocumentResponse:
    """Upload a document (multipart), store in object storage, and create a DB record."""
    from packages.common import get_settings

    settings = get_settings()
    file_content = await file.read()
    file_size = len(file_content)
    file_type = file.content_type or "application/octet-stream"

    # Generate a unique storage key.
    file_key = f"tenants/{tenant_id}/documents/{generate_uuid()}/{file.filename}"

    # Upload to object storage.
    async with storage:
        await storage.ensure_bucket(settings.S3_BUCKET_NAME)
        await storage.upload(
            settings.S3_BUCKET_NAME,
            file_key,
            file_content,
            content_type=file_type,
        )

    # Create DB record.
    doc = Document(
        tenant_id=tenant_id,
        title=title,
        file_key=file_key,
        file_type=file_type,
        file_size=file_size,
        status="uploaded",
        metadata_={},
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Enqueue embedding generation via ARQ
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await arq_pool.enqueue_job(
            "generate_embeddings",
            {"document_id": str(doc.id), "tenant_id": str(tenant_id)},
        )
        await arq_pool.close()
    except Exception:
        pass  # Worker will pick it up on next sweep if enqueue fails

    return DocumentResponse.model_validate(doc)


@router.get(
    "/",
    response_model=PaginatedResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PaginatedResponse:
    """List documents for the current tenant."""
    count_stmt = (
        sa.select(sa.func.count())
        .select_from(Document)
        .where(Document.tenant_id == tenant_id)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        sa.select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return PaginatedResponse(
        items=[DocumentResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> DocumentResponse:
    """Get a single document by ID."""
    stmt = sa.select(Document).where(
        Document.id == document_id, Document.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise ResourceNotFoundError("Document", str(document_id))

    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimiter(requests_per_minute=30))],
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
    storage: StorageAdapter = Depends(get_storage),
) -> None:
    """Delete a document from both the database and object storage."""
    from packages.common import get_settings

    settings = get_settings()

    stmt = sa.select(Document).where(
        Document.id == document_id, Document.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if doc is None:
        raise ResourceNotFoundError("Document", str(document_id))

    # Remove from object storage.
    async with storage:
        await storage.delete(settings.S3_BUCKET_NAME, doc.file_key)

    await db.delete(doc)
    await db.commit()


@router.post(
    "/search",
    response_model=list[SemanticSearchResult],
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def semantic_search(
    body: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> list[SemanticSearchResult]:
    """Perform a semantic search across document embeddings using pgvector."""
    from packages.domain.semantic_search import SemanticSearch

    search_service = SemanticSearch(db)
    results = await search_service.search(
        query=body.query,
        tenant_id=tenant_id,
        limit=body.limit,
        similarity_threshold=body.similarity_threshold,
    )
    return [SemanticSearchResult(**r) for r in results]
