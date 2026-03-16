FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS dependencies

COPY packages/common/pyproject.toml packages/common/
COPY packages/db/pyproject.toml packages/db/
COPY packages/schemas/pyproject.toml packages/schemas/
COPY packages/observability/pyproject.toml packages/observability/
COPY packages/storage/pyproject.toml packages/storage/
COPY packages/ai/pyproject.toml packages/ai/
COPY packages/events/pyproject.toml packages/events/
COPY packages/rules/pyproject.toml packages/rules/
COPY packages/domain/pyproject.toml packages/domain/
COPY apps/api/pyproject.toml apps/api/

RUN pip install --no-cache-dir -e packages/common -e packages/db \
    -e packages/schemas -e packages/observability -e packages/storage \
    -e packages/ai -e packages/events -e packages/rules -e packages/domain \
    -e apps/api

FROM dependencies AS development

COPY packages/ packages/
COPY apps/api/ apps/api/

RUN pip install --no-cache-dir debugpy

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM dependencies AS production

COPY packages/ packages/
COPY apps/api/ apps/api/

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
