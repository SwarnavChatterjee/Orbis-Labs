# Orbis Labs — Complete Architecture Guide

*A consolidated technical reference covering the original proposal, an engineering critique, a leaner MVP architecture, and a deep dive on structured LLM parsing.*

---

## 1. What this system is

At its core, this is an **intelligent ETL pipeline with a natural-language front door and source-backed data delivery**. A user types a plain-English data request; the system turns that into a structured plan, collects data from permitted sources, cleans and deduplicates it, stores it, and hands back a searchable, exportable, source-attributed dataset.

It is explicitly **not**:
- A chatbot that answers from memory
- A single-purpose web scraper
- A RAG system whose final output is an LLM-generated paragraph

The LLM's job is narrow and important: turn fuzzy language into structured intent, and optionally help extract fields from messy text. It does not invent records — every row in the final dataset must trace back to a real collected source.

**The mental model, end to end:**

1. **User intent** — a person describes the data they want in plain English.
2. **Intelligence** — an LLM converts that into structured intent and a collection plan.
3. **Acquisition** — collectors pull data from permitted external sources.
4. **Data engineering** — validation, normalization, and deduplication turn raw scrapes into trustworthy records.
5. **Persistence** — PostgreSQL stores query metadata, records, and source references.
6. **Delivery** — a dashboard lets the user search, filter, review sources, and export.

---

## 2. The originally proposed architecture

The source Executive Summary proposes six modular components:

| Layer | Proposed technology | Responsibility |
|---|---|---|
| Frontend | React + TypeScript | Query input, progress, results table, CSV export |
| Backend API | **Python (FastAPI)** | Auth, REST endpoints, pipeline orchestration |
| LLM service | OpenAI or Anthropic API | Query parsing; optional field extraction |
| Collector | Playwright (Python), `requests` + BeautifulSoup, official APIs | Retrieve raw data from permitted sources |
| Processing | `pydantic` validation + fuzzy matching | Clean, validate, and deduplicate records |
| Database | PostgreSQL (+ optional Qdrant) | Structured storage, full-text or semantic search |

> **Stack note:** this document originally discussed a Node/Express or Next.js backend. The person building this has chosen **Python (FastAPI)** as the backend, so every section below reflects that choice — Pydantic instead of Zod, Playwright-Python/BeautifulSoup instead of Cheerio, and a Postgres-backed Python job queue instead of `pg-boss`.

**Deployment target:** Docker containers, backend on Heroku/AWS, frontend on Netlify/Vercel, CI/CD via GitHub Actions.

**Timeline:** 9 days, one layer (roughly) per day, ending in a demo that runs one realistic query end-to-end and produces ~5 structured, exportable records.

This is a sound *target* architecture for a production system. The issue is fitting all of it — two deployment targets, an undecided job-queue technology, an optional vector database, and a from-scratch scraper — into 9 days without something breaking under time pressure.

---

## 3. Engineering critique

**Strength:** the document correctly separates concerns (parsing vs. collection vs. cleaning vs. storage vs. presentation), which is the right shape for a system whose value is *data trustworthiness*, not just "an LLM did something."

**Risk 1 — too many moving services for the timeline.** Frontend + backend as separate deploys, an unfinalized background-job mechanism, and an optional vector database each add setup and integration time that isn't really optional under a 9-day clock.

**Risk 2 — the riskiest component (scraping) is scheduled latest (Day 4).** Site blocking, layout drift, and robots.txt restrictions are exactly the kind of failure that needs early discovery, not a Day 4 surprise with 5 days left.

**Risk 3 — free-text LLM parsing is underspecified.** "Send a prompt, get JSON back" without a schema contract is a recurring source of subtle bugs: missing fields, inconsistent key names, the model wrapping JSON in prose. Section 5 goes deep on the fix.

**Risk 4 — the schema mismatch.** The database schema defines `stipend TEXT`, but the illustrative "clean record" example nests stipend as `{amount, currency, period}`. This kind of drift between what's designed and what's built is normal in a fast build — but it should be resolved on Day 1–2, not discovered on Day 6 during integration.

---

## 4. A leaner MVP architecture

The core simplification: **collapse two deploys and three infrastructure services into one app and one datastore.**

