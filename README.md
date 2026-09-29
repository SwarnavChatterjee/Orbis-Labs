<div align="center">

# 🌐 Orbis Labs

**Source-backed AI data intelligence. Describe what you're looking for in plain English, get clean, deduplicated results with full provenance.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/status-active%20MVP-orange)

[Overview](#overview) · [Architecture](#architecture) · [Quick Start](#quick-start) · [Configuration](#configuration) · [API](#api-reference) · [Testing](#testing) · [Contributing](#contributing)

</div>

---

## Overview

Orbis Labs turns a natural-language search into a validated, source-backed dataset.

1. **Describe** a job or internship search, e.g. *"remote ML internships in India requiring Python"*.
2. **Plan**: OpenAI interprets your intent into a typed `QueryPlan`.
3. **Collect**: registered Python collectors fetch records from approved sources only.
4. **Clean**: records are validated, normalized, scored, and deduplicated.
5. **Explore**: browse searchable results, each with source identity, URL, and retrieval timestamp.

> The current MVP focuses on **internships and jobs**, while the data contract is designed to extend to other domains.
>
> *Older docs may refer to this project as "AI Data Intelligence Platform" or "Data Intel Platform". They are the same project.*

### Product principles

- **Natural language in, structured data out.** No source-specific query syntax.
- **The LLM plans, it doesn't fetch.** OpenAI produces a typed `QueryPlan` and never chooses arbitrary URLs.
- **Provenance everywhere.** Every result keeps its source, URL, and retrieval information.
- **Python is authoritative** for routing, validation, cleaning, deduplication, confidence, and persistence.
- **Transparent by design.** Users can inspect query status, sources, and raw result data instead of receiving an opaque answer.

---

## Architecture

```mermaid
flowchart TD
    UI["React + TypeScript<br/>(Vite)"] -- "HTTP · OAuth redirect · SSE" --> API["FastAPI API"]
    API <--> DB[("PostgreSQL<br/>queries · users · records · events")]
    API -- enqueue --> Q["Procrastinate queue"]
    Q <--> DB
    Q --> W["Separate worker<br/>plan → collect → clean → persist"]
    W --> R["Collector registry"]
    R --> S1["Internshala"]
    R --> S2["Greenhouse API"]
    W -. "planning only" .-> OAI["OpenAI"]
```

OpenAI is used **only** at the planning boundary. Registered Python collectors are the **only** permitted route to external sources.

### Query lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running
    running --> planned
    planned --> collecting
    collecting --> cleaning
    cleaning --> completed
    cleaning --> failed
    completed --> [*]
    failed --> [*]
```

The API persists a query **before** enqueueing work. The worker records status events and stores safe, public error messages: no credentials, SQL, provider details, or stack traces.

### Processing pipeline

```text
collector output
  → schema validation
  → field normalization
  → confidence calculation
  → deterministic deduplication
  → PostgreSQL persistence with provenance
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLModel, Pydantic Settings |
| Database | PostgreSQL 16, Alembic migrations |
| Jobs | Procrastinate (durable, PostgreSQL-backed) |
| AI | OpenAI structured query planning |
| Auth | Google OAuth 2.0 / OpenID Connect |
| Frontend | React, TypeScript, Vite |
| Testing | pytest, SQLite test DBs, fakes, fixtures |
| Infra | Docker Compose |

---

## Repository structure

```text
backend/app/api/routes/     FastAPI query and authentication routes
backend/app/auth/           Google OpenID Connect integration
backend/app/collectors/     Internshala, Greenhouse, demo, and registry code
backend/app/core/           Settings and database setup
backend/app/jobs/           Procrastinate app and worker tasks
backend/app/llm/            OpenAI planner and evaluation harness
backend/app/models/         SQLModel database and Pydantic contracts
backend/app/processing/     Cleaning and deduplication
backend/alembic/            PostgreSQL migrations
backend/fixtures/           Offline HTML/JSON source fixtures
backend/tests/              API, auth, worker, planner, and contract tests
frontend/src/               React app, API client, and styling
frontend/public/            Static assets
docs/                       Architecture, plans, context, and team prompts
docker-compose.yml          Local PostgreSQL service
.env.example                Safe environment template
CONTRIBUTING.md             Branch and review workflow
```

---

## Quick Start

### Prerequisites

- Git
- Python 3.11+
- Node.js and npm
- Docker Desktop
- Google Cloud OAuth credentials (for sign-in)
- An OpenAI API key (**only** for live planning)

```bash
git --version && python --version && node --version && npm --version && docker compose version
```

### 1. Install dependencies

Run from the repository root.

<details open>
<summary><b>macOS / Linux</b></summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
npm install --prefix frontend
cp .env.example .env
```

</details>

<details>
<summary><b>Windows PowerShell</b></summary>

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
npm install --prefix frontend
Copy-Item .env.example .env
```

</details>

Edit **only** your local `.env`. It is Git-ignored and must never be committed.

### 2. Start PostgreSQL and run migrations

```bash
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U orbis -d orbis_labs
```

<details open>
<summary><b>macOS / Linux</b></summary>

```bash
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app schema --apply
```

</details>

<details>
<summary><b>Windows PowerShell</b></summary>

```powershell
$env:PYTHONPATH = "backend"
alembic -c backend/alembic.ini upgrade head
procrastinate -a app.jobs.tasks.procrastinate_app schema --apply
```

</details>

> The host uses port **5433**; PostgreSQL listens on **5432** inside the container. Data persists in the `orbis-postgres` volume when the container stops.

### 3. Run the app (three terminals)

**API**

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

PowerShell: `$env:PYTHONPATH = "backend"` first, then `uvicorn app.main:app --reload --port 8000`.

| URL | Purpose |
|---|---|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | OpenAPI UI |
| `http://localhost:8000/openapi.json` | OpenAPI JSON |

**Worker**

```bash
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app worker queries
```

> ⚠️ The worker must be running for submitted queries to leave `queued`. API and worker must share the same database.

**Frontend**

```bash
npm run dev --prefix frontend
```

Open **http://localhost:5173**. The landing page is public; the workspace at `/app` requires an authenticated session. Sign-in starts on the landing page.

Production build: `npm run build --prefix frontend`

---

## Configuration

Copy [`.env.example`](.env.example) to `.env`:

```env
APP_NAME=Orbis Labs
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://orbis:orbis@localhost:5433/orbis_labs
OPENAI_API_KEY=
OPENAI_MODEL=gpt-6-astra
DEMO_MODE=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
SESSION_SECRET=replace-with-a-long-random-value
FRONTEND_URL=http://localhost:5173
```

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Database used by API and worker |
| `OPENAI_API_KEY` | Live OpenAI planner credential. **Keep server-side.** |
| `OPENAI_MODEL` | Planner model (use one available to your account) |
| `DEMO_MODE` | Predictable local demo behavior where supported |
| `GOOGLE_CLIENT_ID` | Google Web OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Confidential Google OAuth credential |
| `GOOGLE_REDIRECT_URI` | Exact OAuth callback URL |
| `SESSION_SECRET` | Local session signing secret |
| `FRONTEND_URL` | Redirect destination after authentication |

**Generate a session secret**

```bash
# macOS / Linux
openssl rand -hex 32
```

```powershell
# Windows PowerShell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
```

Each developer should use a **different** session secret. Never share `.env`, OpenAI keys, session secrets, or Google client secrets.

---

## Google authentication

The backend uses a **server-side authorization-code flow**. The frontend never receives the Google client secret.

1. In Google Cloud Console, select the Orbis Labs project.
2. Configure the OAuth consent screen in **Google Auth Platform**.
3. Choose **External** for personal or mixed Google accounts.
4. While in *Testing*, add every teammate's exact Google email under **Test users**.
5. Create a **Web application** OAuth client.
6. Add this exact authorized redirect URI:
   ```text
   http://localhost:8000/api/auth/google/callback
   ```
7. Put credentials only in each developer's local `.env`.

Use **Internal** only when every permitted user belongs to the same Workspace/Cloud Identity organization. See [Google's audience documentation](https://support.google.com/cloud/answer/15549945?hl=en).

```text
GET  /api/auth/google/login
GET  /api/auth/google/callback
GET  /api/auth/me
POST /api/auth/logout
```

The callback requires a **verified** Google email.

---

## OpenAI planner

The planner converts natural-language input into a validated `QueryPlan`, handling intent, role, location, skills, work mode, compensation, and ambiguity flags.

It is **not** trusted to introduce source URLs or bypass registered routing. Python controls:

- source IDs and URLs
- collector selection
- validation and normalization
- confidence scoring
- deduplication
- persistence and error handling

Configure live planning:

```env
OPENAI_API_KEY=your_local_key
OPENAI_MODEL=the_model_available_to_your_account
```

Offline planner tests use fake clients and need no key or network. To run the evaluation harness (requires a key):

```bash
PYTHONPATH=backend python -m app.llm.evaluate
```

Cases live in `backend/app/llm/evaluation_cases.json`. **Never** put an OpenAI key in frontend code or source control.

---

## Data sources

Only explicitly registered collectors can run.

| Source | Type | Offline fixture |
|---|---|---|
| **Internshala** | Scraper-backed | HTML |
| **GitLab Greenhouse board** | API-backed | JSON |

Every record retains **source identity**, **source URL**, and **retrieval timestamp**. Fixtures make collector changes testable without depending on public websites.

> **Before live collection**, review each source's terms, robots rules, rate limits, endpoint behavior, and attribution requirements.

---

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/queries` | Validate, persist, and enqueue a query |
| `GET` | `/api/queries` | Paginated query history |
| `GET` | `/api/queries/{id}` | Query status and metadata |
| `GET` | `/api/queries/{id}/results` | Paginated, query-scoped results |
| `GET` | `/api/queries/{id}/sources` | Sources used by a query |
| `GET` | `/api/queries/{id}/stream` | Persisted progress events over SSE |
| `POST` | `/api/queries/{id}/rerun` | New query from previous input |
| `GET` | `/api/sources` | Registered source descriptors |

Errors use a consistent envelope. Pagination and filters are bounded. Reruns create **new** queries and never modify the original history or results.

---

## Testing

```bash
# Backend
PYTHONPATH=backend pytest backend/tests -q

# Frontend build
npm run build --prefix frontend

# Whitespace / diff hygiene
git diff --check
```

Tests use SQLite, fake planners, fake collectors, fixtures, and test clients, so they don't normally need Docker, OpenAI, Google, or the public internet.

PostgreSQL migrations, the Procrastinate schema, retries, and worker behavior still require **Docker verification**.

### Demo mode

For a predictable presentation:

```env
DEMO_MODE=true
```

Demo mode is for development and presentations. It does not replace live source validation, OpenAI testing, PostgreSQL verification, or compliance review.

---

## Contributing

Keep `main` stable and use focused branches:

```text
feat/frontend-dashboard
feat/api-backend
feat/openai-planner
fix/<short-description>
```

Before opening a pull request:

```bash
git status
git diff --check
PYTHONPATH=backend pytest backend/tests -q
npm run build --prefix frontend
```

Never commit `.env`, credentials, database dumps, Docker volumes, `node_modules`, virtual environments, build output, or screenshots containing tokens. Review diffs before merging and verify migrations against PostgreSQL. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| **PostgreSQL fails** | Run `docker compose ps` and `docker compose exec postgres pg_isready -U orbis -d orbis_labs`; confirm host port `5433`. |
| **Queries stay `queued`** | Apply the Procrastinate schema, start the worker, and confirm API and worker share the same `DATABASE_URL`. |
| **Teammate can't sign in** | Set Google audience to **External**, add their email as a test user, and verify the exact callback URI. |
| **"Access blocked" from Google** | Audience / test-user configuration issue (see above). |
| **Redirect URI mismatch** | The callback URL must match character-for-character. |
| **Profile picture missing** | Sign out and back in after the avatar migration; initials are the fallback. |
| **OpenAI errors** | Verify the backend `OPENAI_API_KEY`, model availability, and restart the API after editing `.env`. |
| **Frontend is stale** | Restart Vite, hard-refresh the browser, and confirm ports `5173` and `8000`. |

---

## Documentation

- [Architecture summary](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Current project context](docs/current-context.md)
- [Complete architecture guide](docs/reference/orbis-labs-architecture-guide.md)
- [Complete implementation plan](docs/reference/orbis-labs-implementation-plan.md)
- [Repository translation](docs/reference/orbis-labs-repo-translation.md)
- [Backend operations](backend/README.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Team prompts](docs/team-prompts/)

---

## Responsible use

Orbis Labs is an active project. Collectors must be operated only where permitted by the relevant source terms, policies, and law. **Adding a source is an engineering and compliance decision, not merely a parser change.**

---

<div align="center">
<sub>Built with FastAPI, React, PostgreSQL, and a healthy respect for source terms.</sub>
</div>
