# Orbis Labs — Complete Implementation Plan
*9 days · 1 `main` + 4 `feat` branches · FastAPI + React + Postgres*

---

## 0. Prerequisites

- Python 3.11+, Node 20+
- Postgres 15+ (local Docker or Railway/Render/Supabase managed instance)
- Anthropic or OpenAI API key
- `.env` (backend):
  ```
  DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dataintel
  ANTHROPIC_API_KEY=...
  PROCRASTINATE_APP=app.jobs.tasks:app
  ```

**Ground rules (non-negotiable across all branches):**
- The LLM never originates a record — only parses queries or fills fields on records a collector already found.
- Every record traces to a `source_url` + `retrieved_at`.
- `main` is protected. No direct pushes. All work merges via PR with CI green.

---

## 1. Branch Map

| Branch | Owns | Doc sections | Depends on |
|---|---|---|---|
| `main` | Shared contract, scaffold, CI | — | — |
| `feat/backend-core` | FastAPI app, DB schema, Procrastinate queue, API routes | §8, §9, §13 | `main` |
| `feat/llm-pipeline` | Structured-output parser, confidence scoring, source routing | §5, §6.1 | `main` |
| `feat/data-collection` | Collectors, cleaning, dedup | §6, §7 | `main`, registry from `feat/llm-pipeline` |
| `feat/frontend-dashboard` | Query UI, SSE progress, results table, history/re-run | §9, §10 | `feat/backend-core` API shape |

**Merge order:** `backend-core` → `llm-pipeline` → `data-collection` → `frontend-dashboard`, rebasing each remaining branch onto `main` after the prior one lands.

---

## 2. Day 0 — Land on `main` before anyone branches

Everything below must be committed to `main` and pushed *first* — all 4 branches import this contract, so branching before it exists causes merge conflicts on the same file later.

```bash
mkdir orbis-labs && cd orbis-labs
git init && git branch -M main
mkdir -p backend/app/{api/routes,models,llm,collectors,processing,jobs,core}
mkdir -p backend/{fixtures,tests,alembic}
npm create vite@latest frontend -- --template react-ts
mkdir -p .github/workflows
```

Add `backend/app/models/schemas.py` (the shared contract, §5.3/§6.1):

```python
from pydantic import BaseModel, Field
from typing import Literal

class AmbiguityFlag(BaseModel):
    field: str
    reason: str

class QueryFilters(BaseModel):
    role: str | None = None
    location: str | None = None
    graduation_year: int | None = None

class QueryPlan(BaseModel):
    intent: Literal["internship_search"]
    filters: QueryFilters
    required_fields: list[str]
    target_count: int
    sources: list[str] = Field(default_factory=list)       # SourceDescriptor ids
    ambiguity_flags: list[AmbiguityFlag] = Field(default_factory=list)

class SourceDescriptor(BaseModel):
    id: str
    name: str
    handles: list[str]
    collector: str   # dotted path to collector function
```

Then: `.github/workflows/ci.yml` running `pytest` on push (even with zero tests — see §9), a `docker-compose.yml` stub (postgres + backend + frontend), and one commit: `chore: repo scaffold + shared Pydantic contract`.

```bash
git checkout -b feat/backend-core && git checkout main
git checkout -b feat/llm-pipeline && git checkout main
git checkout -b feat/data-collection && git checkout main
git checkout -b feat/frontend-dashboard && git checkout main
git remote add origin <repo-url>
git push -u origin main feat/backend-core feat/llm-pipeline feat/data-collection feat/frontend-dashboard
```

---

## 3. Repo Tree (reference)

```
orbis-labs/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/{queries.py, sources.py}
│   │   ├── models/{schemas.py, db.py}
│   │   ├── llm/parser.py
│   │   ├── collectors/{registry.py, internshala.py, careers_page.py}
│   │   ├── processing/{clean.py, validate.py, dedup.py}
│   │   ├── jobs/tasks.py
│   │   └── core/{config.py, db_session.py}
│   ├── fixtures/{source_a.json, source_b.json}
│   ├── tests/, alembic/, requirements.txt, Dockerfile
├── frontend/src/
│   ├── components/{QueryInput.tsx, ProgressStream.tsx, ResultsTable.tsx, QueriesList.tsx}
│   ├── api/client.ts
│   └── App.tsx
├── .github/workflows/ci.yml
└── docker-compose.yml
```

---

## 4. Database DDL (backend-core, Day 2)

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  base_url TEXT NOT NULL
);

CREATE TABLE queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  raw_text TEXT NOT NULL,
  parsed_params JSONB,
  status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|completed|failed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_id UUID REFERENCES queries(id),
  source_id UUID REFERENCES sources(id),
  company TEXT NOT NULL,
  role TEXT NOT NULL,
  location TEXT,
  stipend JSONB,              -- {amount, currency, period} — resolves §8.3 mismatch
  deadline DATE,
  source_url TEXT NOT NULL,
  retrieved_at TIMESTAMPTZ NOT NULL,
  confidence NUMERIC(3,2),
  search_doc tsvector
);

