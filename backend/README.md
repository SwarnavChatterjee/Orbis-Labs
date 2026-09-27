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

Only explicitly registered collectors are eligible for source routing. The
default registry is empty until the project owner approves and registers the
supported sources. Collectors are sync or async callables receiving a
validated `QueryPlan` and `SourceDescriptor`, and returning validated `Record`
objects.

Tests create isolated SQLite tables from SQLModel metadata and inject fake
planners and collectors. The original `0001_initial` migration creates
PostgreSQL JSONB columns and enables PostgreSQL extensions, so the full Alembic
chain, Procrastinate schema, retry behavior, and worker-to-PostgreSQL path still
require verification against PostgreSQL. SQLite results are not proof of those
PostgreSQL-specific behaviors.
