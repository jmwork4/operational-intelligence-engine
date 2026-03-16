"""Observability package for the Operational Intelligence Engine.

Provides structured logging, distributed tracing, metrics helpers, and ASGI
middleware that ties them together.
"""

from packages.observability.logging import (
    bind_context,
    clear_context,
    get_logger,
    setup_logging,
)
from packages.observability.metrics import (
    AITelemetry,
    alerts_generated,
    events_ingested,
    record_ai_telemetry,
    request_counter,
    request_latency,
    rules_evaluated,
)
from packages.observability.middleware import RequestTracingMiddleware
from packages.observability.tracing import (
    get_tracer,
    init_tracing,
    shutdown_tracing,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    "bind_context",
    "clear_context",
    # Tracing
    "init_tracing",
    "get_tracer",
    "shutdown_tracing",
    # Metrics
    "AITelemetry",
    "record_ai_telemetry",
    "request_counter",
    "request_latency",
    "events_ingested",
    "rules_evaluated",
    "alerts_generated",
    # Middleware
    "RequestTracingMiddleware",
]
