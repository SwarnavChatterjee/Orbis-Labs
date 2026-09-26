# Orbis Labs architecture

## Product purpose

Orbis Labs is an intelligent ETL system with a natural-language front door and source-backed data delivery.

It is not a general chatbot, an answer-from-memory system, or a final-answer RAG application. Its primary output is a structured, searchable, exportable dataset whose records can be independently verified.

## System flow

```text
User request
  → OpenAI structured query parser
  → QueryPlan validation and ambiguity flags
  → deterministic source registry routing
  → permitted source collectors
  → cleaning and normalization
  → validation and confidence scoring
  → deduplication
  → PostgreSQL persistence
  → dashboard, provenance, and CSV export
```

## Responsibilities

### OpenAI parser

The OpenAI API converts natural language into the shared `QueryPlan` Pydantic model. Structured Outputs are used instead of free-form JSON parsing.

The parser may identify uncertainty through `ambiguity_flags`, but it must not create job or internship records.

### Source registry

Collectors are selected from a typed registry. The MVP has two planned sources:

| Source | Type | Purpose |
|---|---|---|
| Internshala | HTML/browser collection | India-focused internships |
| GitLab Careers | Greenhouse JSON API | Structured company job listings |

The registry keeps routing deterministic and testable. The LLM does not invent collector names or URLs.

### Data processing

Processing will:

- Normalize locations, currencies, dates, and missing values
- Flag validation failures instead of silently dropping records
- Deduplicate with a composite key first
- Use PostgreSQL trigram similarity for near-duplicates
- Preserve source associations when records are merged

### PostgreSQL

PostgreSQL stores:

```text
users → projects → queries → records ← sources
```

The database also provides full-text and trigram indexes for MVP search and deduplication. Vector search is intentionally deferred.

### API

Current query endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/queries` | Submit a natural-language query |
| GET | `/api/queries` | List query history |
| GET | `/api/queries/{id}` | Read query status and parsed plan |
| GET | `/api/queries/{id}/results` | Read collected records |

Responses use the envelope:

```json
{"success": true, "data": {}}
```

Errors use:

```json
{"success": false, "error": "message"}
```

## Trust and provenance rules

Every stored record must include:

- Source name
- Source URL
- Retrieval timestamp
- Validation status
- Deterministic confidence score

The LLM may parse intent or help fill fields on an already-collected record. It may never add a record that a collector did not find.

## MVP scope boundaries

Included:

- Internship and job search
- Two sources
- Query history and re-run support
- Source attribution
- PostgreSQL search
- CSV export

Deferred:

- Qdrant or other vector databases
- Generic arbitrary-schema extraction
- LLM-generated summaries
- Multi-user permissions and advanced authentication
- Workflow branching and editing

