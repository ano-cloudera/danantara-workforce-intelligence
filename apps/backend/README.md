# Workforce Backend

FastAPI application providing Talent Intelligence, Policy Intelligence, ingestion fallback, application state, guardrails and observability hooks.

Default runtime modes:
- `ORCHESTRATOR_MODE=crewai`
- `DATA_MODE=demo`
- `QDRANT_MODE=optional`
- `GUARDRAILS_MODE=builtin`

The backend uses `QDRANT_CANDIDATE_COLLECTION` and `QDRANT_POLICY_COLLECTION` from configuration;
it does not embed collection names in indexing or retrieval code. The shared deployment also
reserves `QDRANT_NIFI_COLLECTION` for the independent NiFi ingestion demo. Initialize missing
collections with `python scripts/init_qdrant_collections.py` from this directory.

The backend calls Gemini directly through `google-genai`. CrewAI Flows orchestrate business steps but do not hide the model provider.
