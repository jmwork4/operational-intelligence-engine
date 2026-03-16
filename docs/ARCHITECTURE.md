# OIE System Architecture

This document describes the complete architecture of the Operational Intelligence Engine, how each component interacts, and the design decisions behind the system.

---

## System Overview

OIE is a modular, event-driven, multi-tenant platform built as a monorepo. It consists of three application services, nine shared packages, and three infrastructure services, all orchestrated via Docker Compose.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│                                                                         │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│   │  Next.js Web │    │  Mobile App  │    │  External Systems (TMS,  │  │
│   │  (apps/web)  │    │  (planned)   │    │  ERP, IoT, Webhooks)     │  │
│   └──────┬───────┘    └──────┬───────┘    └────────────┬─────────────┘  │
│          │                   │                         │                │
└──────────┼───────────────────┼─────────────────────────┼────────────────┘
           │                   │                         │
           ▼                   ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                      │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    FastAPI Application                          │   │
│   │                    (apps/api) :8000                             │   │
│   │                                                                 │   │
│   │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐   │   │
│   │  │  CORS   │─▶│ Tracing  │─▶│  Tenant   │─▶│  Rate Limit  │   │   │
│   │  │Middleware│  │Middleware│  │Middleware  │  │  (per-tenant) │   │   │
│   │  └─────────┘  └──────────┘  └───────────┘  └──────────────┘   │   │
│   │                                                                 │   │
│   │  Routes:                                                        │   │
│   │  ┌─────────┐ ┌──────┐ ┌───────┐ ┌─────┐ ┌────┐ ┌──────────┐  │   │
│   │  │ /events │ │/rules│ │/alerts│ │/docs│ │/ai │ │/auth     │  │   │
│   │  └─────────┘ └──────┘ └───────┘ └─────┘ └────┘ └──────────┘  │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────┬──────────────────────┬──────────────────┬──────────────────┘
             │                      │                  │
             ▼                      ▼                  ▼
