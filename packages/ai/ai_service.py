"""AI Service — main orchestrator for the OIE AI query pipeline.

Coordinates the full lifecycle of an AI query: policy checks, prompt
retrieval, context assembly, model routing, Anthropic API calls with
tool-use support, output validation, and telemetry recording.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.context_assembly import AssembledContext, ContextAssembler
from packages.ai.model_router import ModelRouter
from packages.ai.policy_guard import InputPolicyGuard, OutputPolicyGuard
from packages.ai.prompt_registry import PromptRegistry
from packages.ai.tool_coordinator import ToolCoordinator
from packages.common.settings import Settings

logger = logging.getLogger(__name__)

# Maximum number of tool-use round-trips before forcing a final response.
_MAX_TOOL_ROUNDS = 3

# Fallback system prompt when no prompt template is found in the registry.
_FALLBACK_SYSTEM_PROMPT = (
    "You are a helpful AI assistant for the Operational Intelligence Engine (OIE). "
    "Answer the user's question based on the provided context. "
    "If you are unsure, say so rather than guessing."
)


class AIService:
    """Main orchestrator for AI query processing.

    Parameters
    ----------
    session:
        An async SQLAlchemy session for database operations.
    settings:
        Application settings (contains API keys, model defaults, etc.).
    tool_coordinator:
        Optional :class:`ToolCoordinator` for MCP tool execution.
    """

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        tool_coordinator: ToolCoordinator | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._tool_coordinator = tool_coordinator or ToolCoordinator()
        self._prompt_registry = PromptRegistry(session)
        self._model_router = ModelRouter()
        self._context_assembler = ContextAssembler(
            max_tokens=settings.MAX_CONTEXT_TOKENS
        )
        self._input_guard = InputPolicyGuard()
        self._output_guard = OutputPolicyGuard()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def query(
        self,
        query: str,
        tenant_id: UUID,
        conversation_id: str | None = None,
        context_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the full AI query pipeline.

        Returns a dict with keys: ``response``, ``sources``,
        ``conversation_id``, ``telemetry``.
        """
        pipeline_start = time.monotonic()
        conversation_id = conversation_id or str(uuid4())
        telemetry: dict[str, Any] = {"conversation_id": conversation_id}

        # ---- 1. Input policy guard -----------------------------------
        input_result = await self._input_guard.check(
            query=query,
            tenant_id=tenant_id,
            context=context_filter,
        )
        if not input_result.allowed:
            logger.warning(
                "Input policy guard rejected query for tenant %s: %s",
                tenant_id,
                input_result.violations,
            )
            return {
                "response": (
                    "I'm unable to process this request due to policy "
                    "restrictions. Please rephrase your question."
                ),
                "sources": [],
                "conversation_id": conversation_id,
                "telemetry": {
                    **telemetry,
                    "rejected": True,
                    "rejection_reason": "input_policy",
                    "violations": input_result.violations,
                    "risk_score": input_result.risk_score,
                    "latency_ms": _elapsed_ms(pipeline_start),
                },
            }

        # ---- 2. Prompt registry lookup --------------------------------
        system_prompt = await self._get_system_prompt()

        # ---- 3. Semantic search for knowledge chunks ------------------
        knowledge_chunks = await self._semantic_search(
            query, tenant_id, context_filter
        )

        # ---- 4. Context assembly -------------------------------------
        conversation_history = await self._get_conversation_history(
            conversation_id
        )
        assembled = await self._context_assembler.assemble(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            knowledge_chunks=knowledge_chunks,
        )

        # ---- 5. Model routing ----------------------------------------
        model_config = await self._model_router.route(
            task_type="question_answering",
            tenant_id=tenant_id,
            context=context_filter,
        )

        # ---- 6. Anthropic API call (with tool-use loop) ---------------
        api_start = time.monotonic()
        response_text, tool_use_rounds = await self._call_anthropic(
            query=query,
            assembled_context=assembled,
            model_config_name=model_config.model_name,
            max_tokens=model_config.max_tokens,
            temperature=model_config.temperature,
        )
        telemetry["api_latency_ms"] = _elapsed_ms(api_start)
        telemetry["tool_use_rounds"] = tool_use_rounds
        telemetry["model"] = model_config.model_name

        # ---- 7. Output policy guard ----------------------------------
        output_result = await self._output_guard.check(response=response_text)
        if not output_result.allowed:
            logger.warning(
                "Output policy guard rejected response: %s",
                output_result.violations,
            )
            response_text = (
                "I generated a response but it was flagged by our safety "
                "system. Please try rephrasing your question."
            )
            telemetry["output_filtered"] = True
            telemetry["output_violations"] = output_result.violations

        # ---- 8. Telemetry --------------------------------------------
        telemetry["latency_ms"] = _elapsed_ms(pipeline_start)
        telemetry["context_utilization_pct"] = assembled.utilization_pct
        telemetry["context_budget"] = assembled.budget_breakdown
        self._record_telemetry(telemetry)

        # ---- 9. Build response dict ----------------------------------
        sources = self._extract_sources(knowledge_chunks)
        return {
            "response": response_text,
            "sources": sources,
            "conversation_id": conversation_id,
            "telemetry": telemetry,
        }

    # ------------------------------------------------------------------
    # Anthropic API interaction
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        query: str,
        assembled_context: AssembledContext,
        model_config_name: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        """Call the Anthropic API, handling tool-use rounds.

        Returns ``(response_text, tool_use_round_count)``.
        """
        api_key = self._settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.warning(
                "ANTHROPIC_API_KEY is not set — returning placeholder response."
            )
            return (
                "AI responses are currently unavailable because the Anthropic "
                "API key has not been configured. Please set the "
                "ANTHROPIC_API_KEY environment variable and try again.",
                0,
            )

        try:
            import anthropic
        except ImportError:
            logger.error("The 'anthropic' package is not installed.")
            return (
                "AI responses are currently unavailable because the Anthropic "
                "SDK is not installed. Please install it with: "
                "pip install anthropic",
                0,
            )

        client = anthropic.AsyncAnthropic(api_key=api_key)

        # Build initial messages.
        messages = self._build_anthropic_messages(
            query=query,
            assembled_context=assembled_context,
            tool_results=None,
        )

        # System prompt (assembled context includes knowledge).
        system_prompt = assembled_context.system_prompt
        if assembled_context.knowledge_context:
            system_prompt += (
                "\n\n## Relevant Context\n\n"
                + assembled_context.knowledge_context
            )

        # Tool definitions.
        tools = self._tool_coordinator.get_available_tools() or None

        tool_use_rounds = 0

        for _round in range(_MAX_TOOL_ROUNDS + 1):
            try:
                response = await client.messages.create(
                    model=model_config_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools if tools else anthropic.NOT_GIVEN,
                )
            except Exception as exc:
                logger.error("Anthropic API call failed: %s", exc, exc_info=True)
                return (
                    "I encountered an error while processing your request. "
                    "Please try again later.",
                    tool_use_rounds,
                )

            # Check if the model wants to use tools.
            if response.stop_reason == "tool_use":
                tool_use_rounds += 1

                # Extract tool_use blocks from the response.
                tool_use_blocks = [
                    block for block in response.content
                    if getattr(block, "type", None) == "tool_use"
                ]

                if not tool_use_blocks:
                    # Shouldn't happen, but handle defensively.
                    break

                # Build tool calls for the coordinator.
                tool_calls = []
                for block in tool_use_blocks:
                    # Tool names are formatted as "server__tool".
                    parts = block.name.split("__", 1)
                    if len(parts) == 2:
                        server_name, tool_name = parts
                    else:
                        server_name, tool_name = "unknown", block.name

                    tool_calls.append(
                        {
                            "server": server_name,
                            "tool": tool_name,
                            "arguments": block.input or {},
                        }
                    )

                # Execute tools in parallel.
                tool_results = await self._tool_coordinator.execute_tools(tool_calls)

                # Append the assistant's response (with tool_use blocks) to messages.
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            _content_block_to_dict(b) for b in response.content
                        ],
                    }
                )

                # Append tool results as a user message.
                tool_result_blocks = []
                for block, result in zip(tool_use_blocks, tool_results):
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(
                                result.get("result") or {"error": result.get("error", "Unknown error")}
                            ),
                            "is_error": not result.get("success", False),
                        }
                    )
                messages.append({"role": "user", "content": tool_result_blocks})

                # Continue the loop for next round.
                continue

            # No tool use — extract the text response.
            text_parts = [
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ]
            return "\n".join(text_parts) if text_parts else "", tool_use_rounds

        # Exhausted tool-use rounds — extract whatever text we have.
        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return (
            "\n".join(text_parts) if text_parts else "I was unable to complete the request within the allowed number of tool-use rounds.",
            tool_use_rounds,
        )

    # ------------------------------------------------------------------
    # Message building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_anthropic_messages(
        query: str,
        assembled_context: AssembledContext,
        tool_results: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Build the messages list for an Anthropic API call.

        Includes conversation history from the assembled context plus the
        current user query.
        """
        messages: list[dict[str, Any]] = []

        # Add conversation history (excluding system messages, which are
        # passed separately via the ``system`` parameter).
        for msg in assembled_context.messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            messages.append({"role": role, "content": msg.get("content", "")})

        # Add the current user query.
        messages.append({"role": "user", "content": query})

        return messages

    # ------------------------------------------------------------------
    # Source extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sources(knowledge_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract source metadata from knowledge chunks for the response."""
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()

        for chunk in knowledge_chunks:
            source_id = chunk.get("document_id") or chunk.get("source_id") or ""
            if source_id and source_id in seen:
                continue
            if source_id:
                seen.add(source_id)

            sources.append(
                {
                    "document_id": source_id,
                    "title": chunk.get("title", ""),
                    "relevance_score": chunk.get("relevance_score", 0.0),
                    "chunk_index": chunk.get("chunk_index"),
                }
            )

        return sources

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_system_prompt(self) -> str:
        """Retrieve the active system prompt, falling back to a default."""
        try:
            prompt_data = await self._prompt_registry.get_active_prompt(
                task_type="question_answering",
                model_family="anthropic",
            )
            return prompt_data.get("system_prompt", _FALLBACK_SYSTEM_PROMPT)
        except (ValueError, Exception) as exc:
            logger.info(
                "No active prompt found, using fallback: %s", exc
            )
            return _FALLBACK_SYSTEM_PROMPT

    async def _semantic_search(
        self,
        query: str,
        tenant_id: UUID,
        context_filter: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Perform semantic search for relevant knowledge chunks.

        This is a placeholder that returns an empty list until the
        semantic search module is wired in.
        """
        # TODO: Integrate with packages/search or a vector-store module.
        logger.debug(
            "Semantic search stub called for tenant %s, query length %d",
            tenant_id,
            len(query),
        )
        return []

    async def _get_conversation_history(
        self, conversation_id: str
    ) -> list[dict[str, Any]]:
        """Load conversation history for a given conversation ID.

        This is a placeholder that returns an empty list until
        conversation persistence is wired in.
        """
        # TODO: Load from database.
        logger.debug(
            "Conversation history stub called for %s", conversation_id
        )
        return []

    def _record_telemetry(self, telemetry: dict[str, Any]) -> None:
        """Record AI telemetry metrics.

        Attempts to use the observability metrics module if available,
        otherwise logs the telemetry data.
        """
        try:
            from packages.observability.metrics import record_ai_telemetry  # type: ignore[import-untyped]

            record_ai_telemetry(telemetry)
        except ImportError:
            logger.debug("Observability module not available; telemetry: %s", telemetry)
        except Exception:
            logger.warning("Failed to record AI telemetry", exc_info=True)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from ``time.monotonic``)."""
    return round((time.monotonic() - start) * 1000, 2)


def _content_block_to_dict(block: Any) -> dict[str, Any]:
    """Convert an Anthropic content block to a plain dict."""
    block_type = getattr(block, "type", "text")
    if block_type == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    elif block_type == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }
    else:
        # Fallback for unknown block types.
        return {"type": block_type}
