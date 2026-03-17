"""Integration management routes — list, configure, and test integrations."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from packages.integrations.outbound import NotificationDispatcher

from apps.api.deps import get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# ---------------------------------------------------------------------------
# In-memory store (production would use database-backed config)
# ---------------------------------------------------------------------------

_AVAILABLE_INTEGRATIONS: list[dict[str, Any]] = [
    {
        "name": "slack",
        "display_name": "Slack",
        "description": "Send alert notifications to Slack channels via incoming webhooks.",
        "category": "notification",
        "required_fields": ["webhook_url"],
    },
    {
        "name": "email",
        "display_name": "Email (SMTP)",
        "description": "Send alert notifications via email using SMTP.",
        "category": "notification",
        "required_fields": ["smtp_host", "smtp_port", "username", "password", "from_addr"],
    },
    {
        "name": "sms",
        "display_name": "SMS (Twilio)",
        "description": "Send SMS notifications via Twilio.",
        "category": "notification",
        "required_fields": ["account_sid", "auth_token", "from_number"],
    },
    {
        "name": "pagerduty",
        "display_name": "PagerDuty",
        "description": "Create PagerDuty incidents from OIE alerts via Events API v2.",
        "category": "notification",
        "required_fields": ["routing_key"],
    },
    {
        "name": "teams",
        "display_name": "Microsoft Teams",
        "description": "Send alert notifications to Teams channels via webhook.",
        "category": "notification",
        "required_fields": ["webhook_url"],
    },
    {
        "name": "edi",
        "display_name": "EDI (204/214/990)",
        "description": "Parse EDI logistics documents into OIE events.",
        "category": "data_source",
        "required_fields": [],
    },
]

_integration_configs: dict[str, dict[str, Any]] = {}

_dispatcher = NotificationDispatcher()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class IntegrationConfigureRequest(BaseModel):
    """Payload to configure an integration."""

    config: dict[str, Any] = Field(
        ..., description="Integration-specific configuration values"
    )
    enabled: bool = Field(default=True, description="Whether the integration is active")


class NotificationTestRequest(BaseModel):
    """Payload to test a notification dispatch."""

    channel: dict[str, Any] = Field(
        ...,
        description=(
            'Channel config including "type" and channel-specific fields '
            "(e.g. webhook_url for Slack)"
        ),
    )
    alert: dict[str, Any] = Field(
        default_factory=lambda: {
            "severity": "info",
            "entity": "test-entity",
            "message": "This is a test notification from OIE.",
        },
        description="Alert payload to send",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/",
    summary="List available integrations",
)
async def list_integrations(
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Return all available integrations and their current configuration status."""
    results = []
    for integration in _AVAILABLE_INTEGRATIONS:
        name = integration["name"]
        tenant_key = f"{tenant_id}:{name}"
        stored = _integration_configs.get(tenant_key)
        results.append(
            {
                **integration,
                "configured": stored is not None,
                "enabled": stored.get("enabled", False) if stored else False,
            }
        )
    return {"integrations": results}


@router.post(
    "/{name}/configure",
    status_code=status.HTTP_200_OK,
    summary="Configure an integration",
)
async def configure_integration(
    name: str,
    body: IntegrationConfigureRequest,
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Store configuration for the named integration."""
    # Validate integration name
    known_names = {i["name"] for i in _AVAILABLE_INTEGRATIONS}
    if name not in known_names:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Integration '{name}' not found"},
        )

    tenant_key = f"{tenant_id}:{name}"
    _integration_configs[tenant_key] = {
        "config": body.config,
        "enabled": body.enabled,
    }

    logger.info("Integration configured", extra={"name": name, "tenant_id": str(tenant_id)})
    return {"status": "configured", "name": name, "enabled": body.enabled}


@router.get(
    "/{name}/status",
    summary="Check integration health",
)
async def integration_status(
    name: str,
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Return the health / configuration status for a specific integration."""
    known_names = {i["name"] for i in _AVAILABLE_INTEGRATIONS}
    if name not in known_names:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Integration '{name}' not found"},
        )

    tenant_key = f"{tenant_id}:{name}"
    stored = _integration_configs.get(tenant_key)

    return {
        "name": name,
        "configured": stored is not None,
        "enabled": stored.get("enabled", False) if stored else False,
        "health": "ok" if stored and stored.get("enabled") else "unconfigured",
    }


@router.post(
    "/notifications/test",
    summary="Test notification dispatch",
)
async def test_notification(
    body: NotificationTestRequest,
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Send a test notification through the specified channel."""
    results = await _dispatcher.dispatch(channels=[body.channel], alert=body.alert)
    result = results[0] if results else {"type": "unknown", "success": False}
    return {
        "status": "sent" if result.get("success") else "failed",
        **result,
    }
