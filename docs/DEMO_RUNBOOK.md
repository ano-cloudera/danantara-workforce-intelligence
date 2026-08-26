# Demo Runbook

## Business storyline

**Message:** One governed data foundation serves both traditional analytics and AI-driven workforce intelligence.

### Track A: Data foundation
Show NiFi ingestion, Iceberg raw/curated and CDE transformation job.

### Track B: Talent Intelligence
Select a role, run matching, explain top candidates and gaps. Open technical backend only after the business result is shown.

### Track C: Policy Intelligence
Ask to compare annual leave for BNS and ENP grade G3, open the cited PKB pages, ask a follow-up,
record thumbs-up/down feedback, and export the grounded answer as PDF.

## Shared Qdrant rehearsal check

Before demonstrating NiFi ingestion or Workforce retrieval:

1. Confirm the NiFi, candidate and policy collection variables are set to three unique names.
2. Run `python apps/backend/scripts/init_qdrant_collections.py` from the project root.
3. Run `python apps/backend/scripts/seed_qdrant.py` and confirm supplied document/chunk metadata.
4. Confirm NiFi writes only to `QDRANT_NIFI_COLLECTION` and Workforce policy retrieval uses
   `QDRANT_POLICY_COLLECTION`.
5. Keep NiFi-owned files under `data/nifi-demo/` and Workforce files under
   `data/workforce-app/`.

## CAI application rehearsal check

1. Confirm all four Applications received `CDSW_APP_PORT` and bind to `127.0.0.1`.
2. Confirm no fixed exposed port is configured in CAI Application variables.
3. Verify `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and `OBSERVABILITY_BASE_URL` use the Application
   URLs assigned by Cloudera AI.
4. Validate each health endpoint before wiring the next Application.

### Track D: Management
Open Cloudera Data Visualization and show total candidates, candidate distribution and recruitment KPIs.

## Failure-safe demo

If CDW is unavailable, use `DATA_MODE=demo`.  
If Qdrant is unavailable, policy demo uses the packaged policy fallback.  
If observability is unavailable, backend logs locally and continues.  
If Agent Studio is unavailable or provider-incompatible, it does not affect the main demo runtime.
