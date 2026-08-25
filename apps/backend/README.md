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

In Cloudera AI it binds to `127.0.0.1:${CDSW_APP_PORT}`. Port precedence is
`CDSW_APP_PORT -> PORT -> 8000` (local only). Configure Qdrant and observability with the CAI URLs
in `QDRANT_BASE_URL` and `OBSERVABILITY_BASE_URL`; legacy `QDRANT_URL` and `OBSERVABILITY_URL`
remain accepted only for backward compatibility.
