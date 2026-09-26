# Orbis Labs implementation plan

## Delivery sequence

### Phase 1: shared foundation — complete

- Orbis Labs repository scaffold
- Pydantic contracts
- FastAPI application
- SQLModel tables
- Alembic migration
- OpenAI parser boundary
- Source registry
- Initial query API

### Phase 2: query intelligence

- Configure `OPENAI_API_KEY` and `OPENAI_MODEL`
- Run a real parser smoke test
- Evaluate 15–20 realistic queries
- Confirm ambiguity flags are useful
- Persist routed source IDs with the parsed plan

### Phase 3: source collectors

1. Build the GitLab Greenhouse API collector.
2. Save representative API fixtures.
3. Build the Internshala collector against fixtures.
4. Add robots.txt and request compliance checks.
5. Validate both collectors against live sources.

### Phase 4: processing

- Normalize locations, dates, and compensation
- Validate required fields and URLs
- Calculate deterministic confidence
- Deduplicate exact matches
- Add trigram-based near-duplicate matching
- Preserve all source associations

### Phase 5: execution and delivery

- Replace the temporary background boundary with a durable worker
- Add pipeline stage events
- Add SSE progress streaming
- Connect the React query form
- Add results filtering and provenance display
- Add CSV export
- Add query history and re-run

## Branch plan

```text
main
├── feat/openai-planner
├── feat/api-backend
└── feat/frontend-dashboard
```

The shared contracts and database migration must be established on `main` before the branches are distributed.

Detailed role prompts are available in:

- [OpenAI planner prompt](team-prompts/openai-planner.md)
- [Detailed OpenAI planner implementation plan](team-prompts/openai-planner-implementation-plan.md)
- [API backend prompt](team-prompts/api-backend.md)
- [Frontend dashboard prompt](team-prompts/frontend-dashboard.md)

### OpenAI planner branch

Owns the parser, ambiguity behavior, source routing, and parser evaluation tests.

### API backend branch

Owns FastAPI routes, persistence, worker integration, status transitions, and SSE.

### Frontend branch

Owns query entry, progress UI, results, history, filters, and CSV export. It may use mocked API responses until the backend contract is stable.

## Definition of done

The MVP is complete when a user can:

1. Submit a natural-language internship or job request.
2. See the parsed plan and any ambiguity warnings.
3. Monitor collection progress.
4. View cleaned and deduplicated records.
5. Open the original source URL for each record.
6. Export the result set as CSV.
7. Re-run an earlier query without modifying its historical result.

## Verification commands

```bash
PYTHONPATH=backend pytest backend/tests -q
npm run build --prefix frontend
```
