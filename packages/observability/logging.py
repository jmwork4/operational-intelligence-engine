"""Structured logging configuration using *structlog*."""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor


# ---------------------------------------------------------------------------
# Custom processors
# ---------------------------------------------------------------------------

def _add_correlation_id(
    _logger: Any, _method: str, event_dict: EventDict
) -> EventDict:
    """Inject correlation IDs from the structlog context if present."""
    # These keys are bound via middleware or manual calls to
    # ``structlog.contextvars.bind_contextvars``.  The processor is a no-op
    # when they are absent.
    return event_dict


def _add_caller_info(
    _logger: Any, _method: str, event_dict: EventDict
) -> EventDict:
    """Attach caller filename and line number."""
    record: Optional[logging.LogRecord] = event_dict.get("_record")
    if record is not None:
        event_dict["caller"] = f"{record.pathname}:{record.lineno}"
    return event_dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(
    log_level: str = "INFO",
    environment: str = "dev",
) -> None:
    """Configure *structlog* for the application.

    Args:
        log_level: Root log level (e.g. ``"DEBUG"``, ``"INFO"``).
        environment: ``"production"`` selects JSON rendering; anything else
            uses a human-readable coloured console renderer.
    """
    is_production = environment.lower() == "production"

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_correlation_id,
        _add_caller_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
        context_class=dict,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a *structlog* bound logger for *name*."""
    return structlog.get_logger(name)


def bind_context(
    *,
    tenant_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Bind well-known correlation fields into the structlog context.

    This is safe to call from middleware, background workers, or anywhere a
    per-request / per-task context should be established.
    """
    ctx: dict[str, Any] = {}
    if tenant_id is not None:
        ctx["tenant_id"] = tenant_id
    if trace_id is not None:
        ctx["trace_id"] = trace_id
    if request_id is not None:
        ctx["request_id"] = request_id
    ctx.update(extra)
    structlog.contextvars.bind_contextvars(**ctx)


def clear_context() -> None:
    """Remove all bound context variables (call at the end of a request)."""
    structlog.contextvars.clear_contextvars()
