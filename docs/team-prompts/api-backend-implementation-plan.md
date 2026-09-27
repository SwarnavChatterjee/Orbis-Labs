# Orbis Labs API Backend — Detailed Implementation Plan

## 1. Purpose

This document is the execution plan for the `feat/api-backend` branch.

The API backend is the orchestration layer of Orbis Labs. It accepts user requests, persists query state, invokes the planner boundary, schedules collection work, exposes progress, and returns source-backed records.

```text
React frontend
      ↓ HTTP/SSE
FastAPI API
      ↓
Query service and PostgreSQL
      ↓
Background worker
      ↓
Planner → collectors → processing → records
```

The backend coordinates the workflow. It does not own OpenAI prompt design, collector-specific scraping rules, or frontend presentation.

## 2. Current repository context

The baseline already contains:

```text
backend/app/main.py                 FastAPI application
backend/app/api/routes/queries.py   Initial query endpoints
backend/app/models/db.py            SQLModel tables
backend/app/models/schemas.py       Shared API/domain contracts
backend/app/core/database.py        Async SQLAlchemy session factory
backend/app/jobs/tasks.py           Temporary query processing boundary
backend/alembic/                    Initial PostgreSQL migration
docker-compose.yml                  PostgreSQL 16 service
backend/tests/                      API and contract tests
```

The local PostgreSQL service has been configured and verified on host port `5433`:

```text
postgresql+asyncpg://orbis:orbis@localhost:5433/orbis_labs
```

The initial migration creates users, projects, sources, queries, records, `pgcrypto`, `pg_trgm`, and initial indexes.

The current processing function uses a temporary FastAPI background-task boundary. This branch must make the workflow durable and observable.

## 3. Product decisions

- Official name: Orbis Labs
- Initial domain: internships and jobs
- Primary source: Internshala scraper
- Secondary source: GitLab Greenhouse API
- LLM provider: OpenAI, accessed through a planner interface
- Database: PostgreSQL
- Job storage: PostgreSQL-backed worker, preferably Procrastinate for the MVP
- Progress transport: Server-Sent Events
- Search: PostgreSQL indexes/full-text search for MVP
- Vector database: deferred
- Query ambiguity: continue with visible warnings
- Record provenance: mandatory

## 4. Scope

### Included

- FastAPI route organization
- Request/response contract enforcement
- Async PostgreSQL sessions
- Query lifecycle persistence
- Planner interface integration
- Durable background job boundary
- Status transitions and failures
- Query history and re-run support
- Paginated results
- SSE progress stream
- Source and project listing foundations
- API, integration, and contract tests
- Local and deployment instructions

### Excluded

- OpenAI prompt engineering
- Collector selectors and API parsing
- Cleaning and deduplication algorithms owned by the processing work
- React component implementation
- Authentication and authorization beyond safe boundaries
- Billing, quotas, and multi-tenant administration
- Vector search
- LLM-generated result summaries

## 5. Backend architecture

Organize the backend around thin routes and testable services:

```text
app/
├── api/routes/       HTTP validation and response mapping
├── core/              configuration, database, shared infrastructure
├── models/            SQLModel tables and Pydantic contracts
├── services/          query orchestration and result logic
├── jobs/              durable tasks and worker entry points
├── collectors/       collector interfaces and implementations
└── processing/        normalization, validation, deduplication
```

The route layer should not contain the full pipeline. A route should validate input, call a service, and map the result to the API envelope.

## 6. Shared API contract

All successful responses use:

```json
{
  "success": true,
  "data": {}
}
```

All expected errors use:

```json
{
  "success": false,
  "error": "Human-readable message"
}
```

Do not silently change this envelope because the frontend depends on it.

### Query submission

Request:

```json
{
  "raw_text": "Find software engineering internships in India"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "query_id": "uuid",
    "status": "accepted"
  }
}
```

The request must return quickly. It must not wait for OpenAI, scraping, or processing to finish.

### Query status

```json
{
  "id": "uuid",
  "raw_text": "Find software engineering internships in India",
  "status": "collecting",
  "parsed_params": {},
  "error_message": null,
  "created_at": "2026-09-28T10:00:00Z",
  "updated_at": "2026-09-28T10:01:00Z"
}
```

### Result record

Each record should expose structured, source-attributed fields:

```json
{
  "company": "Example Company",
  "role": "Software Engineering Intern",
  "location": "Bangalore",
  "stipend": {
    "amount": 20000,
    "currency": "INR",
    "period": "monthly"
  },
  "deadline": "2027-06-30",
  "source_name": "Internshala",
  "source_url": "https://example.com/listing/123",
  "retrieved_at": "2026-09-28T10:05:00Z",
  "confidence": 0.92,
  "validation_errors": []
}
```

## 7. Database model plan

### Users

MVP users are minimal. Keep the table available for future ownership but do not block the first demo on full authentication.

```text
users
  id UUID primary key
  email unique
  created_at timestamptz
```

### Projects

Projects group query history:

```text
projects
  id UUID primary key
  user_id nullable foreign key
  name
  created_at timestamptz
```

