FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS dependencies

COPY packages/common/pyproject.toml packages/common/
COPY packages/db/pyproject.toml packages/db/
COPY packages/observability/pyproject.toml packages/observability/
COPY apps/scheduler/pyproject.toml apps/scheduler/

RUN pip install --no-cache-dir -e packages/common -e packages/db \
    -e packages/observability -e apps/scheduler

FROM dependencies AS development

COPY packages/ packages/
COPY apps/scheduler/ apps/scheduler/

RUN pip install --no-cache-dir debugpy

CMD ["python", "-m", "apps.scheduler.main"]

FROM dependencies AS production

COPY packages/ packages/
COPY apps/scheduler/ apps/scheduler/

CMD ["python", "-m", "apps.scheduler.main"]
