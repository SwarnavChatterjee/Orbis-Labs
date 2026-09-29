# Orbis Labs

Orbis Labs is a source-backed AI data intelligence platform. Users describe a job or internship search in natural language; Orbis Labs converts it into a validated query plan, collects records from approved sources, cleans and deduplicates them, and presents searchable results with provenance.

The official product name is **Orbis Labs**. Older documents may use “AI Data Intelligence Platform” or “Data Intel Platform”; those names refer to this same project.

## Product principles

- Natural-language search instead of source-specific query syntax.
- OpenAI interprets intent into a typed `QueryPlan`; it does not choose arbitrary URLs.
- Every result retains source identity, URL, and retrieval information.
- Python remains authoritative for routing, validation, cleaning, deduplication, confidence, and persistence.
- Users can inspect query status, sources, and result data instead of receiving an opaque answer.

The current MVP focuses on internships and jobs while keeping the contract extensible for future data domains.

## Architecture

```text
React + TypeScript
        │ HTTP, OAuth redirect, SSE
        ▼
FastAPI API ───────────────► PostgreSQL
        │                         │
        │ enqueue                 │ queries, users, records, events
        ▼                         │
Procrastinate queue ◄────────────┘
        │
        ▼
Separate worker
  plan → collect → clean → persist
        │
        ▼
Collector registry
  Internshala + Greenhouse API
```

OpenAI is used at the planning boundary. Registered Python collectors remain the only permitted route to external sources.

### Query lifecycle

```text
queued → running → planned → collecting → cleaning → completed
                                                   └→ failed
```

The API persists a query before enqueueing work. The worker records status events and stores safe public error messages without credentials, SQL statements, provider details, or stack traces.

## Repository structure

```text
backend/app/api/routes/     FastAPI query and authentication routes
backend/app/auth/           Google OpenID Connect integration
backend/app/collectors/     Internshala, Greenhouse, demo, and registry code
backend/app/core/           settings and database setup
backend/app/jobs/           Procrastinate application and worker tasks
backend/app/llm/            OpenAI planner and evaluation harness
backend/app/models/         SQLModel database and Pydantic contracts
backend/app/processing/     cleaning and deduplication
backend/alembic/            PostgreSQL migrations
backend/fixtures/           offline HTML/JSON source fixtures
backend/tests/              API, auth, worker, planner, and contract tests
frontend/src/               React application, API client, and styling
frontend/public/            static assets
docs/                       architecture, plans, context, and team prompts
docker-compose.yml          local PostgreSQL service
.env.example                safe environment template
CONTRIBUTING.md             branch and review workflow
```

## Technology stack

- Python, FastAPI, SQLModel, Pydantic Settings
- PostgreSQL 16 and Alembic
- Procrastinate durable PostgreSQL-backed jobs
- OpenAI structured query planning
- Google OAuth 2.0 / OpenID Connect
- React, TypeScript, and Vite
- pytest, SQLite test databases, fakes, and fixtures
- Docker Compose

## Prerequisites

Install Git, Python 3.11+, Node.js/npm, and Docker Desktop. Google Cloud credentials are required for Google sign-in; an OpenAI API key is required only for live planning.

```bash
git --version
python --version
node --version
npm --version
docker compose version
```

## First-time setup

Run commands from the repository root.

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
npm install --prefix frontend
cp .env.example .env
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\\requirements.txt
npm install --prefix frontend
Copy-Item .env.example .env
```

Edit only the local `.env`. It is ignored by Git and must never be committed.

## Environment configuration

The safe template is [.env.example](.env.example).

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
| `DATABASE_URL` | Database used by API and worker. |
| `OPENAI_API_KEY` | Live OpenAI planner credential. Keep server-side. |
| `OPENAI_MODEL` | Planner model configuration. |
| `DEMO_MODE` | Predictable local demo behavior where supported. |
| `GOOGLE_CLIENT_ID` | Google Web OAuth client identifier. |
| `GOOGLE_CLIENT_SECRET` | Confidential Google OAuth credential. |
| `GOOGLE_REDIRECT_URI` | Exact OAuth callback URL. |
| `SESSION_SECRET` | Local session signing secret. |
| `FRONTEND_URL` | Redirect destination after authentication. |

Generate a local session secret. macOS/Linux:

```bash
openssl rand -hex 32
```

Older Windows PowerShell:

```powershell
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$secret = [System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
$secret
```

Each developer should use a different session secret. Never share `.env`, OpenAI keys, session secrets, or Google client secrets.

## PostgreSQL and migrations

Start PostgreSQL:

```bash
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U orbis -d orbis_labs
```

Apply migrations and initialize Procrastinate:

```bash
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app schema --apply
```

PowerShell:

```powershell
$env:PYTHONPATH = "backend"
alembic -c backend/alembic.ini upgrade head
procrastinate -a app.jobs.tasks.procrastinate_app schema --apply
```

The host uses port `5433`; PostgreSQL listens on `5432) inside the container. Current migrations cover the initial schema, query events, Google identity fields, and user avatars. The `orbis-postgres` volume persists data when the container stops.

## Run the application

Use separate terminals.

### API

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

PowerShell:

```powershell
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload --port 8000
```

Useful URLs:

- Health: `http://localhost:8000/health`
- OpenAPI UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Worker

```bash
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app worker queries
```

The worker must be running for submitted queries to leave `queued`. API and worker must use the same database.

### Frontend

```bash
npm run dev --prefix frontend
```

