# Cloudera AI Deployment Guide

Upload the repository into one Cloudera AI project and create four Applications.

## Mandatory CAI networking standard

Cloudera AI injects `CDSW_APP_PORT` for each Application. Do not configure a fixed exposed port.
Every project launcher binds to `127.0.0.1` and uses:

```text
CDSW_APP_PORT -> PORT -> local development default
```

`PORT` is a secondary compatibility override. The application-specific default is used only
outside Cloudera AI. `CML_APP_PORT` is not part of this project standard.

CAI may execute the selected Application script through its interpreter rather than as a normal
Python file, so `__file__` is not guaranteed. All four launchers resolve their directory from
`__file__` when available, otherwise from `CDSW_PROJECT_DIR` or the project working directory.
The Qdrant launcher additionally supports CAI interpreter execution where none of those identify
the checkout: it uses the interpreter cwd for its downloaded binary and storage bootstrap.
All launchers also detect a repository checkout directly below the CAI working directory, matching
Workbench project layouts such as `danantara-workforce-intelligence/apps/<application>`.
Select the repository `apps/<application>/run_cai.py` entrypoint and keep the complete repository
tree available to the Application. In interpreter mode, launchers also tolerate runner arguments
that are not part of the project launcher CLI.

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
- `QDRANT_BASE_URL=https://<qdrant-app-url>`
- `QDRANT_API_KEY=<hidden>`
- `QDRANT_TIMEOUT_SECONDS=20` for CAI cross-Application routing (`5` is the local default)
- `QDRANT_TRUST_ENV=false`
- `QDRANT_NIFI_COLLECTION=nifi_documents`
- `QDRANT_CANDIDATE_COLLECTION=workforce_candidates`
- `QDRANT_POLICY_COLLECTION=workforce_policies`
- `OBSERVABILITY_BASE_URL=https://<observability-app-url>`
- `OBSERVABILITY_API_KEY=<hidden>`

For governed citation downloads and the Data Sources upload form (see below for both), the backend
Application needs its own storage access configuration, separate from either ingestion Job's own
`S3_ACCESS_MODE`:

- `POLICY_SOURCE_ACCESS_MODE=datalake` plus Ranger read access to `policy-processed/` and
  `policy-review/` for the backend's own workload identity, or citation downloads 404 with
  "Document source is unavailable" even though ingestion succeeded.
- `UPLOAD_ACCESS_MODE=datalake` plus `S3_CV_LANDING_URI=s3a://<bucket>/data/cv-collect/` and
  `S3_POLICY_LANDING_URI=s3a://<bucket>/data/policy-collect/` to make the Data Sources upload form
  write directly into the same governed landing prefixes the ingestion Jobs already read from,
  instead of the backend's local filesystem. Requires Ranger write access to both prefixes for the
  backend's workload identity. Leave unset (`local`, the default) to keep the old local-write +
  direct-Qdrant-index behavior.

Start with `DATA_MODE=demo`. Change to `DATA_MODE=impala` only after CDW connectivity is validated.
The backend uses Qdrant REST over `httpx` as the production CAI transport; it does not depend on
the Qdrant Python SDK transport across Istio/Envoy. Existing `QDRANT_CHECK_COMPATIBILITY` values are
harmless but deprecated.
For ECS Applications without terminal access, use `GET /api/v1/health/qdrant` to compare direct
and environment-proxy connectivity without exposing endpoint or credential values.

## 3. Qdrant Application

Script: `apps/qdrant/run_cai.py`  
Environment variables:
- `QDRANT_VERSION=1.19.0`
- `QDRANT_API_KEY=<hidden>`
- `QDRANT_STORAGE_PATH=<persistent project path>`

The launcher downloads the official Qdrant binary if it is not already cached. If egress is restricted, upload the binary into `apps/qdrant/bin/qdrant` and the launcher will use it.
It probes the binary before startup and launches it as a child process so the CAI Python engine
remains alive and binary failures are visible in Application Logs.

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

The frontend, backend and observability launchers pass the resolved port to Uvicorn. The Qdrant
launcher sets `QDRANT__SERVICE__HTTP_PORT` to the same resolved value. All four force
`127.0.0.1` when `CDSW_APP_PORT` is present.

Each service runs as a child of the CAI Python engine. Launchers must not replace the engine with
`os.execv`, because Workbench can interpret that replacement as an exited Application engine.
Python launchers install into their project-local virtual environment with pip isolated mode and
`--no-user`; this overrides CAI runtime defaults such as `PIP_USER=true` that are invalid inside a
virtual environment.

Do not put local defaults or CAI-internal port assumptions into Application environment variables.
Use the HTTPS Application URLs shown by Cloudera AI for all cross-Application communication.

## Recommended deployment order

1. Observability
2. Qdrant
3. Backend
4. Frontend

