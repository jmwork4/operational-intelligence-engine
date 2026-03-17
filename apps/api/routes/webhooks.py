"""Webhook API routes — receive, configure, and test inbound webhooks."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.integrations.webhook_receiver import (
    FieldMapping,
    InboundWebhookProcessor,
)
from packages.schemas import EventCreate

from apps.api.deps import get_current_tenant, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# ---------------------------------------------------------------------------
# In-memory store (will be replaced by DB-backed config in production)
# ---------------------------------------------------------------------------

_webhook_sources: dict[str, dict[str, Any]] = {}
_processor = InboundWebhookProcessor()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class WebhookSourceConfig(BaseModel):
    """Configuration payload for a webhook source."""

    source: str = Field(..., description="Unique name for the external source")
    secret: str | None = Field(default=None, description="HMAC-SHA256 shared secret")
    field_mappings: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description=(
            "Mapping of target EventCreate field name to "
            '{"source_field": "<dotted.path>"}'
        ),
    )
    description: str = Field(default="", description="Human-readable description")


class WebhookTestRequest(BaseModel):
    """Payload for testing a webhook configuration."""

    source: str = Field(..., description="Source name to test against")
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(..., description="Sample JSON body")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/inbound/{source}",
    status_code=status.HTTP_200_OK,
    summary="Receive an inbound webhook",
)
async def receive_webhook(
    source: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Receive a webhook from an external source, validate, map, and ingest."""
    body = await request.body()
    headers = dict(request.headers)

    # Look up config
    config = _webhook_sources.get(source, {})
    secret = config.get("secret")

    # Build processor with source secret
    processor = InboundWebhookProcessor(
        secrets={source: secret} if secret else None,
    )

    # Build field mappings from stored config
    raw_mappings: dict[str, dict[str, str]] = config.get("field_mappings", {})
    field_mapping: dict[str, FieldMapping] = {}
    for target, fm_dict in raw_mappings.items():
        field_mapping[target] = FieldMapping(
            source_field=fm_dict["source_field"],
            target_field=target,
        )

    try:
        events = await processor.process_webhook(
            source=source,
            headers=headers,
            body=body,
            field_mapping=field_mapping,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(exc)},
        )

    logger.info(
        "Webhook ingested",
        extra={"source": source, "event_count": len(events), "tenant_id": str(tenant_id)},
    )

    return {
        "status": "accepted",
        "source": source,
        "events_created": len(events),
        "events": [e.model_dump(mode="json") for e in events],
    }


@router.post(
    "/configure",
    status_code=status.HTTP_201_CREATED,
    summary="Configure a webhook source",
)
async def configure_webhook_source(
    config: WebhookSourceConfig,
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Register or update the configuration for an inbound webhook source."""
    _webhook_sources[config.source] = {
        "secret": config.secret,
        "field_mappings": {k: v for k, v in config.field_mappings.items()},
        "description": config.description,
        "tenant_id": str(tenant_id),
    }

    logger.info("Webhook source configured", extra={"source": config.source})
    return {"status": "configured", "source": config.source}


@router.get(
    "/sources",
    summary="List configured webhook sources",
)
async def list_webhook_sources(
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Return all configured webhook sources for the current tenant."""
    sources = [
        {
            "source": name,
            "description": cfg.get("description", ""),
            "has_secret": cfg.get("secret") is not None,
            "field_mapping_count": len(cfg.get("field_mappings", {})),
        }
        for name, cfg in _webhook_sources.items()
        if cfg.get("tenant_id") == str(tenant_id)
    ]
    return {"sources": sources}


@router.post(
    "/test",
    summary="Test a webhook configuration with sample data",
)
async def test_webhook(
    payload: WebhookTestRequest,
    tenant_id: UUID = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Dry-run a webhook payload against a configured source mapping."""
    config = _webhook_sources.get(payload.source, {})
    if not config:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Source '{payload.source}' is not configured"},
        )

    import json as _json

    body = _json.dumps(payload.body).encode()

    raw_mappings: dict[str, dict[str, str]] = config.get("field_mappings", {})
    field_mapping: dict[str, FieldMapping] = {}
    for target, fm_dict in raw_mappings.items():
        field_mapping[target] = FieldMapping(
            source_field=fm_dict["source_field"],
            target_field=target,
        )

    # Use a processor *without* signature enforcement for test
    processor = InboundWebhookProcessor()

    try:
        events = await processor.process_webhook(
            source=payload.source,
            headers=payload.headers,
            body=body,
            field_mapping=field_mapping,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(exc)},
        )

    return {
        "status": "ok",
        "source": payload.source,
        "events": [e.model_dump(mode="json") for e in events],
    }
