"""Document, DocumentChunk, and Embedding models."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from packages.db.base import AuditMixin, Base, TenantMixin, TimestampMixin


class Document(AuditMixin, Base):
    __tablename__ = "documents"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    file_key: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )


class DocumentChunk(TenantMixin, Base):
    __tablename__ = "document_chunks"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    document_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    token_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


class Embedding(TenantMixin, Base):
    __tablename__ = "embeddings"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    chunk_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding = mapped_column(Vector(1536), nullable=False)
    model_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