CREATE INDEX idx_records_company_trgm ON records USING GIN (company gin_trgm_ops);
CREATE INDEX idx_records_role_trgm    ON records USING GIN (role gin_trgm_ops);
CREATE INDEX idx_records_search       ON records USING GIN (search_doc);
CREATE INDEX idx_records_location     ON records (location);
```

---

## 5. API Contract (backend-core, Day 3–4)

Envelope: `{"success": true, "data": {}}` / `{"success": false, "error": "message"}`

| Method / path | Purpose |
|---|---|
| `POST /api/queries` | Submit NL query → `{queryId, status: "accepted"}` |
| `GET /api/queries/{id}` | Poll status |
| `GET /api/queries/{id}/results` | Paginated cleaned/deduplicated records |
| `GET /api/queries/{id}/stream` | SSE: `parsing → collecting → cleaning → done` |
| `GET /api/queries` | History list for §10 screen |
| `GET /api/sources`, `GET /api/projects` | Listing endpoints |

---

## 6. Day-by-Day Grid

| Day | `backend-core` | `llm-pipeline` | `data-collection` | `frontend-dashboard` |
|---|---|---|---|---|
| 1 | FastAPI skeleton, alembic init, docker-compose, enable `pg_trgm`/`pgcrypto` | Draft `QueryPlan` few-shot examples; standalone script → 1 hardcoded query → validated `QueryPlan` | Manually pull 10 real records/source by hand → fixtures; check `robots.txt` for both sources | Vite scaffold; route skeleton (Query / Results / History pages) against mock JSON |
| 2 | `queries/records/sources` tables + migration; Procrastinate wired as async worker; CI green | `llm/parser.py` (tool-use / `response_format`), `ambiguity_flags` wired | Stub `SOURCE_REGISTRY` (2 `SourceDescriptor`s), collectors return fixture JSON | `QueryInput` posts to mocked `POST /api/queries` |
| 3 | `POST /api/queries` enqueues Procrastinate job; `GET /{id}` status | Deterministic confidence scorer (§5.6 formula); parser unit tests (clean/ambiguous/unsupported-field cases) | Rule-based routing: match `filters.role`/`intent` → `SOURCE_REGISTRY.handles` | `ProgressStream` (SSE client) skeleton |
| 4 | `GET /{id}/stream` SSE route, pipeline-stage events | Integration support for merge | Point collectors at **live** sources (fixtures stay as fallback) | `ResultsTable` (paginated) + CSV export |
| 5 | `GET /{id}/results` paginated route | — | Cleaning (currency/date/location normalize) + `pg_trgm` dedup + canonical-record selection | Queries/History list (§10): status, source(s), record count, re-run button |
| 6 | **Merge `backend-core` → `main`** | **Merge `llm-pipeline`, rebased on `main`** | Full pipeline wired end-to-end against real backend | Rebase onto updated `main`; swap mocks for real endpoints |
| 7 | Bug support | Bug support | **Merge `data-collection`, rebased on `main`** | Filters UI, error/loading states, confidence + provenance display; **merge** once stable |
| 8 | Unit/integration/e2e tests; contract tests off shared Pydantic model; **cache fallback dataset** | Parser edge-case tests | Dedup/clean tests | UI smoke tests |
| 9 | Deploy (single host) | — | — | Build + serve static bundle from FastAPI image |

---

## 7. Per-Branch Task Checklists

### `feat/backend-core`
- [ ] FastAPI app factory + router registration
- [ ] SQLModel tables + Alembic migration matching §4 DDL
- [ ] Procrastinate app + worker (`asyncio.create_task` alongside Uvicorn, or its own worker command)
- [ ] All 6 routes from §5, response envelope enforced via middleware/exception handler
- [ ] SSE stream via `StreamingResponse`
- **Definition of done:** `pytest` green in CI; can `curl -X POST /api/queries` and see a row land in `queries`.

**Codex/agent kickoff prompt:**
> Scaffold FastAPI in `backend/app/` per the repo tree in §3. Build SQLModel tables per §4's DDL (note: `stipend` is JSONB, not TEXT). Wire Procrastinate as a Postgres-backed job queue (no Redis). Add Alembic migrations. Implement the 6 routes in §5 with the `{success, data|error}` envelope.

### `feat/llm-pipeline`
- [ ] `parser.py`: structured output via Anthropic tool-use or OpenAI `response_format` against `QueryPlan`
- [ ] `ambiguity_flags` populated whenever a field is inferred/normalized, not silently guessed
- [ ] Confidence scorer — deterministic, **not** LLM self-reported (§5.6 formula)
- [ ] Rule-based source router: `filters.role`/`intent` → `SOURCE_REGISTRY[*].handles`
- **Definition of done:** standalone script takes one raw query string, prints a schema-valid `QueryPlan` with `sources` populated.

**Codex/agent kickoff prompt:**
> Using the shared `QueryPlan`/`QueryFilters`/`AmbiguityFlag` models in `models/schemas.py`, build a structured-output parser per §5. Add the deterministic confidence formula from §5.6 (never ask the LLM to self-report confidence). Add the rule-based registry router from §6.1 — no LLM judgment in this step.

### `feat/data-collection`
- [ ] Two collectors (Playwright-Python + `httpx`/BeautifulSoup) built and tested against `fixtures/*.json` before touching the live site
- [ ] `robots.txt` check programmatically before first request to any new source
- [ ] Cleaning: currency → numeric+currency+period, location alias map, dates → ISO
- [ ] Validation: flag failures, never silently drop
- [ ] Dedup: composite key (company+role+location) first pass, `pg_trgm` fuzzy second pass, canonical record chosen, **all source associations kept**
- **Definition of done:** running the pipeline against fixtures produces deduped records with `source_url` + `retrieved_at` on every row.

**Codex/agent kickoff prompt:**
> Build collectors against `backend/fixtures/` first — live scraping only after fixtures pass end to end. Implement cleaning (§7.1), validation (§7.2, flag don't drop), and dedup (§7.3: composite key → `pg_trgm` fuzzy pass → canonical record, keeping every source association).

### `feat/frontend-dashboard`
- [ ] `QueryInput` → `POST /api/queries`
- [ ] `ProgressStream` consuming SSE `/stream`
- [ ] `ResultsTable`: paginated, shows confidence + source URL + retrieved_at, CSV export
- [ ] `QueriesList` (§10): status, source(s) used, record count, re-run button (new `query_id`, never mutates old run)
- **Definition of done:** one full query submitted through the real UI produces a visible, exportable results table.

**Codex/agent kickoff prompt:**
> Build the query input, an SSE-driven progress view, a paginated results table with CSV export, and the queries/history list from §10 with a working re-run action. Wire against the real `feat/backend-core` API contract in §5 once merged; use mock JSON until then.

---

## 8. Git Workflow

- Conventional commits (`feat:`, `fix:`, `chore:`, `test:`).
- PR checklist: CI green, no direct pushes to `main`, contract changes to `schemas.py` called out explicitly in the PR description (it's shared — a silent change breaks the other 3 branches).
- After each merge to `main`, remaining open branches `git rebase main` before continuing — don't wait until Day 9 to reconcile drift.

---

## 9. Testing Plan (§14)

| Type | Covers | Owner |
|---|---|---|
| Unit | Parser ("2027 grads" → `graduation_year: 2027`), date/currency normalization, dedup matching | `llm-pipeline`, `data-collection` |
| Integration | Full API → job → DB round trip | `backend-core` |
| Contract | Tests derived from the shared Pydantic model (one definition, tested once) | `backend-core` |
| E2E | One real query, submission → CSV export, via `pytest` + `httpx.AsyncClient` | shared, Day 8 |

---

## 10. Deployment (§13, Day 9)

| Component | Choice |
|---|---|
| App | FastAPI (Uvicorn/Gunicorn) serving built React bundle from one Docker image |
| Database | Managed Postgres (Railway / Render / Supabase) |
| Jobs | Procrastinate, in-container async worker |
| Scraping | Runs as a Procrastinate job in-app for MVP scale |
| CI/CD | GitHub Actions, `pytest` on push |

---

## 11. Risk Register (§16)

| Risk | Mitigation | Watch owner |
|---|---|---|
| Ambiguous NL queries | Schema-constrained parsing + explicit `ambiguity_flags` | `llm-pipeline` |
| Scraper blocked / layout drift | Validate sources Day 1; keep fixture fallback; check `robots.txt` in code | `data-collection` |
| LLM hallucinating records | LLM only parses/fills — never originates a record | all |
| Over/under-aggressive dedup | Composite key first, fuzzy as secondary signal, log merge rate | `data-collection` |
| Too many moving services | One deploy image, one datastore, no Redis, no vector DB | `backend-core` |
| Demo-day live failure | Cached fallback dataset from a known-good run | `backend-core` |

---

## 12. Demo-Day Checklist

- [ ] Fallback fixture dataset cached and loadable without network access
- [ ] One real end-to-end query run and recorded (video backup)
- [ ] CSV export verified
- [ ] Queries/history list + re-run verified
- [ ] README with setup steps committed

---

## 13. Open Decisions — lock before Day 2

- Final `stipend` field shape (JSONB confirmed above — get sign-off)
- Which two sources to commit to, and confirmed `robots.txt` posture for both
- Clarifying-question UX for low-confidence parses, or proceed + surface confidence in the table
