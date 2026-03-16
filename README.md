# Operational Intelligence Engine (OIE)

A multi-tenant platform for ingesting operational events, evaluating rules, generating alerts, retrieving contextual knowledge, and providing AI-assisted operational insights.

OIE serves as a foundational infrastructure layer capable of powering vertical SaaS products across logistics, healthcare operations, manufacturing, transportation orchestration, and enterprise operational monitoring.

---

## What It Does

**Event-Driven Intelligence** -- Ingest thousands of operational events per second from external systems, evaluate them against configurable rules in real time, and generate intelligent alerts when conditions are met.

**AI-Assisted Operations** -- Upload operational documents, perform semantic search via vector embeddings, and interact with an AI copilot that reasons over your operational data with full observability and deterministic prompt management.

**Multi-Tenant SaaS** -- Strict tenant isolation enforced at the PostgreSQL row-level security layer. Cross-tenant data access is impossible even if application logic fails.

---

## Architecture Overview

```
                         +------------------+
                         |   Next.js Web    |
                         |   (apps/web)     |
                         +--------+---------+
                                  |
                         +--------v---------+
                         |   FastAPI API    |
                         |   (apps/api)     |
                         |   Port 8000      |
                         +--+-----+-----+--+
                            |     |     |
              +-------------+     |     +-------------+
              |                   |                   |
     +--------v-------+  +-------v--------+  +-------v--------+
     |  ARQ Workers   |  |   APScheduler  |  |   MCP Tool     |
     |  (apps/workers)|  | (apps/scheduler)|  |   Servers      |
     +--------+-------+  +-------+--------+  +----------------+
              |                   |
     +--------v------------------v---------+
     |          Data Layer                 |
     |  PostgreSQL + pgvector  |  Redis    |
     |  MinIO (S3-compatible)             |
     +-------------------------------------+
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn, Python 3.12+ |
| Frontend | Next.js (planned) |
| Database | PostgreSQL 16 with pgvector extension |
| Cache / Queue | Redis 7 |
| Object Storage | MinIO (S3-compatible) |
| Background Jobs | ARQ (async Redis queue) |
| Scheduling | APScheduler with PostgreSQL job store |
| AI | Anthropic Claude, version-controlled prompts |
| Observability | OpenTelemetry, structlog, Grafana/Loki |
| Containerization | Docker Compose |
| Linting | Ruff (Python), Biome (TypeScript) |

---

## Project Structure

```
operational-intelligence-engine/
├── apps/
│   ├── api/                    # FastAPI application
│   │   ├── main.py             # App entrypoint, middleware, exception handlers
│   │   ├── auth.py             # JWT creation, password hashing (passlib/bcrypt)
│   │   ├── deps.py             # Dependency injection (DB, auth, rate limiting)
│   │   ├── middleware.py       # Tenant isolation middleware
│   │   └── routes/
│   │       ├── events.py       # POST/GET /api/v1/events
│   │       ├── rules.py        # CRUD /api/v1/rules
│   │       ├── alerts.py       # GET/acknowledge/resolve /api/v1/alerts
│   │       ├── documents.py    # Upload, search /api/v1/documents
│   │       ├── ai.py           # POST /api/v1/ai/query
│   │       ├── tenants.py      # Tenant management
│   │       └── auth_routes.py  # Login, registration
│   ├── workers/                # ARQ background workers
│   │   ├── main.py             # Worker settings and lifecycle
│   │   └── tasks/
│   │       ├── ingestion.py    # Event processing
│   │       ├── embedding.py    # Document embedding generation
│   │       ├── rule_evaluation.py  # Rule engine execution
│   │       ├── alerts.py       # Alert creation and deduplication
│   │       └── maintenance.py  # Lock cleanup, event archival
│   ├── scheduler/              # APScheduler service
│   │   ├── main.py             # Scheduler entrypoint with signal handling
│   │   ├── jobs.py             # Job definitions (enqueue-only, no business logic)
│   │   └── config.py           # Scheduler intervals and settings
│   ├── web/                    # Next.js frontend (planned)
│   └── mcp-*/                  # MCP tool servers (planned)
│
├── packages/
│   ├── common/                 # Shared foundation
│   │   ├── settings.py         # Pydantic Settings (DB, Redis, S3, JWT, AI, rate limits)
│   │   ├── tenant_context.py   # ContextVar-based tenant management + RLS SQL
│   │   ├── exceptions.py       # Exception hierarchy (8 exception types)
│   │   ├── types.py            # Enums and type aliases
│   │   └── utils.py            # UUID generation, timestamps, trace IDs
│   ├── db/                     # Database layer
│   │   ├── base.py             # SQLAlchemy 2.0 DeclarativeBase + mixins
│   │   ├── session.py          # Async engine, session factory, RLS execution
│   │   ├── rls.py              # Row-Level Security policy generation
│   │   ├── models/             # 16 SQLAlchemy models
│   │   └── migrations/         # Alembic (compare_type + compare_server_default)
│   ├── schemas/                # Pydantic v2 API schemas
│   ├── ai/                     # AI services
│   │   ├── prompt_registry.py  # Version-controlled prompt management
│   │   ├── policy_guard.py     # Input/Output policy enforcement
│   │   ├── context_assembly.py # Token budget allocation and context building
│   │   └── model_router.py     # Model selection and routing
│   ├── observability/          # Telemetry
│   │   ├── tracing.py          # OpenTelemetry with OTLP export
│   │   ├── logging.py          # structlog with JSON/console output
│   │   ├── metrics.py          # AI telemetry capture
│   │   └── middleware.py       # Request tracing ASGI middleware
│   └── storage/                # Object storage abstraction
│       ├── adapter.py          # StorageAdapter ABC
│       ├── s3.py               # S3Adapter (aiobotocore)
│       ├── minio.py            # MinIOAdapter (path-style addressing)
│       └── factory.py          # get_storage_adapter() factory
│
├── docker-compose.yml          # Production-like services
├── docker-compose.override.yml # Dev overrides (hot reload, pgAdmin, Redis Commander)
├── pyproject.toml              # Monorepo config (Ruff, pytest, mypy)
├── .pre-commit-config.yaml     # Pre-commit hooks
└── biome.json                  # TypeScript/Next.js linting
```

---

## Core Features

### Event Ingestion

Events represent operational activity from external systems. Each event includes type, entity reference, source system, JSON payload, and timestamps.

```
POST /api/v1/events
{
  "event_type": "shipment_delayed",
  "entity_type": "shipment",
  "entity_id": "SHP-2024-001",
  "source_system": "tms",
  "payload": {"delay_minutes": 45, "reason": "traffic"},
  "metadata": {"vendor_priority": "high"}
}
```

Supported event types: `shipment_dispatched`, `shipment_delayed`, `delivery_completed`, `driver_checkin`, `inventory_received`, `vehicle_status_changed`, `route_deviated`, `vendor_delay`, `order_created`, `order_updated`, `custom`

### Rule Engine

Three rule types evaluate operational conditions and generate alerts:

**Event-Triggered Rules** -- Fire immediately when matching events arrive.
```
event.delay_minutes > 30 AND event.vendor_priority == "high"
```

**Threshold Rules** -- Evaluate metrics over sliding time windows (e.g., temperature > threshold for 10 minutes). Evaluated on configurable intervals via the scheduler.

**Composite Rules** -- Correlate multiple events across time windows (e.g., 3 vendor failures AND delayed shipment AND inventory risk). State tracked in Redis (short-window) and PostgreSQL (long-window).

Rules use a deterministic expression engine. Dynamic execution methods (`eval`, `exec`) are never used.

### Alert System

Alerts are generated when rule conditions are satisfied, with built-in deduplication:

- Deduplication key: `tenant_id` + `rule_id` + `entity_id` + `evaluation_window`
- Severity levels: `low`, `medium`, `high`, `critical`
- Statuses: `active` -> `acknowledged` -> `resolved` (or `suppressed`)

### Knowledge Management

Upload operational documents for AI-powered semantic search:

1. Documents stored in S3-compatible object storage (MinIO)
2. Processed into text chunks
3. Each chunk receives vector embeddings (1536 dimensions)
4. Stored in PostgreSQL via pgvector
5. Semantic search retrieves relevant knowledge during AI reasoning

### AI Copilot

Every AI request follows a secure, observable pipeline:

```
User Query
    -> Input Policy Guard (injection detection, permissions)
    -> Context Assembly (token budgets, knowledge retrieval)
    -> Model Router (provider selection)
    -> Model Invocation
    -> Output Policy Guard (PII detection, compliance)
    -> Response
