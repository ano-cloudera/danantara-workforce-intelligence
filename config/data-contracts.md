# PoC Data Contracts

## Candidate view
Expected fields: `candidate_id`, `name`, `company`, `years_experience`, `skills`, `summary`.

## Position view
Expected fields: `position_id`, `title`, `required_skills`, `preferred_skills`, `min_years_experience`.

## Policy vector payload
Expected metadata: `entity`, `title`, `page`, `text`, `source_path`.

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
