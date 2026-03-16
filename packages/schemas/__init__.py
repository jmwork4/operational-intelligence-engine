"""OIE Pydantic schemas for API request/response validation."""

from packages.schemas.ai import (
    AIQueryRequest,
    AIQueryResponse,
    AITelemetrySummary,
    SourceReference,
)
from packages.schemas.alert import AlertAcknowledge, AlertFilter, AlertResponse
from packages.schemas.common import ErrorResponse, HealthResponse, PaginatedResponse
from packages.schemas.document import (
    DocumentChunkResponse,
    DocumentCreate,
    DocumentResponse,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from packages.schemas.event import (
    EventBatchCreate,
    EventCreate,
    EventFilter,
    EventResponse,
)
from packages.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from packages.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from packages.schemas.user import TokenResponse, UserCreate, UserResponse, UserUpdate

__all__ = [
    # AI
    "AIQueryRequest",
    "AIQueryResponse",
    "AITelemetrySummary",
    "SourceReference",
    # Alert
    "AlertAcknowledge",
    "AlertFilter",
    "AlertResponse",
    # Common
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    # Document
    "DocumentChunkResponse",
    "DocumentCreate",
    "DocumentResponse",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    # Event
    "EventBatchCreate",
    "EventCreate",
    "EventFilter",
    "EventResponse",
    # Rule
    "RuleCreate",
    "RuleResponse",
    "RuleUpdate",
    # Tenant
    "TenantCreate",
    "TenantResponse",
    "TenantUpdate",
    # User
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
