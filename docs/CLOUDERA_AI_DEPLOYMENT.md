# Cloudera AI Deployment Guide

Upload the repository into one Cloudera AI project and create four Applications.

## 1. Frontend Application

Script: `apps/frontend/run_cai.py`  
Environment variables:
- `BACKEND_BASE_URL=https://<backend-app-url>`
- `AUTH_MODE=cai`
- `CDV_DASHBOARD_URL=<optional-CDV-dashboard-url>`

## 2. Backend Application

Script: `apps/backend/run_cai.py`  
Minimum environment variables:
- `GEMINI_API_KEY=<hidden>`
- `GEMINI_TEXT_MODEL=gemini-2.5-flash`
- `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`
- `QDRANT_URL=https://<qdrant-app-url>`
- `QDRANT_API_KEY=<hidden>`
- `QDRANT_NIFI_COLLECTION=nifi_documents`
- `QDRANT_CANDIDATE_COLLECTION=workforce_candidates`
- `QDRANT_POLICY_COLLECTION=workforce_policies`
- `OBSERVABILITY_URL=https://<observability-app-url>`
- `OBSERVABILITY_API_KEY=<hidden>`

Start with `DATA_MODE=demo`. Change to `DATA_MODE=impala` only after CDW connectivity is validated.

## 3. Qdrant Application

Script: `apps/qdrant/run_cai.py`  
Environment variables:
- `QDRANT_VERSION=1.19.0`
- `QDRANT_API_KEY=<hidden>`
- `QDRANT_STORAGE_PATH=<persistent project path>`

The launcher downloads the official Qdrant binary if it is not already cached. If egress is restricted, upload the binary into `apps/qdrant/bin/qdrant` and the launcher will use it.

The Qdrant Application is shared. Configure the same three collection variables for the backend
and NiFi integration, keep all values unique, then run
`apps/backend/scripts/init_qdrant_collections.py`. Separate directories alone do not isolate
Qdrant workloads.

## 4. Observability Application

Script: `apps/observability/run_cai.py`  
Environment variables:
- `OBSERVABILITY_API_KEY=<same hidden key used by backend>`
- `LANGFUSE_ENABLED=false` initially

When Langfuse is available, add `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` and set `LANGFUSE_ENABLED=true`.

## Port handling

The launchers use the Cloudera application port environment variable when present and fall back to a local development port only outside CAI.

## Recommended deployment order

1. Observability
2. Qdrant
3. Backend
4. Frontend

After each deployment, validate `/health` before continuing.
