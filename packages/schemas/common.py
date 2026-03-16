"""Shared response schemas used across the OIE API."""

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list = Field(default_factory=list, description="List of result items")
    total: int = Field(..., ge=0, description="Total number of matching items")
    limit: int = Field(..., ge=1, description="Maximum items per page")
    offset: int = Field(..., ge=0, description="Number of items skipped")


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error context")


class HealthResponse(BaseModel):
    """Service health check response."""

    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