```

**Context Assembly Token Budgets:**

| Section | Allocation |
|---|---|
| System Prompt | 15% |
| Conversation History | 15% |
| Knowledge Retrieval | 40% |
| Tool Results | 20% |
| Reserve | 10% |

**Policy Guards detect:**
- Prompt injection patterns (8 regex patterns)
- PII leakage (SSN, credit cards, emails, phone numbers)
- Policy violations and unsupported claims
- Sensitive document exposure

### Prompt Registry

All AI prompts are version-controlled in the database. Hardcoded prompts are not permitted.

- Prompts associated with evaluation datasets
- Evaluation types: `exact_match`, `semantic_match`, `policy_compliance`, `tool_usage_validation`
- Prompts cannot be promoted to active if evaluations fall below threshold (80%)
- Automatic regression detection on version changes

---

## Multi-Tenant Security

Tenant isolation is enforced at the PostgreSQL database layer using Row-Level Security (RLS).

**How it works:**

1. Every tenant-scoped table includes a `tenant_id` column
2. API middleware sets the session variable on every request:
   ```sql
   SET app.current_tenant_id = '<tenant_uuid>'
   ```
3. RLS policies enforce row access on all operations (SELECT, INSERT, UPDATE, DELETE):
   ```sql
   current_setting('app.current_tenant_id')::uuid = tenant_id
   ```

**11 tenant-isolated tables:** `users`, `events`, `resources`, `processes`, `transactions`, `rules`, `alerts`, `documents`, `document_chunks`, `embeddings`, `audit_logs`

Cross-tenant data access is impossible even if application logic fails.

---

## Database Models

| Model | Purpose |
|---|---|
| `Tenant` | Organization accounts with plan tiers |
| `User` | Tenant members with roles and auth |
| `Event` | Central operational event log |
| `Resource` | Tracked operational resources (vehicles, warehouses) |
| `Process` | Operational processes and workflows |
| `Transaction` | Financial/operational transactions |
| `Rule` | Configurable evaluation rules |
| `Alert` | Generated alerts with deduplication |
| `Document` | Uploaded operational documents |
| `DocumentChunk` | Processed text chunks for retrieval |
| `Embedding` | pgvector embeddings (1536 dimensions) |
| `PromptTemplate` | Version-controlled AI prompts |
| `PromptEvaluation` | Prompt regression test datasets |
| `AuditLog` | Full audit trail |
| `TaskExecutionLock` | Distributed task locking |

---

## API Endpoints

All endpoints are versioned under `/api/v1/`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/v1/auth/login` | Authenticate, receive JWT |
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/events` | Ingest single event |
| `POST` | `/api/v1/events/batch` | Ingest event batch |
| `GET` | `/api/v1/events` | List events (filterable) |
| `GET` | `/api/v1/events/{id}` | Get event by ID |
| `POST` | `/api/v1/rules` | Create rule |
| `GET` | `/api/v1/rules` | List rules |
| `GET` | `/api/v1/rules/{id}` | Get rule |
| `PATCH` | `/api/v1/rules/{id}` | Update rule |
| `DELETE` | `/api/v1/rules/{id}` | Disable rule |
| `GET` | `/api/v1/alerts` | List alerts (filterable) |
| `GET` | `/api/v1/alerts/{id}` | Get alert |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| `POST` | `/api/v1/alerts/{id}/resolve` | Resolve alert |
| `POST` | `/api/v1/documents` | Upload document |
| `GET` | `/api/v1/documents` | List documents |
| `GET` | `/api/v1/documents/{id}` | Get document |
| `DELETE` | `/api/v1/documents/{id}` | Delete document |
| `POST` | `/api/v1/documents/search` | Semantic search |
| `POST` | `/api/v1/ai/query` | AI copilot query |
| `POST` | `/api/v1/tenants` | Create tenant (admin) |
| `GET` | `/api/v1/tenants/{id}` | Get tenant |

**Rate Limiting** (per tenant, per minute):
- Basic tier: 60 requests
- Professional tier: 300 requests
- Enterprise tier: 1,000 requests

Exceeded limits return HTTP `429` with `Retry-After` header.

**API Versioning:** URI-based (`/api/v1/`). Deprecated versions return `Deprecation` and `Sunset` headers and remain supported for 12 months.

---

## Background Workers

ARQ workers process 11 async task types via Redis queues:

| Task | Purpose |
|---|---|
| `process_event` | Process a single ingested event |
| `batch_process_events` | Process event batches |
| `generate_embeddings` | Generate vector embeddings for document chunks |
| `reindex_document` | Regenerate all embeddings for a document |
| `evaluate_event_rules` | Evaluate event-triggered rules |
| `evaluate_threshold_rules` | Evaluate threshold rules over time windows |
| `evaluate_composite_rules` | Evaluate composite correlated rules |
| `create_alert` | Create and deduplicate alerts |
| `send_notification` | Dispatch alert notifications |
| `cleanup_expired_locks` | Remove expired task execution locks |
| `archive_old_events` | Archive events older than 90 days |

Worker config: 5 concurrent jobs, 0.5s poll delay, 10-minute job timeout.

---

## Scheduler

APScheduler with PostgreSQL job store runs 4 scheduled jobs. The scheduler only enqueues work to ARQ -- it never executes business logic directly.

| Job | Schedule |
|---|---|
| Threshold rule evaluation | Every 60 seconds |
| Composite rule evaluation | Every 5 minutes |
| Lock cleanup | Every 10 minutes |
| Event archival | Daily at 2:00 AM |

---

## Observability

**Tracing:** OpenTelemetry with OTLP gRPC export (falls back to console in dev). Every request gets a trace ID, request ID, and tenant ID bound to the context.

**Logging:** structlog with JSON output in production, colored console in development. Correlation IDs flow through all log entries.

**AI Telemetry** captures per-request:
- Prompt version, model provider, model name
- Input/output token counts
- Retrieval scores, context utilization percentage
- Tool invocation count and failures
- Latency (ms)
- Policy guard results (input and output)

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- Node.js 18+ (for frontend, when implemented)

### Quick Start

```bash
# Clone the repository
git clone git@github.com:jmwork4/operational-intelligence-engine.git
cd operational-intelligence-engine

