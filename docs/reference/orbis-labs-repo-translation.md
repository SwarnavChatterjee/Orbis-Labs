Here's a top-down read of the architecture doc translated into an actual repo you can start typing into, plus a 5-branch (main + 4 feat) git setup mapped to how the doc's own layers group naturally. Everything below is copy-paste text — no files generated.

1. Top-down shape (from the doc)
User Intent  →  Intelligence (LLM parse)  →  Acquisition (collectors)
             →  Data Engineering (clean/dedupe)  →  Persistence (Postgres)
             →  Delivery (dashboard)

Four natural work-streams fall out of that pipeline, and they map cleanly onto 4 feature branches:

Branch	Covers (doc sections)	Roadmap days
feat/backend-core	FastAPI skeleton, Pydantic contract models, Postgres schema, Procrastinate job queue	§8, §13, §19 steps 1–3, 6
feat/llm-pipeline	Structured-output query parser, source registry + routing, confidence scoring	§5, §6.1
feat/data-collection	Playwright/BeautifulSoup collectors, cleaning/normalization, pg_trgm dedup	§6, §7
feat/frontend-dashboard	Query input, SSE progress, results table, CSV export, queries/tasks history + re-run	§9, §10

main stays the protected integration branch — nothing gets pushed to it directly, only merged via PR once tests pass (§14).

2. Repo scaffold (monorepo, per §19's Day-1 checklist)
orbis-labs/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   │   ├── queries.py        # POST /api/queries, GET /{id}, /results, /stream
│   │   │   └── sources.py        # GET /api/sources, /api/projects
│   │   ├── models/
│   │   │   ├── schemas.py        # QueryPlan, QueryFilters, AmbiguityFlag, SourceDescriptor
│   │   │   └── db.py             # SQLModel: users, projects, queries, records, sources
│   │   ├── llm/parser.py         # structured-output parser (§5)
│   │   ├── collectors/
│   │   │   ├── registry.py       # SOURCE_REGISTRY (§6.1)
│   │   │   ├── internshala.py
│   │   │   └── careers_page.py
│   │   ├── processing/
│   │   │   ├── clean.py          # §7.1
│   │   │   ├── validate.py       # §7.2
│   │   │   └── dedup.py          # §7.3, pg_trgm
│   │   ├── jobs/tasks.py         # Procrastinate tasks
│   │   └── core/{config.py,db_session.py}
│   ├── fixtures/{source_a.json,source_b.json}
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── QueryInput.tsx
│       │   ├── ProgressStream.tsx   # SSE consumer
│       │   ├── ResultsTable.tsx
│       │   └── QueriesList.tsx      # §10 history/re-run screen
│       ├── api/client.ts
│       └── App.tsx
├── .github/workflows/ci.yml         # pytest on push (§19 step 7)
├── docker-compose.yml
└── README.md
3. Git setup — main + 4 feat branches

One important ordering note first: backend/app/models/schemas.py (the Pydantic models) is the shared contract every other branch depends on. Land that on main before branching, or the other three branches will conflict with each other rewriting the same file.

bash
mkdir orbis-labs && cd orbis-labs
git init
git branch -M main

# --- Step A: seed main with the shared contract only ---
# (scaffold repo dirs, write schemas.py + empty stubs, one commit)
git add -A
git commit -m "chore: repo scaffold + shared Pydantic contract (schemas.py)"

# --- Step B: cut the 4 feature branches from that main ---
git checkout -b feat/backend-core
git checkout main

git checkout -b feat/llm-pipeline
git checkout main

git checkout -b feat/data-collection
git checkout main

git checkout -b feat/frontend-dashboard
git checkout main

git branch   # should list: main, feat/backend-core, feat/llm-pipeline, feat/data-collection, feat/frontend-dashboard

# --- Step C: push everything ---
git remote add origin <your-repo-url>
git push -u origin main
git push -u origin feat/backend-core
git push -u origin feat/llm-pipeline
git push -u origin feat/data-collection
git push -u origin feat/frontend-dashboard
4. Codex briefs — paste one per branch when you switch to it

feat/backend-core:

Scaffold a FastAPI app in backend/app/. Add SQLModel tables for users, projects, queries, records, sources per the schema in doc §8 (note: stipend should be JSONB, not TEXT — see §8.3). Set up Procrastinate as a Postgres-backed job queue (no Redis), wired as an async worker alongside the FastAPI app. Add alembic migrations. Enable pg_trgm and pgcrypto extensions. Response envelope for all endpoints: {"success": true, "data": {}} / {"success": false, "error": "..."}.

feat/llm-pipeline:

Using the shared QueryPlan/QueryFilters/AmbiguityFlag/SourceDescriptor models in models/schemas.py, build a structured-output query parser (Anthropic tool-use or OpenAI response_format) per §5. Include ambiguity_flags handling (§5.5) and a deterministic (non-LLM) confidence scorer per §5.6's formula. Then add the rule-based source-routing function from §6.1: match filters.role/intent against SOURCE_REGISTRY[*].handles to pick collector(s) — no LLM judgment in this step.

feat/data-collection:

Build two collectors (Playwright-Python + httpx/BeautifulSoup) against the fixture files in backend/fixtures/ first, per §19 step 5 — real scraping comes after fixtures pass. Implement cleaning/normalization (§7.1: currency, location aliasing, ISO dates), validation (§7.2: flag failures, don't drop), and dedup (§7.3: composite key first, pg_trgm fuzzy pass second, keep all source associations per duplicate group).

feat/frontend-dashboard:

React + TS UI: query input box, a ProgressStream component consuming GET /api/queries/{id}/stream (SSE, §9), a results table with CSV export, and the Queries/Tasks list screen from §10 — status column, source(s) used, record count, and a re-run button that resubmits the same filters as a new query_id (never mutates the old run).

5. Merge order that avoids pain

Since feat/data-collection and feat/llm-pipeline both read SOURCE_REGISTRY and feat/frontend-dashboard depends on the API shape from feat/backend-core, the least painful merge order is: backend-core → llm-pipeline → data-collection → frontend-dashboard, rebasing each remaining branch onto main after the prior one lands, rather than merging all 4 simultaneously at the end.
