"""AI query and response schemas for the OIE API."""

from uuid import UUID

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Reference to a source document chunk used in an AI response."""

    document_id: UUID
    document_title: str
    chunk_content: str
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score"
    )


class AITelemetrySummary(BaseModel):
    """Telemetry data for an AI query execution."""

    model_provider: str = Field(..., description="AI model provider name")
    model_name: str = Field(..., description="AI model name")
    input_tokens: int = Field(..., ge=0, description="Number of input tokens")
    output_tokens: int = Field(..., ge=0, description="Number of output tokens")
    latency_ms: float = Field(..., ge=0, description="Total latency in milliseconds")
    tools_used: list[str] = Field(
        default_factory=list, description="List of tools invoked during the query"
    )


class AIQueryRequest(BaseModel):
    """Schema for submitting a query to the AI engine."""

    query: str = Field(..., min_length=1, description="User query text")
    conversation_id: str | None = Field(
        default=None, description="Existing conversation ID for context continuity"
    )
    context_filter: dict | None = Field(
        default=None, description="Filters to scope the AI context"
    )


class AIQueryResponse(BaseModel):
    """Schema returned from an AI query."""

    response: str = Field(..., description="AI-generated response text")
    sources: list[SourceReference] = Field(
        default_factory=list, description="Source references used in the response"
    )
    conversation_id: str = Field(..., description="Conversation ID for follow-ups")
    telemetry: AITelemetrySummary = Field(
        ..., description="Telemetry data for the query"
    )