```
┌───────────────────────────┐        ┌───────────────────────────────────┐
│  React + TS frontend       │  HTTP  │  FastAPI backend (single service)  │
│  Query UI, results table,  │◀──────▶│  Routers ──▶ Postgres job queue    │
│  progress, CSV export      │        │  (pydantic-  (Procrastinate,       │
│                             │        │   validated)  no Redis)            │
└───────────────────────────┘        └───────────────────────────────────┘
                                                      │
                                                      ▼
                                       ┌───────────────────────────────────┐
                                       │  LLM parser ─▶ Collector ─▶ Clean  │
                                       │  (structured    (Playwright-Py /   │
                                       │   output,        BeautifulSoup,    │
                                       │   pydantic)       1–2 sources)     │
                                       └───────────────────────────────────┘
                                                      │
                                                      ▼
                                       ┌───────────────────────────────────┐
                                       │  PostgreSQL                        │
                                       │  records, sources, queries          │
                                       │  + pg_trgm fuzzy match + tsvector   │
                                       └───────────────────────────────────┘
```

### What changed, and why

| Original | Leaner MVP (Python backend) | Why |
|---|---|---|
| Node/Express or ad-hoc FastAPI as an alternative | **FastAPI as the primary backend**, async-native | FastAPI's async request handlers pair naturally with async scraping (Playwright-Python, `httpx`) and async LLM calls, all in one language as the collector |
| React SPA + separate Express API, two hosts | React SPA + FastAPI, still two processes but one Docker image (FastAPI serves the built React bundle as static files, or a thin reverse proxy in front of both) | Python can't run a Next.js-style single-process monolith, so the simplification here is *one deployable image*, not *one process* |
| Undecided job queue (Redis/BullMQ implied) | **Procrastinate** (Postgres-backed task queue for Python) — or `arq`/Celery with Redis if you're already comfortable with that stack | Procrastinate keeps the "no new infrastructure" property `pg-boss` gave the Node version: your job queue lives in the Postgres you already have |
| Optional Qdrant vector DB | Skipped entirely for MVP | `pg_trgm` + `tsvector` cover fuzzy dedupe and keyword search in the same datastore, and are called from Python via SQLAlchemy/`asyncpg` the same way |
| Free-text LLM JSON parsing (Zod validation) | Schema-constrained structured output, validated with **Pydantic** | Pydantic models double as your FastAPI request/response schemas *and* your LLM-output schema — one model, not one Zod schema plus a separate Python type |
| Scraper validated on Day 4 | Scraper validated Day 1–2, against 10 real records | Still the same recommendation, independent of language |
| Polling for progress | Server-Sent Events via FastAPI's `StreamingResponse` | FastAPI has first-class support for SSE without extra libraries |

This is not a rejection of the original design — it's the same six responsibilities (parse, collect, clean, dedupe, store, present), just packed into fewer physical services so a 9-day team spends its time on the parts that differentiate the product (data quality, provenance, dedupe) rather than on infrastructure glue.

---

## 5. Structured LLM parsing — deep dive

This is the layer that turns "Find 50 software engineering internships in Bangalore for 2027 graduates" into something a collector can execute deterministically. Getting this right early removes downstream ambiguity from every later stage.

### 5.1 The problem with plain prompting

A prompt like *"Extract the search parameters from this query and return JSON"* will usually work — until it doesn't. Common real-world failure modes:

- The model wraps the JSON in a sentence ("Here's the extracted data: {...}")
- A field is renamed inconsistently across calls (`grad_year` vs `graduation_year`)
- An optional field is omitted instead of set to `null`
- The model infers a field that wasn't in the query at all (silent hallucination of intent)
- Minor formatting differences (trailing commas, single quotes) break a naive `JSON.parse`

None of these are exotic edge cases — they show up within the first few dozen real queries. The fix is to stop asking nicely and start constraining the output mechanically.

### 5.2 Constrained structured output

Both major providers support forcing a model's output to conform to a schema, and both have clean Python SDKs for it:

- **OpenAI (Python SDK):** define the query plan as a `pydantic.BaseModel` and pass it directly as `response_format` via `client.beta.chat.completions.parse(response_format=QueryPlan, ...)`, or use `response_format={"type": "json_schema", "json_schema": {...}, "strict": True}` for finer control. The `openai` Python client will deserialize the response straight into your Pydantic model.
- **Anthropic (Claude, Python SDK):** tool-use / function-calling with a strict `input_schema` — define a tool such as `submit_query_plan` whose `input_schema` is generated from the same Pydantic model (`QueryPlan.model_json_schema()`), and the model's only way to "respond" is to call that tool with schema-conforming arguments.
- **Optional:** the `instructor` library patches either SDK to accept a Pydantic model directly and handles retries automatically when the model's output fails validation — useful if you don't want to hand-roll the retry loop described in 5.4.

Either approach converts "hope the model formats JSON correctly" into "the API layer enforces the shape." You still validate afterward with the same Pydantic model (schemas can technically be satisfied with nonsensical values, e.g. a `graduation_year` of `1899`), but you eliminate the entire category of malformed-output bugs.

### 5.3 Designing the schema

Two design decisions matter more than the field list itself:

**1. Separate "what the user asked for" from "how we'll go get it."** The document's own distinction between *filters* and a *query plan* is the right instinct — keep them as separate sections of one Pydantic model, which then becomes both the LLM's output contract and a FastAPI response model:

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
    ambiguity_flags: list[AmbiguityFlag] = Field(default_factory=list)
```

`filters` is what the LLM is confident it extracted. `ambiguity_flags` (see 5.5) is what it wasn't. Keeping these separate means a downstream collector never has to guess which fields are solid and which are the model's best effort.

**2. Make every optional field genuinely nullable in the schema**, not just "sometimes present." With `strict: true` structured outputs, an undeclared-but-sometimes-missing field is a schema violation waiting to happen. Explicit nulls (`"graduation_year": null`) are far easier to handle downstream than a field that sometimes doesn't exist in the object at all.

### 5.4 A concrete parsing flow

1. **System prompt** defines the schema contract explicitly (even redundantly, alongside the API-level schema) and gives 2–3 few-shot examples covering a clean case, an ambiguous case, and a case with an unsupported field.
2. **API call** uses structured output / tool-use so the response is guaranteed schema-shaped.
3. **Runtime validation** — even with strict mode, re-validate with the same Pydantic model your FastAPI routes and database layer use (e.g. via `sqlalchemy`/`sqlmodel`). One model definition, enforced in three places (API request/response validation, LLM output validation, DB write shape) means a schema change is a one-line edit instead of a hunt across the codebase.
4. **Confidence gating** — if required fields are missing or `ambiguity_flags` is non-empty, either ask a clarifying follow-up (if your UI supports it) or proceed with a lower confidence score attached to the whole query, surfaced to the user rather than hidden.

### 5.5 Handling ambiguity without hallucinating certainty

The temptation is to have the model just pick its best guess silently. Don't — that's exactly the "AI made something up" failure mode the whole platform exists to avoid. Instead, have the schema include a place for the model to flag what it *wasn't* sure about:

```json
{
  "ambiguity_flags": [
    { "field": "location", "reason": "query said 'Bengaluru', normalized to 'Bangalore'" }
  ]
}
```

This turns silent inference into visible, auditable normalization — which lines up directly with the platform's core differentiator: provenance and trust, not just "the AI found some stuff."

### 5.6 Confidence scoring should not come from the LLM

A subtle but important point: don't ask the model to self-report a confidence score for the *whole pipeline*. It's grading its own homework, and LLM-reported confidence is notoriously miscalibrated. Instead, compute confidence deterministically downstream, after cleaning and validation:

```
confidence = 1.0
  - (missing_required_fields / total_required_fields) * 0.5
  - (regex_validation_failures) * 0.1
  - (0.2 if ambiguity_flags is non-empty else 0)
