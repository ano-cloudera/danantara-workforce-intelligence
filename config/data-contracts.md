# PoC Data Contracts

## Candidate view
Expected fields: `candidate_id`, `name`, `company`, `years_experience`, `skills`, `summary`.

## Position view
Expected fields: `position_id`, `title`, `required_skills`, `preferred_skills`, `min_years_experience`.

## Policy vector payload
Expected metadata: `document_id`, `chunk_id`, `entity`, `document_type`, `title`, `page`,
`section`, `text`, `source_s3_uri`, and `source_etag`.

Point IDs are stable derivatives of chunk identity. A changed document version replaces every
Qdrant chunk for its `document_id`, preventing stale citations. PDF chunks retain page numbers;
DOCX headings and XLSX sheet names are retained as sections.

These contracts are deliberately small so the PoC can map existing curated customer tables/views without forcing a new enterprise canonical model.

## CV ingestion Iceberg tables

The CAI fallback Job and NiFi flow share these curated contracts:

- `danantara.candidate_master`: candidate profile, source S3 URI/ETag and extraction status.
- `danantara.candidate_skills`: one normalized skill per row with optional evidence.
- `danantara.candidate_experience`: one employment record per row.
- `danantara.cv_ingestion_audit`: idempotency and pipeline status keyed by S3 URI plus ETag.
- `danantara.v_candidates_api`: safe six-column serving view used by the current backend.

Direct contact details remain governed Iceberg fields and are excluded from Qdrant payloads,
observability metadata and the public candidate API.

## Policy ingestion Iceberg tables

- `danantara.policy_documents`: safe document metadata, governed source location, extraction and
  guardrail status.
- `danantara.policy_ingestion_audit`: idempotency and status keyed by source S3 URI plus ETag.
- `danantara.v_policy_documents_api`: safe metadata serving view for backend/frontend.

The original document remains the system of record in governed S3. Raw document text and
credentials are excluded from observability events.

## Dashboard recruitment-pipeline Iceberg table

- `danantara.recruitment_pipeline`: one row per candidate application, with `application_id`,
  `candidate_id`, `entity`, `position_id`, `stage`, `status`, `match_score`, `salary_compliance`,
  `updated_at`.
- `danantara.v_recruitment_pipeline_api`: safe serving view over the table above, used by
  `GET /dashboard/summary`.

Schema is created by `apps/backend/scripts/init_dashboard_schema.py` (run once against Impala; see
`apps/backend/scripts/dashboard_schema.sql` for the DDL). No ingestion Job populates this table yet
— it is a PoC placeholder for recruitment-pipeline stage/compliance/match-score metrics that would
ultimately come from an ATS/HRIS source. When `DATA_MODE=impala` and the table is empty or
unreachable, `dashboard_summary()` falls back to `data/workforce-app/demo/recruitment_status.json`
so the Overview and Dashboard pages keep rendering.
