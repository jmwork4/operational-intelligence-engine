"""Rule schemas for the OIE API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.common.types import ActionType, EventType, RuleType, Severity


class RuleCreate(BaseModel):
    """Schema for creating a new rule."""

    rule_name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the rule"
    )
    rule_type: RuleType = Field(..., description="Type of rule")
    condition_expression: str = Field(
        ..., min_length=1, description="Rule condition expression"
    )
    severity: Severity = Field(
        default=Severity.MEDIUM, description="Alert severity when rule triggers"
    )
    action_type: ActionType = Field(
        default=ActionType.ALERT, description="Action to take when rule triggers"
    )
    trigger_event: EventType | None = Field(
        default=None, description="Event type that triggers this rule"
    )
    evaluation_window: int | None = Field(
        default=None, ge=1, description="Evaluation window in seconds"
    )
    enabled: bool = Field(default=True, description="Whether the rule is active")


class RuleUpdate(BaseModel):
    """Schema for updating an existing rule."""

    rule_name: str | None = Field(default=None, min_length=1, max_length=255)
    condition_expression: str | None = Field(default=None, min_length=1)
    severity: Severity | None = Field(default=None)
    action_type: ActionType | None = Field(default=None)
    trigger_event: EventType | None = Field(default=None)
    evaluation_window: int | None = Field(default=None, ge=1)
    enabled: bool | None = Field(default=None)


class RuleResponse(BaseModel):
    """Schema returned when reading a rule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_name: str
    rule_type: RuleType
    trigger_event: EventType | None
    condition_expression: str
    evaluation_window: int | None
    severity: Severity
    action_type: ActionType
    enabled: bool
    created_at: datetime
    updated_at: datetime
