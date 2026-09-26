# Orbis Labs OpenAI Planner — Detailed Implementation Plan

## 1. Purpose

This document is the execution plan for `feat/openai-planner`.

The OpenAI Planner is the intelligence boundary between a natural-language request and Orbis Labs’ deterministic collection workflow:

```text
User request → OpenAI Structured Outputs → QueryPlan → source routing → collectors
```

The planner interprets intent. It does not collect records, browse websites, choose arbitrary URLs, or invent data.

## 2. Current repository context

The branch starts from the current Orbis Labs baseline. Relevant files already exist:

```text
backend/app/models/schemas.py       Shared Pydantic contracts
backend/app/llm/parser.py           Initial OpenAI parser boundary
backend/app/jobs/tasks.py           Query processing boundary
backend/app/collectors/registry.py  Registered sources and routing
backend/app/core/config.py          Environment configuration
backend/tests/test_parser.py        Mock parser test
```

The initial parser uses the OpenAI Python SDK pattern:

```python
response = client.responses.parse(
    model=settings.openai_model,
    input=messages,
    text_format=QueryPlan,
)
plan = response.output_parsed
```

The branch must harden this implementation, add evaluation coverage, and preserve compatibility with the API backend branch.

## 3. Fixed MVP decisions

- Official name: Orbis Labs
- Initial domain: internships and jobs
- API: OpenAI Responses API
- Output: Pydantic Structured Outputs
- Primary source: Internshala scraper
- Secondary source: GitLab Greenhouse API
- Ambiguity: continue with visible warnings
- Source selection: deterministic Python routing
- Record creation: collectors only, never the LLM
- Vector search: deferred
- Clarifying-question loop: deferred

OpenAI Structured Outputs is the correct mechanism because the SDK can parse output directly into a Pydantic model and enforce the declared shape. JSON mode alone does not guarantee schema adherence. See the [official OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## 4. Scope

### Included

- OpenAI client configuration
- Query planner interface
- System/developer instructions
- Pydantic structured response integration
- Safe query normalization
- Ambiguity flag generation
- Parser error classification
- Deterministic source-routing handoff
- Mock-based tests
- Real-key smoke-test instructions
- 15–20 query evaluation dataset and harness
- Safe logging and security checks

### Excluded

- Internshala scraping
- Greenhouse API requests
- Browser automation
- Record extraction from job pages
- Cleaning and deduplication
- PostgreSQL record persistence
- React UI work
- CSV export
- Authentication
- Autonomous web browsing or agent loops

## 5. Integration boundary

The API branch should depend on a small planner interface, not OpenAI SDK types:

```python
class QueryPlanner(Protocol):
    def parse(self, raw_text: str) -> QueryPlan:
        ...
```

The production implementation may be an `OpenAIQueryPlanner` class or a wrapped `parse_query()` function. The important dependency direction is:

```text
API service → QueryPlanner interface → OpenAI implementation
                                      ↘ fake test implementation
```

This lets API tests run without network access or an API key.

## 6. Environment and client configuration

The planner reads configuration only from the backend environment:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-6-astra
```

Rules:

1. Never hard-code an API key.
2. Never send the key to React.
3. Never print the key in logs or exceptions.
4. Fail clearly when the key is missing.
5. Keep the model configurable.
6. Do not silently fall back to another provider or model.
7. Inject the client in tests instead of making network calls.

Prefer one reusable client per worker/process rather than constructing a client for every query.

```python
class OpenAIQueryPlanner:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
```

Do not create a network client at module import time if that prevents configuration errors from being tested cleanly.

## 7. Shared output contract

Use the existing models in `backend/app/models/schemas.py`:

```python
class AmbiguityFlag(BaseModel):
    field: str
    reason: str


class QueryFilters(BaseModel):
    role: str | None = None
    location: str | None = None
    graduation_year: int | None = None
    remote: bool | None = None


class QueryPlan(BaseModel):
    intent: Literal["internship_search", "job_search"]
    filters: QueryFilters
    required_fields: list[str]
    target_count: int
    ambiguity_flags: list[AmbiguityFlag]
    sources: list[str]
```

Contract rules:

- Optional values are explicit `null` or model defaults.
- `intent` is an enum, not arbitrary model text.
- `target_count` is bounded.
- `graduation_year` has sensible bounds.
- `sources` is populated or verified by Python routing.
- Stipend and deadline belong to collected `Record`, not `QueryPlan`.
- The planner never returns job records.

If `schemas.py` must change:

1. Explain the reason.
2. Identify API and frontend impact.
3. Update contract tests.
4. Notify the other branch owners.
5. Document the change in the pull request.

## 8. Prompt design

The system/developer instruction must define the model’s limits. It should state that the model is a query interpreter—not a search engine, collector, database writer, or free-form source selector.

The prompt must instruct the model to:

1. Return only the declared structured schema.
2. Extract only stated or directly implied information.
3. Use `null` for unknown optional filters.
4. Add an ambiguity flag for meaningful uncertainty.
5. Never invent companies, URLs, listings, salaries, deadlines, or source IDs.
6. Use only the allowed intent enum.
7. Leave `sources` empty or allow Python to overwrite it.
8. Handle unrelated requests according to the unsupported-input policy.

Use a few-shot set covering:

- A complete internship request
- A request missing location
- Bengaluru/Bangalore normalization
- A remote job request
- An unrelated request

Examples must demonstrate uncertainty instead of encouraging guesses.

Version the prompt:

```python
PARSER_PROMPT_VERSION = "v1"
SYSTEM_PROMPT = "..."
```

If the database later stores prompt versions, historical parser results become easier to audit.

## 9. Structured Outputs call

Use the Responses API with the native Pydantic helper:

```python
response = client.responses.parse(
    model=model,
    input=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": raw_text},
    ],
    text_format=QueryPlan,
)
```

Then verify:

```python
if response.output_parsed is None:
    raise PlannerIncompleteResponseError(...)