```

This is cheap, explainable to a user ("this record is missing a deadline, so confidence is lower"), and doesn't depend on the LLM being honest about its own uncertainty.

### 5.7 Where the LLM's second job fits in

The document also proposes an optional second LLM responsibility: extracting fields from *already-scraped* raw text, for sources where code-based extraction (CSS selectors, regex) isn't reliable. The same structured-output approach applies here — the extraction call should return the same record schema the cleaning layer expects, not free text to be re-parsed. Treat it as "one more producer of the same typed record," not a special case.

**Guardrail:** this extraction step should never be allowed to *add* a record — only to fill in fields for a record whose existence (company + role + source URL) was already established by the collector. That boundary is what keeps "the LLM helps read messy HTML" from sliding into "the LLM invents an internship listing."

---

## 6. Data collection and dynamic workflow selection

**Tools:** Playwright-Python for dynamic/JS-heavy sites (`playwright.async_api`, pairs naturally with FastAPI's async handlers), `httpx` + BeautifulSoup for simple HTTP + HTML parsing, official APIs preferred wherever one exists.

**Commit to at least two sources for the demo, not one.** PS1 explicitly asks for collection from "multiple permitted sources" — a single hardcoded source under-delivers on the stated goal even if it's the safer 9-day choice. Two sources (e.g. Internshala + one company careers page, or Internshala + a general search-API fallback) is enough to demonstrate multi-source collection and deduplication across sources without ballooning scope.

**Source compliance is a first-class concern, not an afterthought:**
- Check `robots.txt` programmatically before the first request to any new source — a policy note in a doc doesn't enforce anything; a code check does.
- Prefer 1–2 stable sources over broad coverage. The document is explicit about this trade-off, and it's the right call under a 9-day clock.
- Log retrieval metadata (URL, timestamp) on every fetch — this is what powers provenance later.

**Validate against fixtures before validating against the live site.** Manually pull ~10 real records on Day 1, save them as fixture data, and build the parsing/cleaning/dedupe pipeline against those fixtures first. This decouples "does my pipeline logic work" from "is the live site blocking me today" — two very different failure modes that are easy to conflate when debugging under time pressure.

### 6.1 Source registry and dynamic workflow selection

PS1 explicitly asks the platform to **"dynamically create and execute an appropriate data-collection workflow"** — not always run the same fixed steps against the same fixed source. The lean architecture as first designed didn't cover this: it had one collector, chosen in advance. This is the one real gap against the problem statement, and the fix does not require reintroducing an open-ended agent loop (which would undo the predictability the rest of the design is built around).

**The pattern: a small, typed source registry, chosen by the query plan, executed deterministically.**

```python
class SourceDescriptor(BaseModel):
    id: str
    name: str
    handles: list[str]        # e.g. ["internship", "software_engineering"]
    collector: str            # dotted path to the collector function

