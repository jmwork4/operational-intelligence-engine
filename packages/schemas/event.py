"""Event schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.common.types import EntityType, EventType


class EventCreate(BaseModel):
    """Schema for creating a new event."""

    event_type: EventType = Field(..., description="Type of event")
    entity_type: EntityType = Field(..., description="Type of entity involved")
    entity_id: str = Field(..., min_length=1, description="Identifier of the entity")
    source_system: str = Field(
        ..., min_length=1, description="System that generated the event"
    )
    payload: dict = Field(default_factory=dict, description="Event payload data")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    occurred_at: datetime | None = Field(
        default=None, description="When the event occurred"
    )
    process_id: str | None = Field(
        default=None, description="Associated process identifier"
    )
    resource_id: str | None = Field(
        default=None, description="Associated resource identifier"
    )


class EventBatchCreate(BaseModel):
    """Schema for creating multiple events in a single request."""

    events: list[EventCreate] = Field(
        ..., min_length=1, description="List of events to create"
    )


class EventResponse(BaseModel):
    """Schema returned when reading an event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    event_type: EventType
    entity_type: EntityType
    entity_id: str
    process_id: str | None
    resource_id: str | None
    source_system: str
    payload: dict
    metadata: dict
    occurred_at: datetime
    ingested_at: datetime
    trace_id: UUID | None


class EventFilter(BaseModel):
    """Schema for filtering events in list queries."""

    event_type: EventType | None = Field(default=None)
    entity_type: EntityType | None = Field(default=None)
    entity_id: str | None = Field(default=None)
    source_system: str | None = Field(default=None)
    from_date: datetime | None = Field(default=None)
    to_date: datetime | None = Field(default=None)
    limit: int = Field(default=50, ge=1, le=1000, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