### Sources

Sources identify registry-backed origins:

```text
sources
  id UUID primary key
  name
  base_url
```

The source registry remains application configuration. The database stores source provenance used by collected records.

### Queries

```text
queries
  id UUID primary key
  project_id nullable foreign key
  raw_text text not null
  parsed_params JSONB nullable
  status text not null
  error_message text nullable
  created_at timestamptz
  updated_at timestamptz
```

Recommended additional fields if needed:

- `prompt_version`
- `started_at`
- `completed_at`
- `source_ids` or a normalized query-source relation
- `record_count`

Add these through an explicit Alembic migration and update the contracts/tests together.

### Records

```text
records
  id UUID primary key
  query_id foreign key
  source_id nullable foreign key
  company
  role
  location nullable
  stipend JSONB nullable
  deadline nullable date
  source_url
  retrieved_at timestamptz
  confidence nullable numeric
  validation_errors JSONB
```

Do not delete source evidence when deduplicating. If multiple sources support one canonical record, preserve all associations.

## 8. Database implementation rules

1. Use async SQLAlchemy sessions through the existing session factory.
2. Keep transactions short.
3. Commit query status transitions explicitly.
4. Do not hold a database session while making long external HTTP/OpenAI calls unless necessary.
5. Re-fetch records after external work before committing final state.
6. Use migrations for schema changes; do not rely on `metadata.create_all()` in production.
7. Keep migration downgrade behavior safe and documented.
8. Add indexes for query status, query ID, source ID, location, and fuzzy search fields.
9. Use server-side pagination for history and results.
10. Avoid returning unbounded record sets.

## 9. Query lifecycle

Use a state machine rather than arbitrary status strings:

```text
queued
  ↓
running
  ↓
planned
  ↓
collecting
  ↓
cleaning
  ↓
completed
```

Failure transitions:

```text
queued/running/planned/collecting/cleaning → failed
```

Rules:

- A completed query is immutable except for safe metadata corrections.
- A re-run creates a new query ID.
- A failed query retains its raw input and error message.
- Status transitions are timestamped through `updated_at`.
- Worker retries must not create duplicate query records.
- A query should be idempotent at the job level using its query ID.

## 10. Query processing service

Create a service boundary such as:

```python
async def process_query(query_id: UUID) -> None:
    plan = await planner.parse(raw_text)
    sources = route_sources(plan.intent, plan.filters.role)
    collected = await collect_from_sources(plan, sources)
    cleaned = clean_records(collected)
    validated = validate_records(cleaned)
    deduplicated = deduplicate_records(validated)
    await persist_records(query_id, deduplicated)
```

The service should emit status events between stages.

Keep the individual operations injectable so tests can replace:

- Planner
- Collector registry
- Processing functions
- Session factory
- Event publisher

## 11. Planner integration

The API branch must call the planner through an interface:

```python
class QueryPlanner(Protocol):
    def parse(self, raw_text: str) -> QueryPlan:
        ...
```

The OpenAI branch owns the implementation. The backend owns orchestration, persistence, timeout policy, and error mapping.

The API must not:

- Put prompts in route functions
- Import React code
- Accept model-provided arbitrary source URLs
- Persist unvalidated model output

## 12. Durable background jobs

The current FastAPI background task is a temporary boundary. Implement a durable PostgreSQL-backed worker using Procrastinate or the agreed equivalent.

Required properties:

- Queued work survives web-process restarts.
- Jobs have retry limits.
- Transient and permanent errors are distinguished.
- A job is associated with one query ID.
- Duplicate execution is safe or detected.
- Worker logs contain query ID and stage, not secrets.
- A separate worker command can run independently of Uvicorn.

Recommended commands:

```bash
uvicorn app.main:app --app-dir backend --reload
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app worker queries
```

The installed Procrastinate CLI uses the `-a module.attribute` form, and the
registered application object is `app.jobs.tasks.procrastinate_app`.

## 13. SSE progress stream

Implement:

```text
GET /api/queries/{id}/stream
```

Example events:

```text
event: status
data: {"query_id":"...","status":"queued"}

event: status
data: {"query_id":"...","status":"planned"}

event: status
data: {"query_id":"...","status":"collecting","source":"gitlab_greenhouse"}

event: status
data: {"query_id":"...","status":"cleaning"}

event: status
data: {"query_id":"...","status":"completed"}
```

The stream must:

- Send current state when connected.
- Send future state changes.
- Close on `completed` or `failed`.
- Handle disconnected clients without failing the worker.
- Avoid holding a database transaction open.
- Use keep-alive comments if infrastructure requires them.

If no event broker exists for the MVP, a PostgreSQL-backed event table or bounded polling loop may be used behind the SSE endpoint. Keep the frontend event shape stable.

## 14. API endpoint plan

### `POST /api/queries`

Responsibilities:

- Validate non-empty raw text.
- Create a queued query.
- Enqueue processing.
- Return query ID immediately.

Failure cases:

- Invalid request body: 422.
- Database failure: safe 503 or 500 envelope.
- Queue failure: persist failed state where possible.

