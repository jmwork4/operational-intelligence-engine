"""Alert schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.common.types import AlertStatus, EntityType, Severity


class AlertResponse(BaseModel):
    """Schema returned when reading an alert."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_id: UUID
    entity_type: EntityType
    entity_id: str
    severity: Severity
    status: AlertStatus
    message: str
    context: dict
    dedup_key: str
    acknowledged_by: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""

    acknowledged_by: UUID = Field(
        ..., description="User ID of the person acknowledging the alert"
    )


class AlertFilter(BaseModel):
    """Schema for filtering alerts in list queries."""

    severity: Severity | None = Field(default=None)
    status: AlertStatus | None = Field(default=None)
    entity_type: EntityType | None = Field(default=None)
    entity_id: str | None = Field(default=None)
    rule_id: UUID | None = Field(default=None)
    from_date: datetime | None = Field(default=None)
    to_date: datetime | None = Field(default=None)
    limit: int = Field(default=50, ge=1, le=1000, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
