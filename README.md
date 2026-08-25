# Danantara Workforce Intelligence

Cloudera AI based PoC for talent screening, workforce intelligence, policy RAG and management analytics.

## Architecture

```text
Sources / Forms / PDF
        |
        v
Cloudera DataFlow (NiFi)
        |
        v
S3 + Iceberg RAW
        |
        v
Cloudera Data Engineering Spark Job
        |
        v
S3 + Iceberg CURATED
        |                         \
        v                          \
Cloudera Data Warehouse             Qdrant Vector Store
(Impala / governed SQL)              (CAI Application)
        |                              |
        +------------+-----------------+
                     |
                     v
          Backend CAI Application
       FastAPI + CrewAI Flows + Gemini
          Guardrails + SQLite state
                     |
                     v
          Frontend CAI Application
                     |
        +------------+-------------+
        |                          |
 Talent Intelligence        Policy Intelligence

Cloudera Data Visualization reads governed curated data separately for management analytics.
Observability events are sent to the Observability CAI Application and optionally forwarded to Langfuse.
```

## Design principles

- Cloudera remains the execution, governance and application platform.
- Agent Studio is a native capability showcase, not a runtime dependency for this PoC.
- CrewAI **Flows** are used for deterministic, auditable orchestration.
- Gemini is called with `google-genai`, not hidden behind a second agent framework.
- Qdrant is complementary vector infrastructure hosted as a separate CAI Application. Its
  deployment is shared, while collection names isolate the NiFi demo from Workforce workloads.
- SQLite stores application state only, never the enterprise system of record.
- Structured enterprise data remains in Iceberg/CDW.
- Guardrails and observability are horizontal platform layers, not agent tools.
- All integrations are configuration-driven with working demo-mode fallbacks.
- Every CAI Application binds to `127.0.0.1` and resolves its listening port as
  `CDSW_APP_PORT`, then `PORT`, then its local-development default.

## Repository map

```text
apps/frontend/       UI + identity-aware backend proxy
apps/backend/        Core application API and CrewAI workflows
apps/qdrant/         Qdrant CAI launcher
apps/observability/  Local tracing dashboard + optional Langfuse forwarding
config/              Shared configuration templates
data/nifi-demo/      NiFi team's ingestion-to-Qdrant demo files
data/workforce-app/  Workforce fixtures, uploads and local application state
docs/                Architecture, API, deployment, operations
_bmad/               BMAD planning artifacts and stories
skills/              Coding-agent skills for continuing vibe coding
scripts/             Preflight, packaging and project utilities
artifacts/            Reference architecture and UI mockups
```

## Quick start: demo mode

```bash
cp .env.example .env
# Fill GEMINI_API_KEY
python scripts/preflight.py
```

Start backend:

```bash
cd apps/backend
python run_cai.py --local-port 8000
```

Start frontend in another terminal:

```bash
cd apps/frontend
BACKEND_BASE_URL=http://127.0.0.1:8000 python run_cai.py --local-port 8080
```

By default `DATA_MODE=demo` and `QDRANT_MODE=optional`, so the UI and talent matching path can be tested before CDW/Qdrant are wired.

## Shared Qdrant workload isolation

One Qdrant deployment safely serves both demos through distinct, configurable collections:

| Owner | Environment variable | Default collection |
|---|---|---|
| NiFi ingestion demo | `QDRANT_NIFI_COLLECTION` | `nifi_documents` |
| Workforce candidate retrieval | `QDRANT_CANDIDATE_COLLECTION` | `workforce_candidates` |
| Workforce policy retrieval | `QDRANT_POLICY_COLLECTION` | `workforce_policies` |

The three names must be non-empty and unique. The Workforce backend reads collection names only
from its settings model. From `apps/backend`, initialize any missing collections with:

```bash
python scripts/init_qdrant_collections.py
```

The initializer is idempotent and rejects an existing collection whose vector size does not match
`GEMINI_EMBED_DIM`.

The shared Qdrant storage directory (`data/qdrant-storage/` locally) is infrastructure storage;
folders are not the workload isolation boundary.

## Cloudera AI deployment

Upload the complete repository to one Cloudera AI project. Create four Applications and select the corresponding entrypoint:

| Application | Script |
|---|---|
| Workforce Frontend | `apps/frontend/run_cai.py` |
| Workforce Backend | `apps/backend/run_cai.py` |
| Qdrant | `apps/qdrant/run_cai.py` |
| Observability | `apps/observability/run_cai.py` |

Detailed settings are in `docs/CLOUDERA_AI_DEPLOYMENT.md`.

### CAI port and service URL standard

Do not assign an exposed port in Cloudera AI. The platform injects `CDSW_APP_PORT`, and every
launcher uses this precedence:

```text
CDSW_APP_PORT -> PORT -> application local default
```

The local defaults are frontend `8080`, backend `8000`, Qdrant `6333`, and observability `8100`.
They apply only outside CAI. Communication between Applications uses their CAI URLs:

- frontend: `BACKEND_BASE_URL`
- backend: `QDRANT_BASE_URL`
- backend: `OBSERVABILITY_BASE_URL`

Set these to the URLs assigned by Cloudera AI; never construct them from a fixed hostname or port.

## Project state

See `PROJECT_STATE.md` and `_bmad/project-state.yaml` before making changes.

## Development method

Use `skills/delivery-method-selector/SKILL.md` to choose the lightest safe workflow: direct changes,
lightweight spec-kit planning, or full BMAD. Routine fixes and maintenance do not require BMAD.