# Start infrastructure services
docker compose up -d postgres redis minio

# Copy environment template
cp .env.example .env  # Edit with your values

# Install Python dependencies (from monorepo root)
pip install -e packages/common -e packages/db -e packages/schemas \
  -e packages/observability -e packages/storage -e packages/ai \
  -e apps/api -e apps/workers -e apps/scheduler

# Run database migrations
cd packages/db && alembic upgrade head && cd ../..

# Start the API (development mode)
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# Start workers (separate terminal)
python -m apps.workers.main

# Start scheduler (separate terminal)
python -m apps.scheduler.main
```

### Docker Compose (Full Stack)

```bash
# Start everything
docker compose up -d

# With dev tools (pgAdmin on :5050, Redis Commander on :8081)
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### Service Ports

| Service | Port | Purpose |
|---|---|---|
| API | 8000 | FastAPI application |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache and queues |
| MinIO API | 9000 | Object storage |
| MinIO Console | 9001 | MinIO web UI |
| pgAdmin | 5050 | Database management (dev) |
| Redis Commander | 8081 | Redis inspection (dev) |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://oie:oie_password@localhost:5432/oie` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | S3/MinIO endpoint |
| `S3_ACCESS_KEY` | `minioadmin` | S3 access key |
| `S3_SECRET_KEY` | `minioadmin123` | S3 secret key |
| `S3_BUCKET_NAME` | `oie-documents` | Document storage bucket |
| `ENVIRONMENT` | `dev` | Runtime environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration |
| `DEFAULT_MODEL_PROVIDER` | `anthropic` | AI model provider |
| `DEFAULT_MODEL_NAME` | `claude-sonnet-4-20250514` | AI model name |
| `MAX_CONTEXT_TOKENS` | `128000` | Max AI context window |
| `OTEL_SERVICE_NAME` | `oie-api` | OpenTelemetry service name |
| `OTEL_EXPORTER_ENDPOINT` | `None` | OTLP collector endpoint |