### `GET /api/queries`

Add:

- `page`
- `page_size`
- Optional `status`
- Newest-first ordering

Return pagination metadata:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### `GET /api/queries/{id}`

Return status, original input, parsed plan, timestamps, error, source summary, and record count where available.

### `GET /api/queries/{id}/results`

Add pagination and safe filters such as location, role, company, and confidence threshold. Query results must always be scoped by query ID.

### `GET /api/queries/{id}/stream`

Return `text/event-stream` and follow the SSE rules above.

### `POST /api/queries/{id}/rerun`

Create a new query ID using the previous raw request or stored filters. Never mutate the old query.

### `GET /api/sources` and `GET /api/projects`

Expose basic registry/database listings only after the core query lifecycle is stable.

## 15. Error handling

Define safe application errors for:

```text
QueryNotFound
InvalidQueryRequest
PlannerFailure
CollectionFailure
ProcessingFailure
DatabaseUnavailable
QueueUnavailable
```

Map errors consistently:

```text
404 → missing query
422 → invalid request parameters
409 → invalid state transition
503 → database/queue dependency unavailable
500 → unexpected internal failure
```

Do not leak:

- Stack traces
- SQL statements containing values
- Database credentials
- OpenAI API keys
- Internal filesystem paths
- Collector authentication data

Log detailed diagnostics server-side with a query ID for correlation.

## 16. Security and operational rules

- Keep `.env` untracked.
- Validate all request bodies and query parameters.
- Bound page sizes and target counts.
- Treat raw user input as untrusted text.
- Do not execute model output as code.
- Restrict collectors to registered source descriptors.
- Add request timeouts for external calls.
- Add worker timeouts for long-running jobs.
- Avoid logging full source responses by default.
- Plan authentication before exposing user/project data publicly.

## 17. Testing strategy

### Unit tests

Test:

- Request validation
- Status transition rules
- Pagination calculations
- Error mapping
- Source routing handoff
- Planner injection
- Record query scoping
- SSE event formatting

### Database integration tests

Use an isolated test database or SQLite-compatible test setup where appropriate. For PostgreSQL-specific JSONB and trigram behavior, add PostgreSQL integration coverage.

Test:

- Migration application
- Query creation
- Status updates
- Failure persistence
- Result insertion
- Query-scoped result retrieval
- Re-run immutability

### Worker tests

Test:

- A queued query becomes running.
- Planner output is persisted.
- Collector failures become failed queries.
- Retries are bounded.
- A completed query is not processed twice accidentally.
- Status events are emitted in order.

### API tests

Test:

- `POST /api/queries` returns accepted.
- `GET /api/queries/{id}` returns status.
- Missing IDs return the error envelope.
- History is ordered and paginated.
- Results are paginated and scoped.
- SSE uses the declared event shape.

Verification command:

```bash
PYTHONPATH=backend pytest backend/tests -q
```

## 18. Implementation sequence

### Step 1 — Freeze contracts

Confirm request models, response envelope, statuses, pagination, and SSE event shapes with the frontend and planner owners.

### Step 2 — Separate service logic from routes

Move query creation, retrieval, and processing orchestration into testable services.

### Step 3 — Complete database models and migrations

Add only the fields required by the lifecycle. Run:

```bash
docker compose up -d postgres
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
```

### Step 4 — Integrate the planner interface

Use a fake planner first. Store the validated plan and source IDs.

### Step 5 — Implement durable jobs

Configure the PostgreSQL-backed worker and verify retry/error behavior.

### Step 6 — Add progress events

Publish stage updates and expose them through SSE.

### Step 7 — Add pagination, filters, and re-run

Complete history and result contracts before frontend integration.

### Step 8 — Add integration tests

Run the complete API → job → database path with fake planner and fixture collectors.

### Step 9 — Prepare frontend handoff

Publish endpoint examples, event examples, status values, and error shapes.

## 19. Acceptance criteria

The branch is merge-ready when:

- A query can be submitted through FastAPI.
- The request is persisted in PostgreSQL.
- Processing is scheduled through a durable worker boundary.
- The planner is injected rather than hard-coded into routes.
- Query statuses and failures persist correctly.
- Results are query-scoped and paginated.
- Re-running creates a new query ID.
- SSE emits useful stage updates and closes correctly.
- Alembic migrations match SQLModel models.
- No credentials appear in responses or logs.
- API and worker tests cover success and failure paths.
- Existing tests pass.

Required commands:

```bash
PYTHONPATH=backend pytest backend/tests -q
npm run build --prefix frontend
```

## 20. Handoff template

The pull request description should include:

```text
Branch:
API endpoints changed:
Database models changed:
Migration revision:
Status lifecycle:
Worker command:
SSE event shape:
Error mapping:
Test commands:
Manual curl examples:
Frontend follow-ups:
Known limitations:
```

## 21. Final principle

The API backend should make the Orbis Labs workflow reliable, observable, and replaceable at each boundary.

```text
Thin routes → explicit services → durable jobs → source-backed records
```
