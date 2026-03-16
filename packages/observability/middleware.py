"""ASGI middleware for request tracing, correlation IDs, and duration tracking."""

from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable, MutableMapping, Optional

from packages.observability.logging import bind_context, clear_context, get_logger
from packages.observability.metrics import request_counter, request_latency

logger = get_logger(__name__)

# Type aliases following the ASGI 3.0 spec.
Scope = MutableMapping[str, Any]
Receive = Callable[..., Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_REQUEST_ID_HEADER = b"x-request-id"
_TRACE_ID_HEADER = b"x-trace-id"
_TENANT_ID_HEADER = b"x-tenant-id"


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> Optional[str]:
    """Return the decoded value of the first header matching *name*."""
    for key, value in headers:
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class RequestTracingMiddleware:
    """ASGI middleware that adds correlation context to every HTTP request.

    Responsibilities:
    * Generate ``X-Request-Id`` when absent.
    * Extract or generate ``X-Trace-Id``.
    * Extract ``X-Tenant-Id`` from upstream headers.
    * Bind all three IDs into the *structlog* context so every log line
      emitted during the request is automatically annotated.
    * Measure wall-clock request duration and record it via
      :data:`request_latency` / :data:`request_counter`.
    * Inject correlation headers into the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))

        request_id = _header_value(headers, _REQUEST_ID_HEADER) or uuid.uuid4().hex
        trace_id = _header_value(headers, _TRACE_ID_HEADER) or uuid.uuid4().hex
        tenant_id = _header_value(headers, _TENANT_ID_HEADER)

        # Bind IDs into structlog context for the duration of this request.
        bind_context(
            request_id=request_id,
            trace_id=trace_id,
            tenant_id=tenant_id,
        )

        logger.info(
            "request_started",
            method=scope.get("method", ""),
            path=scope.get("path", ""),
        )

        start = time.perf_counter()

        response_started = False
        status_code: Optional[int] = None

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            nonlocal response_started, status_code

            if message["type"] == "http.response.start":
                response_started = True
                status_code = message.get("status")

                # Inject correlation headers into the response.
                resp_headers: list[list[bytes]] = list(
                    message.get("headers", [])
                )
                resp_headers.append(
                    [_REQUEST_ID_HEADER, request_id.encode("latin-1")]
                )
                resp_headers.append(
                    [_TRACE_ID_HEADER, trace_id.encode("latin-1")]
                )
                message["headers"] = resp_headers

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            request_counter.inc()
            request_latency.observe(duration_ms)

            logger.info(
                "request_finished",
                method=scope.get("method", ""),
                path=scope.get("path", ""),
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
            )
            clear_context()
