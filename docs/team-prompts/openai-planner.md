# Role 1 — OpenAI Query Planner

## Branch

```text
feat/openai-planner
```

## Prompt

You are responsible for the OpenAI-powered query-planning layer of Orbis Labs.

Read these files before changing anything:

- `README.md`
- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/current-context.md`
- `backend/app/models/schemas.py`
- `backend/app/llm/parser.py`
- `backend/app/jobs/tasks.py`
- `backend/app/collectors/registry.py`

### Product context

Orbis Labs is a source-backed AI data intelligence platform. A user submits a natural-language request for internships or jobs. OpenAI converts that request into a validated `QueryPlan`. The LLM interprets intent; it must never invent job records, source URLs, companies, or collected data.

The MVP uses:

- OpenAI Responses API
- Pydantic Structured Outputs
- Internshala as a scraper source
- GitLab Greenhouse as an API source
- Visible ambiguity warnings instead of blocking clarification questions

### Your responsibilities

1. Harden the OpenAI parser in `backend/app/llm/parser.py`.
2. Keep the parser output compatible with the existing `QueryPlan` model.
3. Ensure missing or uncertain fields produce `ambiguity_flags`.
4. Ensure the model never selects arbitrary URLs or invents sources.
5. Keep source selection deterministic through `route_sources()`.
6. Add parser tests for clean, incomplete, ambiguous, and unsupported requests.
7. Add a small evaluation harness for 15–20 realistic user queries.
8. Document required environment variables without exposing secrets.

### Required behavior

The parser must:

- Return only `internship_search` or `job_search` intents.
- Preserve unspecified filters as `null` or defaults.
- Add an ambiguity flag when the user omits or ambiguously states a meaningful filter.
- Never populate `sources` using free-form model text.
- Allow the Python routing layer to populate `sources` from the registry.
- Raise a clear, actionable error when `OPENAI_API_KEY` is missing.
- Handle empty, malformed, refused, or incomplete model responses safely.

### Important boundaries

Do not:

- Build collectors.
- Change database tables unless the shared contract absolutely requires it.
- Add a second LLM provider.
- Add vector search or RAG.
- Put the API key in frontend code, tests, commits, or documentation.
- Change the public API response envelope without coordinating with the API branch.

### Suggested implementation

- Keep OpenAI access behind a small `QueryPlanner`-compatible interface.
- Make the model configurable through `OPENAI_MODEL`.
- Use the existing Pydantic model with `responses.parse(..., text_format=QueryPlan)`.
- Use dependency injection or a fake client for tests.
- Keep deterministic source routing outside the LLM call.
- Store parser evaluation cases as safe, non-secret fixture data.

### Definition of done

- The parser works with a real local OpenAI key when configured.
- Tests run without a network call or API key.
- At least 15 evaluation queries are documented and checked.
- Ambiguity behavior is visible and deterministic.
- The parser does not invent source IDs or records.
- `PYTHONPATH=backend pytest backend/tests -q` passes.
- Changes are documented in the pull request.

### Handoff

Report:

- Files changed
- Parser behavior and model configuration
- Evaluation results
- Any schema changes
- Exact test commands and results
- Any required follow-up for the API or collector owner

