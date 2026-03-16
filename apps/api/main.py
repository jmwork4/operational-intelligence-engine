"""OIE API — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.common import (
    OIEBaseException,
    RateLimitExceededError,
    ResourceNotFoundError,
    TenantAccessDeniedError,
    ValidationError,
    get_settings,
)
from packages.db.session import get_async_engine, init_db
from packages.observability import (
    RequestTracingMiddleware,
    get_logger,
    init_tracing,
    setup_logging,
)
from packages.schemas import ErrorResponse, HealthResponse

from apps.api.middleware import TenantMiddleware
from apps.api.routes import ai, alerts, auth_routes, documents, events, rules, tenants

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Deprecation header helper
# ---------------------------------------------------------------------------

def add_deprecation_headers(
    response: JSONResponse,
    *,
    deprecation_date: str | None = None,
    sunset_date: str | None = None,
    link: str | None = None,
) -> JSONResponse:
    """Attach ``Deprecation`` and ``Sunset`` headers to a response.

    Parameters
    ----------
    response:
        The outgoing response object.
    deprecation_date:
        HTTP-date when the endpoint was deprecated (RFC 7231).
    sunset_date:
        HTTP-date when the endpoint will be removed (RFC 8594).
    link:
        URL to documentation for the replacement endpoint.
    """
    if deprecation_date:
        response.headers["Deprecation"] = deprecation_date
    if sunset_date:
        response.headers["Sunset"] = sunset_date
    if link:
        response.headers["Link"] = f'<{link}>; rel="successor-version"'
    return response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    settings = get_settings()

    # Logging
    setup_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
    logger.info("Starting OIE API", version="0.1.0", environment=settings.ENVIRONMENT)

    # Tracing
    init_tracing(
        service_name=settings.OTEL_SERVICE_NAME,
        otlp_endpoint=settings.OTEL_EXPORTER_ENDPOINT,
        environment=settings.ENVIRONMENT,
    )

    # Database
    init_db(settings.DATABASE_URL)
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.error("Database connection failed — startup continuing anyway")

    yield

    logger.info("Shutting down OIE API")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="OIE API",
    version="0.1.0",
    lifespan=lifespan,
)

# -- Middleware (order matters: outermost first) ---------------------------

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(TenantMiddleware)

# -- Routers ---------------------------------------------------------------

app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(documents.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai.router, prefix=settings.API_V1_PREFIX)
app.include_router(tenants.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_routes.router, prefix=settings.API_V1_PREFIX)


# -- Root health endpoint --------------------------------------------------

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Service health check."""
    s = get_settings()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=s.ENVIRONMENT,
    )


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            code=exc.code or "RATE_LIMIT_EXCEEDED",
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            code=exc.code or "RESOURCE_NOT_FOUND",
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(TenantAccessDeniedError)
async def tenant_access_denied_handler(request: Request, exc: TenantAccessDeniedError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            code=exc.code or "TENANT_ACCESS_DENIED",
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code=exc.code or "VALIDATION_ERROR",
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(OIEBaseException)
async def oie_base_handler(request: Request, exc: OIEBaseException) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=exc.code or "INTERNAL_ERROR",
            message=exc.message,
        ).model_dump(),
    )