Open `http://localhost:5173`. The landing page is separate from the protected workspace at `/app`. Google sign-in begins on the landing page and the workspace requires an authenticated session.

Build the frontend:

```bash
npm run build --prefix frontend
```

## Google authentication

The backend uses a server-side authorization-code flow. The frontend never receives the Google client secret.

1. In Google Cloud Console, select the Orbis Labs project.
2. Configure the OAuth consent screen in Google Auth Platform.
3. Choose **External** for personal or mixed Google accounts.
4. While the app is in Testing, add every teammate's exact Google email under **Test users**.
5. Create a Web application OAuth client.
6. Add this exact authorized redirect URI:

   `http://localhost:8000/api/auth/google/callback`

7. Put credentials only in each developer's local `.env`.

Use **Internal** only when every permitted user belongs to the same Workspace/Cloud Identity organization. External apps in Testing are restricted to configured test users. See [Google's audience documentation](https://support.google.com/cloud/answer/15549945?hl=en).

Auth endpoints:

```text
GET  /api/auth/google/login
GET  /api/auth/google/callback
GET  /api/auth/me
POST /api/auth/logout
```

The callback requires a verified Google email. “Access blocked” usually means audience/test-user configuration; redirect URI mismatch means the callback URL differs character-for-character.

## OpenAI planner

The planner converts natural-language input into a validated `QueryPlan`. It handles intent, role, location, skills, work mode, compensation, and ambiguity flags.

It must not be trusted to introduce source URLs or bypass registered routing. Python controls:

- source IDs and URLs;
- collector selection;
- validation and normalization;
- confidence scoring;
- deduplication;
- persistence and error handling.

Configure live planning:

```env
OPENAI_API_KEY=your_local_key
OPENAI_MODEL=the_model_available_to_your_account
```

Offline parser tests use fake clients and need no key or network. Run the evaluation harness with a configured key:

```bash
PYTHONPATH=backend python -m app.llm.evaluate
```

Evaluation cases are in `backend/app/llm/evaluation_cases.json`. Never put an OpenAI key in frontend code or source control.

## Sources and processing

Only explicitly registered collectors can run.

- **Internshala:** scraper-backed source with an offline HTML fixture.
- **GitLab Greenhouse board:** API-backed source with an offline JSON fixture.

Before live collection, review source terms, robots rules, rate limits, endpoint behavior, and attribution requirements.

```text
collector output
  → schema validation
  → field normalization
  → confidence calculation
  → deterministic deduplication
  → PostgreSQL persistence with provenance
```

Every record should retain source identity, source URL, and retrieval timestamp. Fixtures make collector changes testable without depending on public websites.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/queries` | Validate, persist, and enqueue a query. |
| GET | `/api/queries` | Paginated query history. |
| GET | `/api/queries/{id}` | Query status and metadata. |
| GET | `/api/queries/{id}/results` | Paginated query-scoped results. |
| GET | `/api/queries/{id}/sources` | Sources used by a query. |
| GET | `/api/queries/{id}/stream` | Persisted progress events over SSE. |
| POST | `/api/queries/{id}/rerun` | New query from previous input. |
| GET | `/api/sources` | Registered source descriptors. |

Errors use a consistent envelope. Pagination and filters are bounded. Reruns create new queries and do not modify the original history or results.

## Testing

Backend tests:

```bash
PYTHONPATH=backend pytest backend/tests -q
```

Frontend build:

```bash
npm run build --prefix frontend
```

Diff check:

```bash
git diff --check
```

Tests use SQLite, fake planners, fake collectors, fixtures, and test clients. They do not normally require Docker, OpenAI, Google, or public internet. PostgreSQL migrations, Procrastinate schema, retries, and worker behavior still require Docker verification.

## Demo mode

For a predictable presentation:

```env
DEMO_MODE=true
```

Demo behavior is for development and presentations. It does not replace live source validation, OpenAI testing, PostgreSQL verification, or compliance review.

## Team Git workflow

Keep `main` stable. Use focused branches:

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

Never commit `.env`, credentials, database dumps, Docker volumes, `node_modules`, virtual environments, build output, or screenshots containing tokens. Review diffs before merging and verify migrations against PostgreSQL.

## Troubleshooting

**PostgreSQL fails:** run `docker compose ps` and `docker compose exec postgres pg_isready -U orbis -d orbis_labs`; confirm host port `5433).

**Queries remain queued:** apply the Procrastinate schema, start the worker, and confirm API and worker share `DATABASE_URL`.

**Teammate cannot sign in:** set Google audience to External, add the email as a test user, and verify the exact callback URI.

**Profile picture missing:** sign out and sign in again after the avatar migration; initials are the fallback.

**OpenAI fails:** verify the backend's `OPENAI_API_KEY`, model availability, and restart the API after editing `.env).

**Frontend is stale:** restart Vite and hard-refresh the browser; confirm ports `5173) and `8000).

## Documentation map

- [Architecture summary](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Current project context](docs/current-context.md)
- [Complete architecture guide](docs/reference/orbis-labs-architecture-guide.md)
- [Complete implementation plan](docs/reference/orbis-labs-implementation-plan.md)
- [Repository translation](docs/reference/orbis-labs-repo-translation.md)
- [Backend operations](backend/README.md)
- [Contribution workflow](CONTRIBUTING.md)
- [Team prompts](docs/team-prompts/)

## Source responsibility

This is an active project. Collectors must be operated only where permitted by relevant source terms, policies, and law. Adding a source is an engineering and compliance decision, not merely a parser change.