SOURCE_REGISTRY: list[SourceDescriptor] = [
    SourceDescriptor(id="internshala", name="Internshala",
                      handles=["internship"], collector="collectors.internshala.run"),
    SourceDescriptor(id="careers_page", name="Company careers pages",
                      handles=["internship", "full_time"], collector="collectors.careers.run"),
]
```

Extend the `QueryPlan` schema from Section 5 with a `sources` field, populated one of two ways:

1. **Rule-based (recommended for the 9-day build):** after parsing, a small deterministic function matches `filters.role`/`intent` against each `SourceDescriptor.handles` and selects the matching collector(s). No LLM judgment involved — simple, testable, and still satisfies "the platform designs a workflow per request" because different requests genuinely route to different sources.
2. **LLM-selected (a step further, if time allows):** the LLM itself picks from the registry's `id` values as part of its structured output — the registry, not free text, is what constrains the choice, so the result is still schema-bound.

Either way, **only the "which source(s) to call" decision is dynamic.** Execution after that point — collect → clean → dedupe → store — stays the same fixed sequence for every query. That's what keeps this "workflow design," not an unpredictable agent.

---

## 7. Cleaning, validation, and deduplication

### 7.1 Normalization

| Raw value | Normalized |
|---|---|
| ₹20,000 per month | Numeric amount + currency + period |
| Bengaluru | Bangalore (if a location alias map is configured) |
| 30 June 2027 | `2027-06-30` (ISO date) |
| Not specified | `null` |

### 7.2 Validation

Deterministic rules, not LLM judgment: required fields present, date fields parse to valid dates, URLs match a URL pattern, stipend normalizes to a numeric+currency shape. Records that fail get flagged (not silently dropped) so the failure rate itself is visible as a data-quality metric.

### 7.3 Deduplication

**Composite key** (company + role + location) for a first pass, **fuzzy similarity** for near-duplicates ("Google" vs "Google India"), and a **canonical record** chosen per duplicate group.

**Recommendation beyond the original document:** don't destroy source evidence when merging duplicates. A duplicate from a second source can still be useful — it might have a working application link when the first source's link is dead, or it can serve as independent verification. Keep every source association even when only one record is shown as canonical.

**Implementation note:** PostgreSQL's `pg_trgm` extension does trigram similarity matching *inside the database*, avoiding a separate fuzzy-matching library and keeping the comparison logic close to the data it's comparing.

---

## 8. Database

### 8.1 Core entities

`users → projects → queries → records ← sources`

- **Users** — authenticated identities.
- **Projects** — optional grouping of queries.
- **Queries** — original NL text, parsed parameters (JSONB), status, timestamps.
- **Records** — one structured row per collected item, with a foreign key to its query.
- **Sources** — normalized source names/base URLs, referenced by many records.

### 8.2 Indexing

- B-tree indexes on `company` and `location` for exact/prefix filters.
- `GIN` index (via `pg_trgm`) for fuzzy company/role matching used in dedup.
- `tsvector` full-text index across role + description for keyword search.

This combination covers both the MVP's stated search need (full-text) and its dedup need (fuzzy match) without a second datastore.

### 8.3 Schema note

Resolve the `stipend TEXT` vs. structured `{amount, currency, period}` mismatch on Day 1–2. A `JSONB` column for stipend gives you structure without a rigid schema migration if the format varies by source.

---

## 9. API layer

Consistent envelope for every response:

```json
{ "success": true, "data": {} }
{ "success": false, "error": "message" }
```

**Core endpoints:**

| Method / path | Purpose |
|---|---|
| `POST /api/queries` | Submit a natural-language query, returns `{queryId, status: "accepted"}` |
| `GET /api/queries/{id}` | Poll status (or subscribe via SSE — see below) |
| `GET /api/queries/{id}/results` | Paginated, cleaned, deduplicated records |
| `GET /api/queries/{id}/stream` | SSE stream of pipeline stage updates |
| `GET /api/projects`, `GET /api/sources` | Optional listing endpoints |

**Async execution, done simply:** the document correctly identifies that a long-running scrape shouldn't block an HTTP request. **Procrastinate** gives you that without adding Redis — jobs are rows in your existing Postgres, picked up by an async worker process (for a 9-day MVP, this can run as a background task started alongside your FastAPI app with `asyncio.create_task`, or as Procrastinate's own worker command in the same container).

**SSE over polling for progress:** a single open connection pushing `"Parsing query…" → "Collecting data…" → "Cleaning data…"` events is simpler to implement than it sounds, and avoids the frontend re-polling a status endpoint every second.

---

## 10. Task management, history, and demo scope

PS1 names two goals that got quietly pushed to "optional" in the lean-MVP cut: **"allow users to monitor and manage collection tasks"** and **"maintain workflow and dataset history... revisit previous workflows."** These aren't extras — the `queries` and `projects` tables were already in the Section 8 schema for exactly this reason, so reinstating the UI for them is mostly wiring, not new design.

**Core screen (not optional): Queries / Tasks list**

- One row per submitted query: original NL text, status (`queued` / `running` / `completed` / `failed`), source(s) used (from the Section 6.1 registry selection), record count, submitted-at timestamp.
- A **re-run** action on any past query — re-submits the same `filters` through the pipeline, producing a new `query_id` and a fresh set of records (never mutates the old run, so history stays intact).
- Clicking a row opens that query's results table (the same view the live progress screen transitions into on completion).

**What this buys the demo:** it's a direct, visible answer to "monitor and manage collection tasks" and "revisit previous workflows" — both stated goals, both otherwise invisible in a single-query walkthrough. It's also cheap: the data already exists in `queries`; this is a list view and a re-run button, roughly half a day of frontend work, not a new backend capability.

**Scope boundary for the hackathon:** this stays a flat list with a re-run button — no editing a past query's filters, no branching/forking workflows, no diffing between runs. Those are reasonable v2 ideas but not required by PS1's wording ("monitor," "manage," "revisit," "history" — all satisfied by list + status + re-run).



## 11. Search and indexing

**MVP:** PostgreSQL full-text search (`tsvector`) for keyword queries like "software engineering intern," plus exact filters on company/location/date.

**Deliberately deferred:** semantic/vector search (embeddings + Qdrant). It solves a real problem — matching on meaning rather than keywords — but it's additional infrastructure and setup time that doesn't block the MVP's core promise: a structured, source-attributed dataset the user can search and filter.

**Is this RAG?** Not really, and that's fine. Query parsing (NL → structured filters) is not retrieval-augmented generation. The system becomes RAG-adjacent only if you later add LLM-generated, source-backed summaries on top of the retrieved records — an explicit post-MVP extension, not a requirement.

---

## 12. Provenance and auditability

Every record should be able to answer, without hedging: *where did this come from, and when?*

```
Record #1024
  Company:      ABC Corp
  Role:         Software Intern
  Source:       Internshala
  Source URL:   https://example.com/internship/123
  Retrieved at: 2026-09-23T18:30:00Z
  Confidence:   0.92
