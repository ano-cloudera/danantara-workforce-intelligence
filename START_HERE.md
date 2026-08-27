# START HERE: Danantara Workforce Intelligence PoC

This repository is a BMAD-structured, Cloudera AI-ready starter project for the **AI-Powered Talent Screening & Workforce Intelligence Platform** PoC.

## What this project is

The PoC demonstrates one governed data and AI foundation that serves three business experiences:

1. **Talent Intelligence**: candidate matching, ranking, skill gap analysis, and AI-generated recommendations.
2. **Policy Intelligence**: policy search, cross-entity comparison, grounded answers, and citations.
3. **Management Analytics**: candidate and recruitment monitoring through Cloudera Data Visualization.

The custom application stack is intentionally hosted on **Cloudera AI** while enterprise structured data remains in **Iceberg / Cloudera Data Warehouse (Impala)**.

## Locked application topology

Four logical Cloudera AI applications are used:

1. `frontend`: custom Workforce Intelligence UI and identity-aware reverse proxy.
2. `backend`: FastAPI + CrewAI Flows + Gemini + Guardrails + SQLite application state.
3. `qdrant`: shared vector database service with distinct NiFi, candidate and policy collections.
4. `observability`: lightweight local trace collector with optional Langfuse forwarding.

Other platform services:

- Cloudera DataFlow / NiFi: source ingestion, OCR/extraction and routing.
- Cloudera Data Engineering: Spark transformation job from raw to curated Iceberg.
- Cloudera Data Warehouse: governed SQL serving through Impala.
- Cloudera Data Visualization: management dashboard.
- SDX / Ranger / Atlas: governance, policy, metadata and lineage foundation.

Local files are separated under `data/nifi-demo/` and `data/workforce-app/`. Qdrant workload
isolation is enforced by the configurable collection names documented in `README.md`, not by
filesystem directories.

## First run

1. Read `README.md`.
2. Copy `.env.example` to `.env` and fill the Gemini API key and service URLs.
3. Run `python scripts/preflight.py`.
4. For a local smoke test, follow `docs/LOCAL_DEVELOPMENT.md`.
5. For Cloudera AI, follow `docs/CLOUDERA_AI_DEPLOYMENT.md`.

Before development, use `skills/delivery-method-selector/SKILL.md` to choose direct implementation,
lightweight spec-kit planning, or full BMAD. BMAD is reserved for changes whose business or
architecture scope justifies the full artifact chain.

The frontend now provides a responsive six-page enterprise PoC experience (Overview, Talent,
Policy, Dashboard, Data Sources, and Settings) while preserving the FastAPI same-origin proxy.
Reference screenshots define visual language only; every visible business value comes from the
PoC backend or is explicitly labelled as unavailable/PoC state.

The supplied `sample/data` and `sample/additional` package is normalized by
`apps/backend/scripts/import_sample_data.py`. Policy Intelligence is a citation-first conversational
workspace with feedback, source access, and PDF export; global search remains available across
desktop, tablet, and mobile layouts.

For all four CAI Applications, the platform-provided `CDSW_APP_PORT` is authoritative. Launchers
bind to `127.0.0.1` and resolve ports as `CDSW_APP_PORT -> PORT -> local default`. Cross-Application
calls use `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and `OBSERVABILITY_BASE_URL` assigned by CAI.

While the governed NiFi/CDE pipeline is being completed, `jobs/cv_ingestion/run_cai_job.py`
provides a one-shot scheduled PoC fallback for S3 CVs. It is a Job, not a fifth Application;
Iceberg/Impala remains the system of record and Qdrant receives only a sanitized projection.

`jobs/policy_ingestion/run_cai_job.py` provides the equivalent bounded policy fallback for PDF,
DOCX, and XLSX sources. It uses governed S3A access, review/failed routing, pre/post-index
guardrails, Iceberg metadata/audit tables, and the environment-configured Workforce policy
collection. Original policy files remain authoritative in S3.

## Gemini

The backend uses the current Google Gen AI SDK:

```python
from google import genai
```

Default models are configurable and start with the models already validated in the Workbench test:

- Text: `gemini-2.5-flash`
- Embeddings: `gemini-embedding-001`

## 95% ready means

The code, configuration, demo fallbacks, application entrypoints, skills, BMAD artifacts, API contracts, UI shell, tests and deployment instructions are included. The remaining environment-specific work is limited to providing secrets, assigning Cloudera application URLs, validating connectivity to CDW/NiFi, and confirming the Qdrant runtime download in the target Workbench.