After each deployment, validate `/health` before continuing.

For Qdrant, use its built-in `/healthz` and `/readyz` endpoints instead of the FastAPI `/health`
route used by the other three Applications.

## Scheduled CV ingestion Job

The NiFi/CDE flow remains the target governed ingestion architecture. For a self-contained PoC
simulation, create a Workbench Job with script `jobs/cv_ingestion/run_cai_job.py`. This is a batch
Job and does not add a fifth Application.

1. Synchronize the CAI execution identity in IDBroker and grant its user/group Ranger `cm_s3`
   read/write access to the CV input, processed and failed prefixes.
2. Enable the Spark 3 runtime add-on, set `S3_ACCESS_MODE=datalake`, and use `s3a://` for all three
   `S3_CV_*` URIs. Provide the remaining non-interactive Impala, Gemini, Qdrant and observability
   variables documented in `.env.example`.
3. Run the Job once with `CV_JOB_INIT_SCHEMA=true` using an identity allowed to create Iceberg
   tables/views in the existing `danantara` database, then restore it to `false`.
4. Set `CV_JOB_DRY_RUN=true` and `CV_JOB_MAX_OBJECTS=1` for the first Job execution.
5. Confirm extraction and sanitized observability events, then set `CV_JOB_DRY_RUN=false`.
6. Schedule the one-shot Job at the minimum practical interval supported by the Workbench.

A JDBC URL with `auth=browser` is suitable only for an interactive user. Scheduled execution needs
the workload/service authentication mechanism approved for the CDW Virtual Warehouse. Qdrant
remains complementary; Iceberg is the candidate system of record.

## Scheduled policy ingestion Job

Create a separate Workbench Job using `jobs/policy_ingestion/run_cai_job.py`. It shares the same
four-Application topology and is a fallback for the target NiFi/CDE policy flow.

1. Grant the Job identity recursive Ranger `cm_s3` read/write access to the governed
   `policy-collect`, `policy-processed`, `policy-review`, and `policy-failed` prefixes.
2. Set `S3_ACCESS_MODE=datalake`, all four `S3_POLICY_*` URIs, Gemini/Qdrant/Impala/observability
   variables, and keep `QDRANT_POLICY_COLLECTION` aligned with the backend.
3. Run once with `POLICY_JOB_INIT_SCHEMA=true`, then restore it to `false`.
4. Run with `POLICY_JOB_DRY_RUN=true` and `POLICY_JOB_MAX_OBJECTS=1`; verify extraction and safe
   observability events without any S3, Impala, or Qdrant mutation.
5. Set dry-run to `false`, process one document, then validate the Iceberg audit/document rows,
   Qdrant citation payload, Policy Intelligence query, and the citation card's Download Source
   action (the citation card no longer exposes a separate "View metadata" link/raw-JSON view).
6. Raise the bounded batch limit to at most 20 and schedule it only after the single-file path is
   validated.

The backend Application needs `IMPALA_POLICY_DOCUMENT_TABLE=danantara.v_policy_documents_api` and
`POLICY_SOURCE_ACCESS_MODE=datalake` for dynamic metadata and governed source downloads. Files with
uncertain metadata or prompt-injection patterns go to review without indexing; corrupt files go to
failed; partial Impala/Qdrant failures leave the landing object retryable.

## Data Sources upload -> governed landing prefixes

The Data Sources page's upload form can write directly into the same governed S3A prefixes the
CV/policy ingestion Jobs read from, so "upload from the UI, then run the Job" is a real, demoable
loop end to end. This is opt-in on the backend Application:

1. Set `UPLOAD_ACCESS_MODE=datalake`, `S3_CV_LANDING_URI=s3a://<bucket>/data/cv-collect/`, and
   `S3_POLICY_LANDING_URI=s3a://<bucket>/data/policy-collect/` on the backend Application.
2. Grant the backend's workload identity Ranger write access to both prefixes (this is separate
   from, and in addition to, the read/write grants already given to the ingestion Jobs' identities).
3. Upload one PDF from Data Sources with Document Type "Candidate CV" and confirm it lands in
   `cv-collect/`; upload one with any other Document Type (Group HR Policy, PKB, Salary Policy, Job
   Opening) and confirm it lands in `policy-collect/`.
4. Trigger the matching ingestion Job manually and confirm the uploaded file is picked up, processed,
   and becomes queryable through Talent Intelligence / Policy Intelligence.

Leaving `UPLOAD_ACCESS_MODE` unset (`local`, the default) keeps the previous behavior: the file is
written to the backend's local filesystem and, for PDFs, indexed directly into Qdrant from the
backend itself, bypassing the ingestion Jobs' guardrails and Impala metadata/audit rows entirely.
Only use `local` for isolated frontend testing, not for anything meant to demonstrate the governed
ingestion path.
