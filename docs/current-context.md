# Orbis Labs current context

## Snapshot

This document records the current state before team branches are distributed.

Repository: `SwarnavChatterjee/Orbis-Labs`

Baseline commit:

```text
ab1eb89 chore: initialize Orbis Labs platform
```

The baseline `main` branch has been pushed to GitHub. The working tree was clean at the time of the push.

## Product decisions

- Official name: Orbis Labs
- Initial domain: internships and jobs
- LLM provider: OpenAI API
- Primary source: Internshala scraper
- Secondary source: GitLab Greenhouse API
- Ambiguity behavior: continue with visible warnings
- Database: PostgreSQL
- MVP search: PostgreSQL indexes and full-text search
- Vector database: deferred
- LLM rule: never invent records

## Implemented code

### Backend

- FastAPI application in `backend/app/main.py`
- Pydantic contracts in `backend/app/models/schemas.py`
- SQLModel tables in `backend/app/models/db.py`
- Async database session in `backend/app/core/database.py`
- OpenAI parser in `backend/app/llm/parser.py`
- Source registry in `backend/app/collectors/registry.py`
- Approved collectors in `backend/app/collectors/internshala.py` and
  `backend/app/collectors/greenhouse.py`, with fixture coverage
- Record cleaning and deterministic deduplication in `backend/app/processing/`
- Query processing boundary in `backend/app/jobs/tasks.py`
- Query routes in `backend/app/api/routes/queries.py`

### Database

- Docker Compose PostgreSQL 16 service
- Host port `5433` mapped to container port `5432`
- Local database URL:

```text
postgresql+asyncpg://orbis:orbis@localhost:5433/orbis_labs
```

- Initial Alembic migration applied locally
- `pgcrypto` and `pg_trgm` extensions included

### Frontend

- React + TypeScript + Vite shell
- Orbis Labs branding
- Production build configured

### Documentation and CI

- Architecture documentation
- Implementation plan
- Contribution workflow
- GitHub Actions backend test workflow

## Verification status

Current local verification:

```text
26 backend tests passing
Frontend production build passing
PostgreSQL accepting connections
Alembic migrations and Procrastinate schema applied
```

The test suite uses isolated SQLite databases for repeatable tests. PostgreSQL is used for local runtime/migration verification.

## Not yet complete

- Live OpenAI smoke test with a real API key
- Live-source validation and compliance checks
- Deterministic confidence scoring
- SSE progress implementation
- Frontend/backend integration
- CSV export
- Query history UI

## Team constraints

- Do not commit `.env` or API keys.
- Keep shared Pydantic contracts coordinated.
- Do not silently change API response envelopes.
- Preserve provenance on every collected record.
- Keep collectors separate from route modules.
- Add tests for behavior changed by each branch.

## Recommended first actions after branching

1. Configure an OpenAI key and run the planner evaluation.
2. Validate the two collectors against permitted live endpoints.
3. Connect the frontend workspace to the query API, SSE, results, and export.
