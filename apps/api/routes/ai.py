"""AI routes — natural-language query interface."""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai import (
    ContextAssembler,
    InputPolicyGuard,
    OutputPolicyGuard,
    PromptRegistry,
)
from packages.common import PolicyViolationError, generate_uuid, get_settings
from packages.schemas import (
    AIQueryRequest,
    AIQueryResponse,
    AITelemetrySummary,
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
    """Submit a natural-language query to the AI engine.

    Pipeline:
    1. Run InputPolicyGuard on the user query.
    2. Fetch the active prompt from PromptRegistry.
    3. Assemble a token-budgeted context via ContextAssembler.
    4. Invoke the model (placeholder).
    5. Run OutputPolicyGuard on the generated response.
    6. Return the response with telemetry.
    """
    settings = get_settings()
    start_time = time.perf_counter()

    # --- 1. Input policy guard -------------------------------------------
    input_guard = InputPolicyGuard()
    input_result = await input_guard.check(body.query, tenant_id)
    if not input_result.allowed:
        raise PolicyViolationError(
            message=f"Input policy violation: {'; '.join(input_result.violations)}",
            violation_type="input",
        )

    # --- 2. Fetch active prompt ------------------------------------------
    registry = PromptRegistry(session=db)
    try:
        prompt = await registry.get_active_prompt(
            task_type="general_query",
            model_family=settings.DEFAULT_MODEL_PROVIDER,
        )
    except ValueError:
        # Fallback system prompt when no prompt is registered yet.
        prompt = {
            "system_prompt": (
                "You are an operational intelligence assistant. "
                "Answer questions about logistics, supply-chain events, and "
                "alerts using the provided context."
            ),
            "user_template": "{query}",
        }

    # --- 3. Context assembly ---------------------------------------------
    assembler = ContextAssembler(max_tokens=settings.MAX_CONTEXT_TOKENS)
    conversation_history: list[dict] = []
    knowledge_chunks: list[dict] = []

    # TODO: retrieve conversation history from DB if conversation_id provided
    # TODO: run semantic search to populate knowledge_chunks

    assembled = await assembler.assemble(
        system_prompt=prompt["system_prompt"],
        conversation_history=conversation_history,
        knowledge_chunks=knowledge_chunks,
    )

    # --- 4. Model invocation (placeholder) --------------------------------
    # TODO: replace with actual model call via ModelRouter
    model_response_text = (
        "This is a placeholder response. The AI model integration is pending. "
        "Your query was: " + body.query
    )
    input_tokens = assembled.total_tokens
    output_tokens = len(model_response_text) // 4

    # --- 5. Output policy guard ------------------------------------------
    output_guard = OutputPolicyGuard()
    output_result = await output_guard.check(model_response_text)
    if not output_result.allowed:
        raise PolicyViolationError(
            message=f"Output policy violation: {'; '.join(output_result.violations)}",
            violation_type="output",
        )

    # --- 6. Build response -----------------------------------------------
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    conversation_id = body.conversation_id or str(generate_uuid())

    return AIQueryResponse(
        response=model_response_text,
        sources=[],
        conversation_id=conversation_id,
        telemetry=AITelemetrySummary(
            model_provider=settings.DEFAULT_MODEL_PROVIDER,
            model_name=settings.DEFAULT_MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(elapsed_ms, 2),
            tools_used=[],
        ),
    )
