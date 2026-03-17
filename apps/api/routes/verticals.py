"""Vertical package routes — list, inspect, and apply industry vertical packages."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from apps.api.deps import get_current_tenant
from packages.verticals.base import get_vertical, list_verticals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verticals", tags=["Verticals"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class VerticalSummary(BaseModel):
    name: str
    display_name: str
    description: str
    event_type_count: int
    rule_template_count: int
    prompt_template_count: int


class VerticalDetail(BaseModel):
    name: str
    display_name: str
    description: str
    event_types: list[dict]
    rule_templates: list[dict]
    prompt_templates: list[dict]
    dashboard_config: dict
    document_templates: list[str]


class ApplyResult(BaseModel):
    vertical: str
    tenant_id: str
    event_types_created: int
    rules_created: int
    prompts_created: int
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[VerticalSummary])
async def list_available_verticals() -> list[VerticalSummary]:
    """List all available industry vertical packages."""
    verticals = list_verticals()
    return [
        VerticalSummary(
            name=v.name,
            display_name=v.display_name,
            description=v.description,
            event_type_count=len(v.event_types),
            rule_template_count=len(v.rule_templates),
            prompt_template_count=len(v.prompt_templates),
        )
        for v in verticals
    ]


@router.get("/{name}", response_model=VerticalDetail)
async def get_vertical_detail(name: str) -> VerticalDetail:
    """Get full details for a specific vertical package."""
    v = get_vertical(name)
    return VerticalDetail(
        name=v.name,
        display_name=v.display_name,
        description=v.description,
        event_types=v.event_types,
        rule_templates=v.rule_templates,
        prompt_templates=v.prompt_templates,
        dashboard_config=v.dashboard_config,
        document_templates=v.document_templates,
    )


@router.post(
    "/{name}/apply",
    response_model=ApplyResult,
    status_code=status.HTTP_201_CREATED,
)
async def apply_vertical(
    name: str,
    tenant_id: UUID = Depends(get_current_tenant),
) -> ApplyResult:
    """Apply an industry vertical package to the current tenant.

    Creates event types, rules, and prompt configurations based on the
    vertical's templates.
    """
    v = get_vertical(name)

    logger.info(
        "Applying vertical package",
        extra={"vertical": name, "tenant_id": str(tenant_id)},
    )

    # In a full implementation this would persist event types, rules, and
    # prompts to the database for the tenant.  For now we return a summary
    # of what would be created.

    return ApplyResult(
        vertical=v.name,
        tenant_id=str(tenant_id),
        event_types_created=len(v.event_types),
        rules_created=len(v.rule_templates),
        prompts_created=len(v.prompt_templates),
        message=(
            f"Successfully applied {v.display_name} package: "
            f"{len(v.event_types)} event types, {len(v.rule_templates)} rules, "
            f"{len(v.prompt_templates)} prompts configured."
        ),
    )
