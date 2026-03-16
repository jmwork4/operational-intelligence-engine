"""Context Assembly — builds a token-budgeted context window for LLM calls.

The assembler allocates a fixed percentage of the total token budget to each
section (system prompt, conversation history, knowledge retrieval, tool
results) and truncates or prunes content to fit within those budgets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AssembledContext:
    """The fully assembled, token-budgeted context ready for an LLM call."""

    system_prompt: str
    messages: list[dict[str, Any]]
    knowledge_context: str
    tool_context: str | None
    total_tokens: int
    utilization_pct: float
    budget_breakdown: dict[str, int]


class ContextAssembler:
    """Assembles and truncates LLM context to fit within a token budget.

    Parameters
    ----------
    max_tokens:
        Maximum number of tokens the assembled context may occupy.
    """

    # Budget allocation as a fraction of *max_tokens*.
    SYSTEM_PROMPT_PCT: float = 0.15
    CONVERSATION_HISTORY_PCT: float = 0.15
    KNOWLEDGE_RETRIEVAL_PCT: float = 0.40
    TOOL_RESULTS_PCT: float = 0.20
    RESERVE_PCT: float = 0.10

    def __init__(self, max_tokens: int = 128_000) -> None:
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assemble(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, Any]],
        knowledge_chunks: list[dict[str, Any]],
        tool_results: list[dict[str, Any]] | None = None,
    ) -> AssembledContext:
        """Build an :class:`AssembledContext` that fits within the token budget.

        Parameters
        ----------
        system_prompt:
            The system-level instruction text.
        conversation_history:
            List of message dicts (``{"role": ..., "content": ...}``).
        knowledge_chunks:
            List of retrieval results, each containing at least ``"text"``
            and optionally ``"relevance_score"``.
        tool_results:
            Optional list of tool output dicts, each containing ``"tool_name"``
            and ``"output"``.
        """
        budgets = self._allocate_budgets()

        # 1. System prompt — truncate if it exceeds its budget.
        truncated_system = self._truncate_to_budget(
            system_prompt, budgets["system_prompt"]
        )

        # 2. Conversation history — prune oldest messages first.
        pruned_messages = self._prune_conversation_history(
            conversation_history, budgets["conversation_history"]
        )

        # 3. Knowledge chunks — rank by relevance and truncate.
        ranked_chunks = self._rank_and_truncate_knowledge(
            knowledge_chunks, budgets["knowledge_retrieval"]
        )
        knowledge_text = "\n\n---\n\n".join(
            chunk["text"] for chunk in ranked_chunks
        )
        knowledge_text = self._truncate_to_budget(
            knowledge_text, budgets["knowledge_retrieval"]
        )

        # 4. Tool results — concatenate and truncate.
        tool_text: str | None = None
        if tool_results:
            raw_tool = "\n\n".join(
                f"[{tr.get('tool_name', 'unknown')}]\n{tr.get('output', '')}"
                for tr in tool_results
            )
            tool_text = self._truncate_to_budget(
                raw_tool, budgets["tool_results"]
            )

        # Compute totals.
        total_tokens = (
            self._estimate_tokens(truncated_system)
            + sum(
                self._estimate_tokens(m.get("content", ""))
                for m in pruned_messages
            )
            + self._estimate_tokens(knowledge_text)
            + (self._estimate_tokens(tool_text) if tool_text else 0)
        )
        utilization_pct = round(
            (total_tokens / self.max_tokens) * 100, 1
        ) if self.max_tokens else 0.0

        breakdown = {
            "system_prompt": self._estimate_tokens(truncated_system),
            "conversation_history": sum(
                self._estimate_tokens(m.get("content", ""))
                for m in pruned_messages
            ),
            "knowledge_retrieval": self._estimate_tokens(knowledge_text),
            "tool_results": self._estimate_tokens(tool_text) if tool_text else 0,
            "reserve": budgets["reserve"],
        }

        return AssembledContext(
            system_prompt=truncated_system,
            messages=pruned_messages,
            knowledge_context=knowledge_text,
            tool_context=tool_text,
            total_tokens=total_tokens,
            utilization_pct=utilization_pct,
            budget_breakdown=breakdown,
        )

    # ------------------------------------------------------------------
    # Budget helpers
    # ------------------------------------------------------------------

    def _allocate_budgets(self) -> dict[str, int]:
        """Return per-section token budgets derived from *max_tokens*."""
        return {
            "system_prompt": int(self.max_tokens * self.SYSTEM_PROMPT_PCT),
            "conversation_history": int(
                self.max_tokens * self.CONVERSATION_HISTORY_PCT
            ),
            "knowledge_retrieval": int(
                self.max_tokens * self.KNOWLEDGE_RETRIEVAL_PCT
            ),
            "tool_results": int(self.max_tokens * self.TOOL_RESULTS_PCT),
            "reserve": int(self.max_tokens * self.RESERVE_PCT),
        }

    # ------------------------------------------------------------------
    # Truncation / pruning
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_to_budget(text: str, max_tokens: int) -> str:
        """Truncate *text* so its estimated token count does not exceed *max_tokens*.

        Uses a simple ``len(text) // 4`` token estimator, so the character
        cutoff is ``max_tokens * 4``.
        """
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars]

    @staticmethod
    def _prune_conversation_history(
        messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Keep the most recent messages that fit within *max_tokens*.

        System messages are never removed.  Oldest non-system messages are
        dropped first.
        """
        estimate = lambda t: len(t) // 4  # noqa: E731

        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        # Token budget consumed by system messages (always included).
        system_tokens = sum(
            estimate(m.get("content", "")) for m in system_msgs
        )
        remaining = max_tokens - system_tokens
        if remaining <= 0:
            return system_msgs

        # Walk from newest to oldest, accumulating until budget is exhausted.
        kept: list[dict[str, Any]] = []
        for msg in reversed(non_system):
            msg_tokens = estimate(msg.get("content", ""))
            if msg_tokens <= remaining:
                kept.append(msg)
                remaining -= msg_tokens
            else:
                break  # no room for older messages

        # Restore chronological order.
        kept.reverse()
        return system_msgs + kept

    @staticmethod
    def _rank_and_truncate_knowledge(
        chunks: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Sort *chunks* by ``relevance_score`` (descending) and keep those
        that fit within *max_tokens*.
        """
        estimate = lambda t: len(t) // 4  # noqa: E731

        sorted_chunks = sorted(
            chunks,
            key=lambda c: c.get("relevance_score", 0.0),
            reverse=True,
        )

        kept: list[dict[str, Any]] = []
        used = 0
        for chunk in sorted_chunks:
            tokens = estimate(chunk.get("text", ""))
            if used + tokens <= max_tokens:
                kept.append(chunk)
                used += tokens
            else:
                break
        return kept

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: 1 token per 4 characters."""
        return len(text) // 4
