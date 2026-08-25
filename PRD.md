# Product Requirements Document (PRD)

## Product
Danantara Workforce Intelligence

## Experiences

### Talent Intelligence
Inputs: position, optional company/entity, optional skills/keywords.  
Outputs: ranked candidate list, deterministic match score, matched skills, gaps, experience summary, AI reasoning and source coverage.

### Policy Intelligence
Inputs: natural-language question, selected entities, policy topic.  
Outputs: grounded answer, entity comparison, retrieved sources, citations and trust/safety metadata.

### Data Sources
Inputs: PDF upload, candidate registration form.  
Behavior: proxy to NiFi when configured; direct local parsing/indexing only as PoC fallback.

### Management Dashboard
The custom UI may show a link/summary, while the primary management dashboard is Cloudera Data Visualization.

### Settings
Expose non-secret runtime configuration indicators, model route, guardrail mode, data mode and external service health. Secret values must never be rendered.

## Functional requirements

- FR-01 Frontend and backend run as separate CAI Applications.
- FR-02 Backend exposes versioned REST endpoints under `/api/v1`.
- FR-03 Frontend proxies API calls and propagates CAI identity when available.
- FR-04 Gemini text model and embedding model are environment-configurable.
- FR-05 CrewAI Flow is the default orchestration mode.
- FR-06 Candidate structured data is retrieved from CDW/Impala in production mode.
- FR-07 Demo-mode candidate data is included for development.
- FR-08 Policy retrieval uses Qdrant when available.
- FR-09 Policy demo fallback works without Qdrant for initial UI/backend validation.
- FR-10 Qdrant collection size follows configurable Gemini embedding dimensionality.
- FR-11 SQLite persists sessions, feedback and application events only.
- FR-12 Guardrails run on input and final output.
- FR-13 Observability events contain session ID, user ID, event type, latency and metadata.
- FR-14 Observability can run locally and optionally forward events to Langfuse.
- FR-15 Direct file upload can be routed to NiFi through a configured webhook.
- FR-16 Human-review status is included with AI-generated recommendations.
- FR-17 A shared Qdrant deployment isolates the NiFi demo, Workforce candidate retrieval and
  Workforce policy retrieval through three unique environment-configured collection names.

## Non-functional requirements

- Configuration via environment variables.
- No secrets committed to source control.
- Health endpoints for all HTTP applications.
- Deterministic business scoring separated from LLM reasoning.
- Graceful degradation when Qdrant, CDW or Langfuse is unavailable in demo mode.
- Structured JSON API outputs for stable UI rendering.
- Timeouts on external requests.
- Minimal PII logging by default.
- Collection names must be non-empty, unique across workloads and never hardcoded in backend
  retrieval or indexing services.
