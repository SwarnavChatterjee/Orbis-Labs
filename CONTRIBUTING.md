# Contributing to Orbis Labs

## Shared rules

- Use the official name **Orbis Labs** in user-facing text.
- Never commit `.env` files or API keys.
- The LLM never originates a record.
- Every record requires a source URL and retrieval timestamp.
- Keep schema changes explicit because the Pydantic models are shared contracts.
- Use conventional commits such as `feat:`, `fix:`, `test:`, and `docs:`.

## Branch ownership

Each contributor works on one branch:

```text
feat/openai-planner
feat/api-backend
feat/frontend-dashboard
```

Avoid editing the same shared files across branches when possible. In particular, coordinate changes to:

- `backend/app/models/schemas.py`
- `backend/app/main.py`
- API route contracts
- Alembic migrations

## Pull request checklist

- Tests pass locally.
- Frontend build passes when frontend files changed.
- No secrets or generated dependency directories are committed.
- API or schema changes are documented in the pull request.
- Source-attribution and validation behavior are covered by tests.

