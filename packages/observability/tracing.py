"""OpenTelemetry tracing setup for the Operational Intelligence Engine."""

from __future__ import annotations

import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import NoOpTracer, Tracer

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None


def init_tracing(
    service_name: str,
    *,
    otlp_endpoint: Optional[str] = None,
    environment: Optional[str] = None,
    insecure: bool = True,
) -> TracerProvider:
    """Initialise OpenTelemetry tracing with an OTLP exporter.

    Falls back to a console exporter when the OTLP endpoint is unreachable or
    not configured, so local development never breaks.

    Args:
        service_name: Logical name of the service (e.g. ``"oie-api"``).
        otlp_endpoint: gRPC endpoint for the OTLP collector.  Defaults to
            ``OTEL_EXPORTER_OTLP_ENDPOINT`` env-var, then ``"localhost:4317"``.
        environment: Deployment environment label (``"dev"``, ``"staging"``,
            ``"production"``).  Defaults to ``DEPLOYMENT_ENVIRONMENT`` env-var,
            then ``"dev"``.
        insecure: Whether to use an insecure gRPC channel.  Defaults to
            ``True``.

    Returns:
        The configured :class:`TracerProvider`.
    """
    global _tracer_provider  # noqa: PLW0603

    resolved_endpoint = otlp_endpoint or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"
    )
    resolved_env = environment or os.getenv("DEPLOYMENT_ENVIRONMENT", "dev")

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": resolved_env,
        }
    )

    provider = TracerProvider(resource=resource)

    # Attempt to configure the OTLP gRPC exporter; fall back to console.
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        otlp_exporter = OTLPSpanExporter(
            endpoint=resolved_endpoint,
            insecure=insecure,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "OTLP span exporter configured (endpoint=%s)", resolved_endpoint
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "OTLP exporter unavailable; falling back to ConsoleSpanExporter. "
            "Install opentelemetry-exporter-otlp-proto-grpc for production use."
        )
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str) -> Tracer:
    """Return a tracer bound to *name*.

    If :func:`init_tracing` has not been called yet a :class:`NoOpTracer` is
    returned so that instrumentation never raises at import time.
    """
    if _tracer_provider is None:
        return NoOpTracer()
    return _tracer_provider.get_tracer(name)


def shutdown_tracing() -> None:
    """Flush pending spans and shut down the tracer provider."""
    global _tracer_provider  # noqa: PLW0603
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None
