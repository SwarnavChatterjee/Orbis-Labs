# Role 2 — API, PostgreSQL, and Job Backend

## Branch

```text
feat/api-backend
```

## Prompt

You are responsible for the FastAPI, PostgreSQL, migration, and background-processing layer of Orbis Labs.

Read these files before changing anything:

- `README.md`
- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/current-context.md`
- `backend/app/main.py`
- `backend/app/api/routes/queries.py`
- `backend/app/models/db.py`
- `backend/app/models/schemas.py`
- `backend/app/core/database.py`
- `backend/alembic/versions/0001_initial.py`
- `docker-compose.yml`

### Product context

Orbis Labs accepts a natural-language request, creates a query record, parses it into a `QueryPlan`, routes it to permitted sources, collects records, processes them, and eventually exposes results with provenance.

The local PostgreSQL service runs on host port `5433` and container port `5432`:

```text
postgresql+asyncpg://orbis:orbis@localhost:5433/orbis_labs
```

The database migration already defines users, projects, sources, queries, and records.

### Your responsibilities

1. Keep the FastAPI query lifecycle reliable.
2. Complete the API contract for query submission, status, history, results, and progress.
3. Integrate the parser through an interface rather than coupling routes directly to OpenAI.
4. Replace the temporary background-task boundary with a durable PostgreSQL-backed worker when appropriate.
5. Add query status transitions and failure persistence.
6. Implement SSE progress events for the frontend.
7. Keep migrations reversible and synchronized with SQLModel models.
8. Add integration tests against isolated test databases.

### Required endpoints

Maintain these routes:

```text
POST /api/queries
GET  /api/queries
GET  /api/queries/{id}
GET  /api/queries/{id}/results
GET  /api/queries/{id}/stream
```

Use the existing response envelope:

```json
{"success": true, "data": {}}
```

### Required status behavior

Use explicit states such as:

```text
queued → running → planned → collecting → cleaning → completed
                                      ↘ failed
```

Every failure should be persisted with a safe error message. Never expose secrets, database credentials, or raw provider credentials in an API response.

### Important boundaries

Do not:

- Change `QueryPlan` casually; coordinate with the OpenAI planner owner.
- Put OpenAI API calls in React or browser code.
- Implement scraping logic in API route modules.
- Delete historical queries during re-runs.
- Add Redis unless explicitly approved; PostgreSQL is the planned MVP job store.
- Commit `.env` or any credentials.

### Suggested implementation

- Keep routes thin and move workflow logic into services/jobs.
- Use dependency injection for database sessions and query planning.
- Make background processing callable directly in tests.
- Use a durable worker command separate from the web process when implementing Procrastinate.
- Emit stage events with query ID, status, timestamp, and an optional safe message.
- Add pagination parameters to result/history endpoints before the frontend depends on them.

### Definition of done

- A query can be created and persisted in PostgreSQL.
- The parser can be invoked through the backend boundary.
- Status and failure transitions are persisted.
- Results are query-scoped and ordered deterministically.
- SSE emits useful stage updates.
- Alembic migration matches the models.
- Tests pass without requiring production credentials.
- `PYTHONPATH=backend pytest backend/tests -q` passes.

### Handoff

Report:

- Endpoint changes
- Database/migration changes
- Status lifecycle
- Worker command or startup instructions
- SSE event shape
- Tests and manual curl examples
- Any frontend contract changes

