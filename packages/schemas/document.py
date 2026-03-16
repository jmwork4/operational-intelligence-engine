"""Document and semantic search schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    title: str = Field(
        ..., min_length=1, max_length=500, description="Document title"
    )
    file_type: str = Field(
        ..., min_length=1, max_length=50, description="File MIME type or extension"
    )
    metadata: dict = Field(
        default_factory=dict, description="Additional document metadata"
    )


class DocumentResponse(BaseModel):
    """Schema returned when reading a document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    title: str
    file_key: str
    file_type: str
    file_size: int
    status: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    """Schema returned when reading a document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    token_count: int


class SemanticSearchRequest(BaseModel):
    """Schema for performing a semantic search query."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(
        default=5, ge=1, le=100, description="Maximum number of results"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to include",
    )


class SemanticSearchResult(BaseModel):
    """Schema for a single semantic search result."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    content: str
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score"
    )