┌─────────────────────┐ ┌────────────────────┐ ┌─────────────────────────┐
│   ASYNC EXECUTION   │ │    SCHEDULER       │ │    AI SERVICES          │
│                     │ │                    │ │                         │
│  ┌───────────────┐  │ │  ┌──────────────┐  │ │  ┌───────────────────┐  │
│  │  ARQ Workers  │  │ │  │ APScheduler  │  │ │  │ Input Policy Guard│  │
│  │ (apps/workers)│  │ │  │(apps/scheduler│  │ │  ├───────────────────┤  │
│  │               │  │ │  │              │  │ │  │ Prompt Registry   │  │
│  │ • ingestion   │  │ │  │ Jobs:        │  │ │  ├───────────────────┤  │
│  │ • embedding   │  │ │  │ • threshold  │  │ │  │ Context Assembly  │  │
│  │ • rule_eval   │  │ │  │ • composite  │  │ │  ├───────────────────┤  │
│  │ • alerts      │  │ │  │ • cleanup    │  │ │  │ Model Router      │  │
│  │ • maintenance │  │ │  │ • archival   │  │ │  ├───────────────────┤  │
│  └───────┬───────┘  │ │  └──────┬───────┘  │ │  │Output Policy Guard│  │
│          │          │ │         │          │ │  └───────────────────┘  │
└──────────┼──────────┘ └─────────┼──────────┘ └─────────────────────────┘
           │                      │
           ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                     │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │   PostgreSQL 16  │  │   Redis 7    │  │   MinIO                │    │
│  │   + pgvector     │  │              │  │   (S3-compatible)      │    │
│  │                  │  │              │  │                        │    │
│  │  • 16 models     │  │  • Job queue │  │  • Document files     │    │
│  │  • RLS policies  │  │  • Rate limit│  │  • Presigned URLs     │    │
│  │  • Vector search │  │  • Rule state│  │                        │    │
│  │  • Job store     │  │  • Cache     │  │                        │    │
│  │  • Audit logs    │  │              │  │                        │    │
│  └──────────────────┘  └──────────────┘  └────────────────────────┘    │
│       :5432                :6379             :9000 / :9001             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dives

### 1. API Layer (`apps/api/`)

The FastAPI application is the system's single entry point for all client interactions. It handles authentication, tenant isolation, rate limiting, and request routing.

**Request Lifecycle:**

```
HTTP Request
  │
  ├── CORSMiddleware          Validates origin headers
  ├── RequestTracingMiddleware Assigns request_id, trace_id, binds structlog context
  ├── TenantMiddleware         Extracts tenant_id from JWT, sets TenantContext
  │
  ├── Route Handler
  │   ├── Depends(get_db)           Async SQLAlchemy session
  │   ├── Depends(get_current_tenant) Verifies JWT, executes SET app.current_tenant_id
  │   ├── Depends(RateLimiter)      Redis counter check (per tenant, per endpoint, per minute)
  │   └── Business Logic            Query/mutate via SQLAlchemy
  │
  └── Exception Handlers
      ├── RateLimitExceededError  → 429
      ├── ResourceNotFoundError  → 404
      ├── TenantAccessDeniedError → 403
      ├── ValidationError        → 422
      └── OIEBaseException       → 500
```

**Auth-Free Paths** (skip tenant middleware): `/`, `/docs`, `/openapi.json`, `/redoc`, `/api/v1/auth/*`

**Rate Limiting Implementation:**
```
Key:    rate_limit:{tenant_id}:{endpoint}:{minute_bucket}
TTL:    60 seconds
Action: INCR + compare against tier limit
Result: 429 with Retry-After header if exceeded
```

---

### 2. Multi-Tenant Security Model

This is the most critical architectural decision. Tenant isolation is enforced at the database layer, not the application layer, making cross-tenant access impossible even if application code has bugs.

**Three-Layer Enforcement:**

```
Layer 1: JWT Middleware
  │  Extracts tenant_id from token claims
  │  Sets contextvars.ContextVar for the request scope
  │
Layer 2: SQLAlchemy Session Hook
  │  Executes: SET app.current_tenant_id = '<uuid>'
  │  Runs before any query in the session
  │
Layer 3: PostgreSQL Row-Level Security
     Every tenant-scoped table has 4 RLS policies:
     ┌─ SELECT: WHERE current_setting('app.current_tenant_id')::uuid = tenant_id
     ├─ INSERT: WITH CHECK (current_setting('app.current_tenant_id')::uuid = tenant_id)
     ├─ UPDATE: WHERE + WITH CHECK on tenant_id
     └─ DELETE: WHERE current_setting('app.current_tenant_id')::uuid = tenant_id
```

**Tenant-Scoped Tables (11):**
`users`, `events`, `resources`, `processes`, `transactions`, `rules`, `alerts`, `documents`, `document_chunks`, `embeddings`, `audit_logs`

**Non-Tenant Tables (4):**
`tenants` (root table), `prompt_templates`, `prompt_evaluations`, `task_execution_locks`

---

### 3. Event Processing Pipeline

Events are the central data primitive. Everything in OIE originates from events.

```
External System
  │
  ▼
POST /api/v1/events
  │
  ├── Validate (Pydantic EventCreate schema)
  ├── Assign trace_id, ingested_at timestamp
  ├── INSERT into events table (with RLS)
  ├── Enqueue to ARQ: process_event(event_data)
  │
  ▼
ARQ Worker: process_event
  │
  ├── Append to Redis stream (for real-time consumers)
  ├── Match against event-triggered rules
  │   ├── Load active rules WHERE trigger_event matches
  │   ├── Evaluate condition_expression against event payload
  │   └── If condition TRUE → enqueue create_alert
  │
  └── Done

Batch ingestion (POST /api/v1/events/batch):
  Same flow, but bulk INSERT + individual enqueue per event
```

**Target Throughput:**
- MVP: 500-1,000 events/second
- Scale path: Dedicated ingestion service, batch writes, partitioned tables, reduced indexing

---

### 4. Rule Engine Architecture

The rule engine is the decision-making core. It evaluates three types of rules without ever executing arbitrary code.

```
┌──────────────────────────────────────────────────────────┐
│                    RULE ENGINE                            │
│                                                          │
│  ┌─────────────────┐                                     │
│  │ Event-Triggered  │  Fires immediately on event match  │
│  │                  │  Evaluated by: ARQ ingestion worker │
│  │  event arrives   │  Latency: <100ms after ingestion    │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  match rules     │                                     │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  eval expression │                                     │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  generate alert  │                                     │
│  └─────────────────┘                                     │
│                                                          │
│  ┌─────────────────┐                                     │
│  │   Threshold      │  Evaluates metrics over windows    │
│  │                  │  Triggered by: APScheduler (60s)    │
│  │  scheduler tick  │  Evaluated by: ARQ rule worker      │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  query events    │  "temp > 80 for 10 minutes"        │
│  │  in time window  │                                     │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  eval threshold  │                                     │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  generate alert  │                                     │
│  └─────────────────┘                                     │
│                                                          │
│  ┌─────────────────┐                                     │
│  │   Composite      │  Correlates multiple event types   │
│  │                  │  Triggered by: APScheduler (5min)   │
│  │  scheduler tick  │  State management:                  │
│  │       │          │                                     │
│  │       ▼          │   Window < 1hr:  Redis only        │
│  │  load state from │   1hr - 24hr:   Redis + PG backup  │
│  │  Redis / PG      │   > 24hr:       PostgreSQL only    │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  eval composite  │                                     │
│  │  conditions      │                                     │
│  │       │          │                                     │
│  │       ▼          │                                     │
│  │  generate alert  │                                     │
│  └─────────────────┘                                     │
│                                                          │
│  Expression Engine:                                       │
│  • AND, OR, NOT logical operators                        │
│  • =, !=, <, >, <=, >= comparison operators              │
│  • Field references (event.field_name)                   │
│  • Time-window expressions                               │
│  • NO eval(), exec(), or dynamic code execution          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Alert Deduplication:**
```
dedup_key = hash(tenant_id + rule_id + entity_id + evaluation_window)
UniqueConstraint on (tenant_id, dedup_key) prevents duplicate alerts
```

---

### 5. AI Request Pipeline

Every AI interaction passes through a six-stage pipeline with full observability.

```
┌──────────────────────────────────────────────────────────────────┐
│                    AI REQUEST PIPELINE                            │
│                                                                  │
│  User Query: "Why are shipments from Vendor X delayed?"         │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  1. INPUT POLICY GUARD                                   │     │
│  │                                                         │     │
│  │  Checks:                                                │     │
│  │  • 8 prompt injection patterns (regex)                  │     │
│  │    - "ignore previous instructions"                     │     │
│  │    - "reveal system prompt"                             │     │
│  │    - "you are now a..."                                 │     │
│  │    - "act as if you are..."                             │     │
│  │    - "DAN/jailbreak"                                    │     │
│  │    - "forget everything"                                │     │
│  │    - "<system> tags"                                    │     │
│  │  • Tenant model permissions                             │     │
│  │  • Tool permissions                                     │     │
│  │  • Sensitive document classification                    │     │
│  │                                                         │     │
│  │  Output: PolicyResult(allowed, violations, risk_score)  │     │
│  │  Blocked if risk_score >= 1.0                           │     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  2. PROMPT REGISTRY                                      │     │
│  │                                                         │     │
│  │  • Fetches active prompt by (task_type, model_family)   │     │
│  │  • All prompts versioned in database                    │     │
│  │  • Promotion requires evaluation pass (>= 80%)         │     │
│  │  • Zero hardcoded prompts in application code           │     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  3. CONTEXT ASSEMBLY                                     │     │
│  │                                                         │     │
│  │  Token Budget (128K default):                           │     │
│  │  ┌──────────────────────────────────────────────────┐   │     │
│  │  │ System Prompt          15%     19,200 tokens     │   │     │
│  │  │ Conversation History   15%     19,200 tokens     │   │     │
│  │  │ Knowledge Retrieval    40%     51,200 tokens     │   │     │
│  │  │ Tool Results           20%     25,600 tokens     │   │     │
│  │  │ Reserve                10%     12,800 tokens     │   │     │
│  │  └──────────────────────────────────────────────────┘   │     │
│  │                                                         │     │
│  │  Process:                                               │     │
│  │  1. Allocate budgets per section                        │     │
│  │  2. Preserve system prompt (always kept)                │     │
│  │  3. Prune conversation history (oldest first)           │     │
│  │  4. Rank knowledge chunks by relevance_score            │     │
│  │  5. Truncate tool results to budget                     │     │
│  │  6. Return AssembledContext with utilization metrics     │     │
│  │                                                         │     │
│  │  Token estimation: len(text) // 4                       │     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  4. MODEL ROUTER                                         │     │
│  │                                                         │     │
│  │  Default: Anthropic Claude (claude-sonnet-4-20250514)   │     │
│  │                                                         │     │
│  │  Task-specific defaults:                                │     │
│  │  • summarization:  temp=0.3, max_tokens=2048            │     │
│  │  • qa:             temp=0.1, max_tokens=4096            │     │
│  │  • classification: temp=0.0, max_tokens=512             │     │
│  │  • extraction:     temp=0.0, max_tokens=4096            │     │
│  │  • analysis:       temp=0.4, max_tokens=8192            │     │
│  │  • conversation:   temp=0.7, max_tokens=4096            │     │
│  │                                                         │     │
│  │  Supports: provider_override, model_override per request│     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  5. MODEL INVOCATION                                     │     │
│  │     (via Anthropic SDK or configured provider)          │     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  6. OUTPUT POLICY GUARD                                  │     │
│  │                                                         │     │
│  │  Checks:                                                │     │
│  │  • PII leakage detection (regex):                       │     │
│  │    - SSN patterns (XXX-XX-XXXX)                         │     │
│  │    - Credit card numbers (13-19 digits)                 │     │
│  │    - Email addresses                                    │     │
│  │    - Phone numbers                                      │     │
│  │  • Policy violation keywords:                           │     │
│  │    - "bypass security", "hack into"                     │     │
│  │    - "exploit vulnerability", "unauthorized access"     │     │
│  │  • Unsupported claim detection:                         │     │
│  │    - "I guarantee", "100% certain"                      │     │
│  │    - "I promise", "legally binding"                     │     │
│  │                                                         │     │
│  │  Output: PolicyResult(allowed, violations, risk_score)  │     │
│  └─────────────────────┬───────────────────────────────────┘     │
│                        │                                         │
│                        ▼                                         │
│  Response returned with AITelemetrySummary                       │
│  (model_provider, tokens, latency, tools_used)                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Latency Targets:**
| Component | Target |
|---|---|
| Knowledge retrieval | < 500ms |
| Chunk reranking | < 200ms |
| Context assembly | < 200ms |
| Model inference | < 4 seconds |
| Tool coordination | < 1 second |
| **Simple request total** | **< 5 seconds** |
| **Complex request total** | **< 10 seconds** |

---

### 6. Knowledge Management Pipeline

```
Document Upload                    Semantic Search
     │                                  │
     ▼                                  ▼
POST /api/v1/documents          POST /api/v1/documents/search
     │                                  │
     ├── Store file in MinIO            ├── Embed query text
     ├── Create Document record         ├── pgvector similarity search
     ├── Enqueue: generate_embeddings   ├── Rank by cosine similarity
     │                                  └── Return matching chunks
     ▼                                       with document context
ARQ Worker: generate_embeddings
     │
     ├── Extract text from document
     ├── Split into chunks (with token counts)
     ├── Generate embeddings (1536 dimensions)
     ├── Store DocumentChunk records
     └── Store Embedding records (pgvector Vector(1536))
```

---

### 7. Scheduler and Worker Interaction

The scheduler and workers have a strict separation of concerns: the scheduler only enqueues, workers only execute.

```
┌──────────────────────┐         ┌──────────────┐        ┌──────────────┐
│    APScheduler       │         │    Redis      │        │  ARQ Workers │
│  (PostgreSQL store)  │         │   (Queue)     │        │              │
│                      │         │              │        │              │
│  Every 60s: ─────────┼────────▶│ enqueue_job  │───────▶│ evaluate_    │
│   threshold_rules    │         │ ("evaluate_  │        │ threshold_   │
│                      │         │  threshold") │        │ rules()      │
│  Every 5m: ──────────┼────────▶│              │───────▶│              │
│   composite_rules    │         │              │        │ evaluate_    │
│                      │         │              │        │ composite_   │
│  Every 10m: ─────────┼────────▶│              │───────▶│ rules()      │
│   cleanup_locks      │         │              │        │              │
│                      │         │              │        │ cleanup_     │
│  Daily 2am: ─────────┼────────▶│              │───────▶│ expired_     │
│   archive_events     │         │              │        │ locks()      │
│                      │         │              │        │              │
└──────────────────────┘         └──────────────┘        │ archive_     │
                                                         │ old_events() │
Also from API:                                           │              │
  POST /events ────────────────▶ enqueue_job ───────────▶│ process_     │
                                 ("process_event")       │ event()      │
  POST /documents ─────────────▶ enqueue_job ───────────▶│ generate_    │
                                 ("generate_embeddings") │ embeddings() │
                                                         └──────────────┘
```

**Worker Configuration:**
- Max concurrent jobs: 5 per worker process
- Poll delay: 0.5 seconds
- Job timeout: 10 minutes
- Horizontally scalable (run multiple worker instances)

---

### 8. Storage Architecture

Domain code never imports vendor SDKs directly. All storage access goes through the adapter abstraction.

```
┌────────────────────────┐
│   Application Code     │
│   (routes, workers)    │
└──────────┬─────────────┘
           │ uses
           ▼
┌────────────────────────┐
│   StorageAdapter (ABC) │
│                        │
│   • upload()           │
│   • download()         │
│   • delete()           │
│   • list_objects()     │
│   • get_presigned_url()│
│   • ensure_bucket()    │
└──────┬───────┬─────────┘
       │       │
       ▼       ▼
┌──────────┐ ┌──────────┐
│S3Adapter │ │MinIO     │
│          │ │Adapter   │
│(aioboto- │ │(inherits │
│ core)    │ │ S3, adds │
│          │ │ path-    │
│          │ │ style)   │
└──────────┘ └──────────┘
       │       │
       ▼       ▼
   AWS S3    MinIO
            (:9000)
```

**Factory Pattern:**
```python
adapter = get_storage_adapter("minio", endpoint_url="http://minio:9000", ...)
# or
adapter = get_storage_adapter("s3", region="us-east-1", ...)
```

---

### 9. Observability Architecture

Every request is traced end-to-end with correlated identifiers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST CONTEXT                               │
│                                                                 │
│  Generated/extracted on every request:                          │
│  • request_id  (X-Request-Id header or UUID)                   │
│  • trace_id    (X-Trace-Id header or UUID hex)                 │
│  • tenant_id   (from JWT)                                      │
│                                                                 │
│  Bound to:                                                      │
│  • structlog context (all log entries)                          │
│  • OpenTelemetry span attributes                               │
│  • Response headers (X-Request-Id, X-Trace-Id)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Telemetry Flow:

  FastAPI Request                structlog                 OTLP
       │                            │                       │
       ├── RequestTracingMiddleware  │                       │
       │   binds context ──────────▶│ JSON logs ──────────▶ Loki
       │                            │                       │
       ├── Span creation ──────────────────────────────────▶ Grafana
       │                            │                     (via Tempo)
       ├── AI Pipeline              │                       │
       │   records AITelemetry ────▶│ structured metrics    │
       │   • prompt_version         │                       │
       │   • model_provider/name    │                       │
       │   • input/output tokens    │                       │
       │   • retrieval_score        │                       │
       │   • context_utilization    │                       │
       │   • tool_invocations       │                       │
       │   • latency_ms             │                       │
       │   • policy_guard results   │                       │
       │                            │                       │
       └── Response ◀───────────────┘                       │

  Environment Behavior:
  • dev:        Colored console logs, ConsoleSpanExporter
  • production: JSON logs, OTLP gRPC BatchSpanProcessor
```

---

### 10. Data Flow Summary

```
                    ┌──────────────────────────────────┐
                    │        EXTERNAL SYSTEMS           │
                    │  TMS, ERP, IoT, Webhooks          │
                    └──────────────┬───────────────────┘
                                   │
                              Events (JSON)
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │       EVENT INGESTION             │
                    │  Validate → Store → Enqueue       │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
             ┌───────────┐  ┌──────────┐  ┌────────────┐
             │  Event    │  │ Threshold│  │  Composite  │
             │  Rules    │  │  Rules   │  │   Rules     │
             │ (instant) │  │ (60s)    │  │   (5min)    │
             └─────┬─────┘  └────┬─────┘  └─────┬──────┘
                   │             │               │
                   └──────┬──────┴───────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   ALERTS    │
                   │ (deduplicated)│
                   └──────┬──────┘
                          │
                   ┌──────┴──────┐
                   │             │
                   ▼             ▼
            ┌───────────┐  ┌──────────┐
            │ Dashboard │  │ Webhook/ │
            │  Display  │  │ Notify   │
            └───────────┘  └──────────┘


         ┌──────────────────────────────────┐
         │       KNOWLEDGE PIPELINE         │
         │                                  │
         │  Upload → Chunk → Embed → Store  │
         │                                  │
         │  Query → Embed → Search → Rank   │
         └──────────────┬──────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────┐
         │        AI COPILOT                │
         │                                  │
         │  Guard → Registry → Assemble →   │
         │  Route → Invoke → Guard → Reply  │
         └──────────────────────────────────┘
```

---

### 11. Connection Pool Management

PostgreSQL connections are a finite resource. The system must ensure total connections stay below `max_connections`.

```
Formula:
  (API workers × pool_size) + (ARQ workers × pool_size) < max_connections

Example (development):
  API:       4 workers × 5 pool = 20 connections
  ARQ:       2 workers × 3 pool =  6 connections
  Scheduler: 1 worker  × 2 pool =  2 connections
  ─────────────────────────────────────────────
  Total:                          28 connections
  PostgreSQL default:            100 connections
  Headroom:                       72 connections  ✓
```

---

### 12. Scaling Strategy

The modular architecture supports incremental scaling without rewriting domain logic.

```
MVP (Current):
  Single Docker Compose host
  ┌─────────────────────────────────────┐
  │ API + Workers + Scheduler + DB + Redis + MinIO │
  └─────────────────────────────────────┘

Growth (1K-5K events/sec):
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ API ×3   │  │ Workers  │  │ Scheduler│
  │ (load    │  │ ×5       │  │ ×1       │
  │ balanced)│  │          │  │          │
  └────┬─────┘  └────┬─────┘  └────┬─────┘
       └──────┬──────┘             │
              ▼                    │
  ┌──────────────────┐  ┌─────────┘
  │ Managed PostgreSQL│  │
  │ (RDS/Cloud SQL)  │  │
  └──────────────────┘  │
  ┌──────────────────┐  │
  │ Redis Cluster    │◀─┘
  └──────────────────┘

Enterprise (10K+ events/sec):
  ┌──────────────┐
  │ Dedicated    │  Batch writes, partitioned tables,
  │ Ingestion    │  reduced indexing, queue partitioning
  │ Service      │
  └──────────────┘
  ┌──────────────┐
  │ Kubernetes   │  Container orchestration,
  │ Orchestration│  auto-scaling, rolling deploys
  └──────────────┘
  ┌──────────────┐
  │ Read Replicas│  Separate read/write paths
  └──────────────┘
```

**Key Invariant:** The domain event model remains stable across all scaling tiers. Ingestion services can be replaced without changing the core schema.

---

## Package Dependency Graph

```
packages/common          ◀── Foundation (no internal deps)
    │
    ├── packages/db      ◀── Depends on: common
    │       │
    │       ├── packages/schemas   ◀── Depends on: common
    │       │
    │       ├── packages/events    ◀── Depends on: common, db
    │       │
    │       ├── packages/rules     ◀── Depends on: common, db
    │       │
    │       └── packages/ai        ◀── Depends on: common, db, observability
    │
    ├── packages/observability     ◀── Depends on: common
    │
    ├── packages/storage           ◀── Depends on: common
    │
    └── packages/domain            ◀── Standalone

apps/api        ◀── Depends on: all packages
apps/workers    ◀── Depends on: common, db, schemas, observability, storage, ai, events, rules
apps/scheduler  ◀── Depends on: common, db, observability
```

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| Cross-tenant access | PostgreSQL RLS enforced at DB layer |
| Prompt injection | 8-pattern regex detection in InputPolicyGuard |
| PII leakage | Regex detection for SSN, CC, email, phone in OutputPolicyGuard |
| Arbitrary code execution | Rule expressions use deterministic parser, no eval/exec |
| JWT compromise | Configurable expiry (default 30min), bcrypt password hashing |
| Rate abuse | Per-tenant Redis counters with tier-based limits |
| Storage access | Presigned URLs with configurable expiry |
| Audit trail | AuditLog table captures all mutations with tenant/user context |

---

## Design Principles

1. **Security First** -- Tenant isolation at the database layer, not application layer
2. **Deterministic AI** -- Prompt-versioned, context-budget controlled, observable
3. **Vendor Independence** -- Containerized, abstracted storage, swappable model providers
4. **Event-Driven Intelligence** -- Insight originates from event streams, not static data
5. **Modular Scalability** -- Components separable into dedicated services without rewrites