```

This is the platform's real differentiator over "an AI chatbot that lists some internships" — a user can click through to verify anything the system shows them, and every record's confidence score is explainable rather than a black box.

---

## 13. Deployment

| Component | MVP choice |
|---|---|
| App | FastAPI backend (Uvicorn/Gunicorn), serving the built React static bundle from the same Docker image for MVP scale |
| Database | Managed Postgres (Railway, Render, Supabase, or Heroku Postgres) |
| Background jobs | **Procrastinate**, running inside the same container as an async worker |
| Scraping | Runs as a Procrastinate job within the app for MVP scale; split into a separate worker container later if scraping volume grows |
| CI/CD | GitHub Actions running `pytest` on push |

A single-host deployment (e.g., Railway or Render with a managed Postgres add-on) is simpler to demo, debug, and iterate on than a split frontend/backend/Heroku/Vercel setup — the split makes sense once the product is past prototype stage, not during a 9-day build.

---

## 14. Testing

- **Unit tests** for the parser (does "2027 grads" resolve to `graduation_year: 2027`?), date/currency normalization, and dedup matching.
- **Integration tests** for the full API → job → DB round trip.
- **Contract tests derived from the shared Pydantic model** — since the same model validates API input/output, LLM output, and DB writes, testing against that model (rather than hand-written assertions scattered across the codebase) keeps Day 8 short. FastAPI's `TestClient` (built on `httpx`) makes API-level tests fast to write.
- **End-to-end**: simulate one real query from submission through to CSV export, e.g. with `pytest` + `httpx.AsyncClient`.

---

## 15. Revised 9-day roadmap

| Day | Focus | Key shift from the original plan |
|---|---|---|
| 1 | Scope, schema design, **manually validate both chosen data sources** by pulling 10 real records by hand from each, sketch the source registry | Scraping risk surfaced immediately, not Day 4; multi-source requirement locked in from the start |
| 2 | FastAPI scaffold, React frontend scaffold, Postgres schema, Procrastinate setup | Job queue lives in Postgres, no Redis to provision |
| 3 | LLM query parser with structured/schema-constrained output | Schema-first, not prompt-and-hope |
| 4 | Collector built against Day 1 fixtures, then pointed at the live source | Decouples pipeline bugs from live-site issues |
| 5 | Cleaning, `pg_trgm`-based dedup, deterministic confidence scoring | No custom fuzzy-matching library needed |
| 6 | API routes, SSE progress stream, full pipeline wired end-to-end | — |
| 7 | Frontend: query input, results table, filters, CSV export | — |
| 8 | Unit/integration/e2e tests, bug fixes, **cache a fallback dataset for demo day** | Demo resilience explicitly planned for |
| 9 | Deploy, docs, demo recording | Single-host deploy simplifies this significantly |

---

## 16. Risks and mitigations (updated)

| Risk | Mitigation |
|---|---|
| Ambiguous natural-language queries | Schema-constrained parsing with explicit `ambiguity_flags`; surface uncertainty rather than silently guessing |
| Scraper blocked or site layout changes | Validate the source on Day 1; keep a fixture/fallback dataset for the demo; respect `robots.txt` programmatically |
| LLM hallucinating data | LLM never originates records — only parses queries or fills fields on records the collector already found; all data traces to a scraped source |
| Over- or under-aggressive deduplication | Rule-based composite key first, fuzzy similarity as a secondary signal via `pg_trgm`; log merge rate as a visible metric |
| Running out of time across too many services | Collapse to one deploy, one datastore, no Redis, no vector DB for MVP |
| Demo-day live failure | Cached fallback dataset from a known-good run |

---

## 17. Open decisions

These remain genuinely open and should be settled early, not mid-build:

- Final field list and exact schema for `stipend` (TEXT vs. structured JSONB)
- Which single source to commit to for the MVP demo, and confirmation of its scraping legality/robots.txt posture
- Whether to add a clarifying-question UX for low-confidence query parses, or simply proceed and surface confidence in the results table
- Post-MVP: when (if ever) to add semantic search, multi-source aggregation, or LLM-generated summaries on top of retrieved records

---

## 18. Summary

The original proposal gets the *shape* of the system right: parse → collect → clean → dedupe → store → present, with provenance running through every stage. The main engineering adjustment for a 9-day build is **infrastructure minimalism** — one deployable image, one datastore doing double duty (relational storage, fuzzy matching, and full-text search), and structured/schema-constrained LLM output instead of free-text JSON parsing. None of this changes what the product *is* — it changes how much of the 9 days gets spent on plumbing versus on the parts that actually make this more than "a prompt sent to an LLM": reliable collection, deterministic data quality, honest confidence scoring, and a fully traceable source for every record.

**Why Python fits this project well:** the scraping/cleaning ecosystem (Playwright-Python, BeautifulSoup, `pandas` for any batch normalization work, `rapidfuzz` if you want a fuzzy-matching library outside the database) is arguably deeper than the Node equivalent, and Pydantic gives you one schema definition that serves as your API contract, your LLM output contract, and your data validation layer — the same "define it once" property Zod gave the TypeScript version, just in the language actually doing the scraping and cleaning work.

**Against PS1 specifically:** the architecture covers every stated goal. Two items — multi-source collection and task/history management — were quietly narrowed while optimizing for 9 days and are now restored to core scope (Sections 6.1 and 10). The one genuine design gap, dynamic workflow selection, is closed with a typed source registry rather than an open-ended agent, keeping the system's predictability intact while still satisfying "dynamically create and execute an appropriate data-collection workflow" as written.

---

## 19. Initial steps to execute (Day 0 / Day 1 checklist)

A concrete, in-order checklist to actually start building — everything before this point in the document is design; this is the first hour of typing.

1. **Repo and environment**
   ```bash
   mkdir orbis-labs && cd orbis-labs
   git init
   python -m venv .venv && source .venv/bin/activate
   pip install fastapi uvicorn[standard] pydantic sqlmodel asyncpg procrastinate \
               playwright beautifulsoup4 httpx pytest
   playwright install chromium
   npm create vite@latest frontend -- --template react-ts
   ```

2. **Provision Postgres** (Railway, Render, or Supabase — pick one, don't evaluate all three). Enable extensions immediately:
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for UUID defaults if needed
   ```