plan = response.output_parsed
```

Do not use prompt-only JSON instructions, regex extraction of prose, or `json.loads()` as the primary strategy.

Structured Outputs still requires runtime handling for refusal, incomplete output, transport errors, authentication errors, rate limits, and unsupported model/schema combinations.

## 10. Query interpretation rules

The planner extracts:

- Search intent
- Job or internship type
- Role
- Location
- Graduation year
- Remote preference
- Requested result count
- Required output fields

It may apply narrow, explainable normalization:

```text
"Bengaluru" → "Bangalore"
"SWE intern" → "software engineering"
"2027 grads" → 2027
```

If normalization changes meaning or is uncertain, add an ambiguity flag.

Correct behavior for an underspecified request:

```json
{
  "filters": {"role": "engineering", "location": null},
  "ambiguity_flags": [
    {"field": "location", "reason": "No location was specified."}
  ]
}
```

Never turn a missing value into a confident default simply because it is common.

## 11. Source-routing handoff

Routing remains deterministic and outside model judgment:

```python
plan = parse_query(raw_text)
sources = route_sources(plan.intent, plan.filters.role)
plan.sources = [source.id for source in sources]
```

The only valid source IDs are registered values such as:

```text
internshala
gitlab_greenhouse
```

The planner branch must not add collector-specific scraping logic or accept free-form model URLs.

Required routing tests:

- Internship intent routes to registered internship sources.
- Software engineering role routes to matching sources.
- Unknown roles do not create arbitrary collector selections.
- A model-supplied unknown source ID is discarded or overwritten.

## 12. Confidence and ambiguity

The LLM must not self-report final record confidence. It may report ambiguity flags only.

The data-processing branch calculates confidence from deterministic evidence:

- Required-field completeness
- URL validity
- Date validity
- Normalization success
- Duplicate status
- Source metadata

Do not add a model-generated confidence field without coordinating a contract change.

## 13. Error model

Use typed or clearly classified errors:

```text
PlannerConfigurationError
PlannerAuthenticationError
PlannerRateLimitError
PlannerTransportError
PlannerRefusalError
PlannerIncompleteResponseError
PlannerSchemaError
```

Suggested safe messages:

```text
The query planner is not configured. Add OPENAI_API_KEY to the backend environment.
The query planner could not complete the request. Please retry.
The request could not be planned safely.
```

Do not expose headers, API keys, full provider traces, or raw authorization errors to users.

Retry policy:

- Do not retry authentication failures.
- Retry transient network errors only through worker policy.
- Retry rate limits with bounded backoff.
- Do not retry malformed results indefinitely.
- Make attempt limits configurable.

## 14. Testing strategy

### Unit tests

Use a fake OpenAI client. Required cases:

1. Fully specified internship query.
2. Fully specified job query.
3. Missing location.
4. Missing graduation year.
5. Remote-only request.
6. Location alias normalization.
7. Role abbreviation.
8. Unsupported unrelated request.
9. Empty or whitespace input.
10. Invalid parsed output.
11. Missing parsed output.
12. Refusal response.
13. Missing API configuration.
14. Authentication failure.
15. Rate-limit failure.

Tests must not require a network connection or a real API key.

### Contract tests

Every successful plan must:

- Validate as `QueryPlan`.
- Use one allowed intent.
- Contain valid filter types.
- Have a bounded target count.
- Use valid ambiguity flag shapes.
- Reject or ignore arbitrary extra keys.

### Smoke test

The real API smoke test runs only when a developer has configured a local key:

```bash
PYTHONPATH=backend python -m app.llm.smoke_test
```

It should print the structured plan and safe metadata, never the key.

## 15. Evaluation dataset

Create a checked-in, secret-free dataset with expected semantic fields:

```json
{
  "name": "india_internship_2027",
  "input": "Find software engineering internships in India for 2027 graduates.",
  "expected": {
    "intent": "internship_search",
    "filters.location": "India",
    "filters.graduation_year": 2027
  }
}
```

Include 15–20 cases across:

- Specific internship requests
- General job searches
- Missing locations
- Missing graduation years
- Remote queries
- Location aliases
- Role aliases
- Different target counts
- Ambiguous wording
- Unsupported requests

Compare important semantic fields rather than requiring identical serialized JSON. Ordering of `required_fields` need not matter; intent and graduation year do.

Score:

- Intent accuracy
- Role extraction
- Location extraction
- Graduation-year extraction
- Remote flag accuracy
- Target-count handling
- Ambiguity detection
- No-invention behavior
- Source-routing compatibility
- Schema validity

Record failures by category, not only as one total score. OpenAI’s evaluation guidance recommends using evaluations to detect regressions when prompts or models change; see the [official evals guidance](https://developers.openai.com/api/docs/guides/evals).

## 16. Logging and privacy

Safe metadata may include:

- Query ID
- Prompt version
- Model name
- Request duration
- Success or failure category
- Ambiguity-flag count
- Registered source IDs

Avoid logging:

- API keys
- Authorization headers
- Full private user queries in production logs
- Raw provider responses by default
- Full prompts containing private data

Verbose logging must be opt-in and disabled by default.

## 17. Implementation sequence

### Step 1 — Review baseline

```bash
git switch feat/openai-planner
PYTHONPATH=backend pytest backend/tests -q
```

Confirm the shared contracts, source registry, current parser, and tests are present.

### Step 2 — Add the planner interface

Introduce a protocol or abstract interface without changing public API routes.

### Step 3 — Refactor the OpenAI implementation

Centralize client construction, prompt versioning, structured parsing, validation, and error translation.

### Step 4 — Add mock tests and fixtures

Add fake-client tests, evaluation inputs, refusal/incomplete-response cases, and safe error assertions.

### Step 5 — Add routing handoff tests

Verify that only registry IDs reach the next pipeline stage.

### Step 6 — Run a real smoke test

With a local `.env` key, execute the smoke test and record model, prompt version, and semantic result—not the secret.

### Step 7 — Coordinate with API backend

Share the planner interface, error categories, `QueryPlan` shape, sync/async expectations, and smoke-test instructions.

### Step 8 — Prepare pull request

Include evaluation results, test commands, configuration notes, and every contract change.

## 18. Acceptance criteria

The branch is merge-ready when:

- Production parsing uses OpenAI Structured Outputs.
- The model is configurable.
- No secret is committed.
- Results validate as `QueryPlan`.
- Ambiguity is visible instead of silently guessed.
- Source IDs are deterministic and registry-bound.
- Provider failures are classified and sanitized.
- Mock tests cover success and failure paths.
- At least 15 evaluation cases are checked in.
- A real smoke test has been run or explicitly documented as blocked by missing credentials.
- Existing tests pass.
- The API owner confirms the integration boundary.

Verification commands:

```bash
PYTHONPATH=backend pytest backend/tests -q
npm run build --prefix frontend
```

## 19. Handoff template

The pull request description should contain:

```text
Branch:
Model:
Prompt version:
Files changed:
Schema changes:
Evaluation cases:
Evaluation result:
Real smoke test: yes/no
Required environment variables:
Test commands:
Known limitations:
API-backend follow-ups:
```

## 20. Final principle

The OpenAI Planner succeeds when it makes the rest of Orbis Labs deterministic—not when it behaves like an autonomous agent.

```text
Natural language → typed intent → deterministic workflow
```

