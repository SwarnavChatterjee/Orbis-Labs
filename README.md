# Orbis Labs

Orbis Labs is a source-backed AI data intelligence platform. It turns a natural-language request into a structured collection plan, gathers internship and job records from permitted sources, cleans and deduplicates them, and presents searchable results with provenance.

The LLM helps interpret intent and structure messy text. It does not invent records. Every result must trace back to a source URL and retrieval timestamp.

## MVP architecture

- Backend: Python, FastAPI, SQLModel, PostgreSQL
- LLM: OpenAI API with Pydantic Structured Outputs
- Sources: Internshala scraper and GitLab Greenhouse API
- Processing: normalization, validation, deterministic confidence, deduplication
- Frontend: React + TypeScript
- Jobs: PostgreSQL-backed background processing boundary, with durable worker integration planned

The end-to-end flow is:

```text
Natural-language request
        ↓
OpenAI QueryPlan
        ↓
Deterministic source routing
        ↓
Collection and processing
        ↓
PostgreSQL records with provenance
        ↓
Search, review, and export
```

## Current status

Implemented:

- Shared Pydantic contracts
- OpenAI parser boundary
- Source registry and routing
- SQLModel database models
- Alembic initial migration
- Query submission, status, history, and results endpoints
- React frontend shell
- Automated backend tests and frontend build

Next:

- Durable background worker
- GitLab Greenhouse collector
- Internshala collector
- Cleaning and deduplication pipeline
- Frontend API integration, SSE progress, and CSV export

## Documentation

- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Current project context](docs/current-context.md)
- [Contribution and branch workflow](CONTRIBUTING.md)
- [Team prompts](docs/team-prompts/)

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Then open `http://localhost:8000/health`.

To start PostgreSQL locally:

```bash
docker compose up -d postgres
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
```