3. **Write the core Pydantic models first, before any route or collector.** `QueryPlan`, `QueryFilters`, `AmbiguityFlag`, `SourceDescriptor`, `Record` (Section 5.3 and 6.1). These are the contract everything else is built against — get them right before writing logic that depends on them.

4. **Manually validate both data sources by hand** — no code yet. Open each target source in a browser, confirm the data you need is actually visible/reachable, check `robots.txt`, and manually copy 10 real records per source into two JSON fixture files (`fixtures/source_a.json`, `fixtures/source_b.json`). This is the single highest-leverage hour of the whole project: it either confirms the plan works or surfaces a source problem while there are still 8 days to react.

5. **Stub the source registry** (Section 6.1) with both sources' `SourceDescriptor` entries and `collector` functions that, for now, just return the fixture JSON. This lets every later step — parsing, cleaning, dedup, API, frontend — be built and tested against real-shaped data immediately, without depending on live scraping working yet.

6. **Create the `queries`, `records`, `sources` tables** (Section 8) via a migration tool (`alembic` if using SQLModel/SQLAlchemy) and confirm you can write and read one row of each by hand before building any API route on top.

7. **First commit, first CI run.** Push the skeleton, add a GitHub Actions workflow that runs `pytest` on push, even with zero tests yet — this way the pipeline exists before Day 8's testing crunch, not invented that day.

8. **Confirm the LLM call end-to-end**, in isolation, before wiring it into the API: a standalone script that sends one hardcoded query string, gets back a schema-validated `QueryPlan`, and prints it. This isolates "does structured output work with our chosen provider" from every other moving part.

Once steps 1–8 are done, Day 1 of the roadmap in Section 15 is complete and Day 2 (API routes, job queue) has real fixtures, real schemas, and a real database to build against — not placeholders.
