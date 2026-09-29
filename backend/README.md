# API backend operations

The API persists each query before enqueueing it, then schedules a Procrastinate
job in PostgreSQL. Run the API and worker as separate processes. Install the
Python requirements first, including the Psycopg 3 pool used by Procrastinate.

```powershell
pip install -r backend/requirements.txt
$env:PYTHONPATH = "backend"
uvicorn app.main:app --reload
```

Initialize the existing Alembic schema and Procrastinate's job tables in a
PostgreSQL database before starting the worker:

```powershell
$env:PYTHONPATH = "backend"
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app schema --apply
PYTHONPATH=backend procrastinate -a app.jobs.tasks.procrastinate_app worker queries
```

Google authentication requires the `0003_google_identity` migration and these
local environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_REDIRECT_URI`, `SESSION_SECRET`, and `FRONTEND_URL`. The callback URI
must exactly match the Web OAuth client configuration in Google Cloud Console.

Only explicitly registered collectors are eligible for source routing. The
default registry contains the two approved MVP sources: Internshala and
GitLab's Greenhouse job board. Collectors are sync or async callables receiving
a validated `QueryPlan` and `SourceDescriptor`, and returning validated
`Record` objects. Fixture parsers are tested before live HTTP calls are used.

The live collectors are intentionally conservative: they only request the
configured source endpoints, apply the parsed filters, and preserve the source
URL and retrieval timestamp on every record. Review source terms, robots rules,
rate limits, and endpoint availability before production use.

Tests create isolated SQLite tables from SQLModel metadata and inject fake
planners and collectors. The original `0001_initial` migration creates
PostgreSQL JSONB columns and enables PostgreSQL extensions, so the full Alembic
chain, Procrastinate schema, retry behavior, and worker-to-PostgreSQL path still
require verification against PostgreSQL. SQLite results are not proof of those
PostgreSQL-specific behaviors.