---

## Development

### Code Quality

```bash
# Python linting and formatting
ruff check .
ruff format .

# TypeScript linting (when frontend is added)
npx biome check .

# Pre-commit hooks (runs automatically on commit)
pre-commit install
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=packages --cov=apps --cov-report=term-missing

# Run by marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

Coverage minimum: 80% (enforced in pyproject.toml).

### Database Migrations

```bash
cd packages/db

# Generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Alembic is configured with `compare_type=True` and `compare_server_default=True` for accurate schema diffing.

---

## Target Customer

**Initial vertical:** Mid-size logistics companies operating 50-200 vehicles.

**Operational challenges solved:**
- Late shipment detection and alerting
- Driver dispatch coordination
- Vendor delay tracking
- Inventory timing optimization

**Typical event flow:**
```
shipment_dispatched -> shipment_delayed -> delivery_completed
driver_checkin -> route_deviated
inventory_received -> vendor_delay
```

---

## Business Model

| Tier | Price | AI Requests/min |
|---|---|---|
| Small Operations | ~$50/mo | 60 |
| Mid-Size Operations | ~$200/mo | 300 |
| Enterprise | Custom | 1,000+ |

Revenue streams: SaaS subscriptions, enterprise licensing, vertical SaaS products, operational analytics services.

---

## Build Phases

- [x] **Phase 1: Foundations** -- Tenant isolation, Prompt Registry, Policy Guards, Context Assembly, Scheduler, Workers, Storage, Observability, Linting, Migrations
- [ ] **Phase 2: Core Engine** -- Event ingestion, Rule evaluation, Alert system, Document ingestion, Embedding pipeline, Semantic retrieval
- [ ] **Phase 3: AI Layer** -- MCP integration, AI copilot interface, Tool orchestration, AI observability dashboards

---

## License

Proprietary. All rights reserved.
