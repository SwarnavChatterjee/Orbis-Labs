# Role 3 — Frontend Dashboard

## Branch

```text
feat/frontend-dashboard
```

## Prompt

You are responsible for the React and TypeScript dashboard for Orbis Labs.

Read these files before changing anything:

- `README.md`
- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/current-context.md`
- `CONTRIBUTING.md`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `backend/app/models/schemas.py`
- `backend/app/api/routes/queries.py`

### Product context

Orbis Labs presents source-backed internship and job data. The user should be able to submit a natural-language request, monitor the pipeline, inspect records, verify sources, export CSV, and revisit previous queries.

The current frontend is a branded shell only. Backend endpoints exist, but progress streaming, result views, and history are not complete.

### Your responsibilities

1. Build a clean Orbis Labs query dashboard.
2. Connect the query form to `POST /api/queries`.
3. Display queued, running, planned, collecting, cleaning, completed, and failed states.
4. Consume the SSE progress endpoint when available.
5. Build a results table with filters and pagination.
6. Display confidence, source name, source URL, and retrieval timestamp.
7. Add CSV export from the structured result data.
8. Add query history and a re-run action.
9. Use mock data or a typed API client while backend work is in progress.

### Required UX behavior

- Make ambiguity warnings visible without blocking the user.
- Show failures clearly and provide a retry or re-run path.
- Keep source URLs clickable and distinguish source attribution from AI-generated interpretation.
- Never claim that a query is complete before the backend reports completion.
- Preserve historical query results when a query is re-run.
- Support loading, empty, error, and partial-result states.

### API assumptions

Use these endpoints and do not invent incompatible paths:

```text
POST /api/queries
GET  /api/queries/{id}
GET  /api/queries/{id}/results
GET  /api/queries/{id}/stream
GET  /api/queries
```

Keep API calls in a typed client module. Do not scatter `fetch()` calls across components.

### Important boundaries

Do not:

- Put the OpenAI API key in frontend code.
- Implement parsing, scraping, cleaning, or deduplication in the browser.
- Change backend response shapes silently.
- Use generated build artifacts as source files.
- Add authentication or complex design-system dependencies unless approved.

### Suggested implementation

- Break the UI into query input, progress stream, results table, history list, and reusable status components.
- Define TypeScript types from the backend contract.
- Start with mock JSON fixtures and switch to real endpoints behind the same client functions.
- Use `EventSource` for SSE and close it when a query completes or the component unmounts.
- Generate CSV in the browser from the displayed structured records.
- Keep the existing Orbis Labs visual direction unless a product decision changes it.

### Definition of done

- A user can submit a query from the browser.
- Progress and errors are visible.
- Results show structured fields and provenance.
- CSV export downloads a usable file.
- Query history lists status and record count.
- Re-run creates a new query instead of mutating the old one.
- `npm run build --prefix frontend` passes.
- Backend tests remain passing after integration.

### Handoff

Report:

- Components created
- API types and assumptions
- SSE behavior
- CSV format
- Mock data removed or retained
- Build/test commands and results
- Backend changes required for final integration

