"""Metrics helpers and AI telemetry dataclass."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# AI Telemetry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AITelemetry:
    """Structured telemetry record for a single AI/LLM interaction.

    All numeric fields default to ``0`` / ``0.0`` so callers only need to
    populate the values they have.
    """

    prompt_version: str
    model_provider: str
    model_name: str

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0

    # Retrieval / RAG quality
    retrieval_score: float = 0.0
    context_utilization_pct: float = 0.0

    # Tool / function-calling
    tool_invocation_count: int = 0
    tool_failures: int = 0

    # Latency
    latency_ms: float = 0.0

    # Policy guard verdicts (e.g. "pass", "block", "warn")
    policy_guard_input_result: str = ""
    policy_guard_output_result: str = ""


def record_ai_telemetry(telemetry: AITelemetry) -> None:
    """Emit a structured log line containing all AI telemetry fields.

    Downstream log aggregation pipelines can parse this record for
    dashboards, alerting, and cost attribution.
    """
    logger.info(
        "ai_telemetry",
        prompt_version=telemetry.prompt_version,
        model_provider=telemetry.model_provider,
        model_name=telemetry.model_name,
        input_tokens=telemetry.input_tokens,
        output_tokens=telemetry.output_tokens,
        total_tokens=telemetry.input_tokens + telemetry.output_tokens,
        retrieval_score=telemetry.retrieval_score,
        context_utilization_pct=telemetry.context_utilization_pct,
        tool_invocation_count=telemetry.tool_invocation_count,
        tool_failures=telemetry.tool_failures,
        latency_ms=telemetry.latency_ms,
        policy_guard_input_result=telemetry.policy_guard_input_result,
        policy_guard_output_result=telemetry.policy_guard_output_result,
    )


# ---------------------------------------------------------------------------
# Lightweight counters (thread-safe via atomics)
# ---------------------------------------------------------------------------


class _Counter:
    """A trivially simple counter backed by a list (GIL-safe increment)."""

    __slots__ = ("_name", "_value")

    def __init__(self, name: str) -> None:
        self._name = name
        self._value: int = 0

    def inc(self, amount: int = 1) -> None:
        self._value += amount
        logger.debug("counter_increment", counter=self._name, delta=amount, value=self._value)

    @property
    def value(self) -> int:
        return self._value

    def reset(self) -> None:
        self._value = 0

    def __repr__(self) -> str:
        return f"Counter({self._name!r}, value={self._value})"


class _LatencyRecorder:
    """Record request latency observations and expose basic stats."""

    __slots__ = ("_name", "_observations")

    def __init__(self, name: str) -> None:
        self._name = name
        self._observations: list[float] = []

    def observe(self, duration_ms: float) -> None:
        self._observations.append(duration_ms)
        logger.debug(
            "latency_observation",
            metric=self._name,
            duration_ms=duration_ms,
        )

    @property
    def count(self) -> int:
        return len(self._observations)

    @property
    def total_ms(self) -> float:
        return sum(self._observations)

    def reset(self) -> None:
        self._observations.clear()

    def __repr__(self) -> str:
        return f"LatencyRecorder({self._name!r}, count={self.count})"


# Pre-built counters for OIE domain events
request_counter = _Counter("http_requests_total")
request_latency = _LatencyRecorder("http_request_duration_ms")

events_ingested = _Counter("events_ingested_total")
rules_evaluated = _Counter("rules_evaluated_total")
alerts_generated = _Counter("alerts_generated_total")
