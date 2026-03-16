"""AI routes — natural-language query interface and telemetry."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai import AIService
from packages.common import PolicyViolationError, get_settings
from packages.schemas import (
    AIQueryRequest,
    AIQueryResponse,
    AITelemetrySummary,
    SourceReference,
)

from apps.api.deps import RateLimiter, get_current_tenant, get_db

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/query",
    response_model=AIQueryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(requests_per_minute=30))],
)
async def ai_query(
    body: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> AIQueryResponse:
    """Submit a natural-language query to the AI copilot.

    Full pipeline: InputPolicyGuard -> PromptRegistry -> SemanticSearch ->
    ContextAssembly -> ModelRouter -> Anthropic API (with tool use) ->
    OutputPolicyGuard -> Telemetry -> Response.
    """
    settings = get_settings()

    ai_service = AIService(db=db, settings=settings)
    result = await ai_service.query(
        query=body.query,
        tenant_id=tenant_id,
        conversation_id=body.conversation_id,
        context_filter=body.context_filter,
    )

    # Map result to response schema
    sources = [
        SourceReference(**s) for s in result.get("sources", [])
    ]
    telemetry = result.get("telemetry", {})

    return AIQueryResponse(
        response=result["response"],
        sources=sources,
        conversation_id=result.get("conversation_id", ""),
        telemetry=AITelemetrySummary(
            model_provider=telemetry.get("model_provider", settings.DEFAULT_MODEL_PROVIDER),
            model_name=telemetry.get("model_name", settings.DEFAULT_MODEL_NAME),
            input_tokens=telemetry.get("input_tokens", 0),
            output_tokens=telemetry.get("output_tokens", 0),
            latency_ms=telemetry.get("latency_ms", 0),
            tools_used=telemetry.get("tools_used", []),
        ),
    )


@router.get(
    "/telemetry",
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def get_ai_telemetry(
    hours: int = Query(default=24, ge=1, le=168),
    tenant_id: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI telemetry metrics for the specified time range.

    Returns aggregated stats on model usage, token consumption, latency,
    tool invocations, and policy guard results.
    """
    # Return mock telemetry data for now — will be populated from
    # the ai_telemetry table once recording is fully wired.
    return {
        "time_range_hours": hours,
        "tenant_id": str(tenant_id),
        "summary": {
            "total_queries": 284,
            "avg_latency_ms": 3200,
            "total_input_tokens": 892_400,
            "total_output_tokens": 245_600,
            "avg_context_utilization_pct": 62.4,
        },
        "by_model": {
            "claude-sonnet-4-20250514": {
                "queries": 284,
                "avg_latency_ms": 3200,
                "input_tokens": 892_400,
                "output_tokens": 245_600,
            }
        },
        "tool_usage": {
            "total_invocations": 412,
            "failures": 3,
            "by_tool": {
                "sql__query_events": 156,
                "sql__get_event_stats": 89,
                "file__search_documents": 78,
                "workflow__get_alert_summary": 62,
                "observability__get_system_health": 27,
            },
        },
        "policy_guard": {
            "input_checks": 284,
            "input_violations": 2,
            "output_checks": 282,
            "output_violations": 0,
            "avg_input_risk_score": 0.05,
            "avg_output_risk_score": 0.02,
        },
    }
