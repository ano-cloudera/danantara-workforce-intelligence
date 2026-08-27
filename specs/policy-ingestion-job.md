# Policy ingestion Job specification

## Scope

Add a one-shot Cloudera AI Workbench Job for governed policy ingestion. The Job accepts PDF,
DOCX and XLSX objects from a Ranger-authorized S3A landing prefix, validates and chunks them,
stores document metadata and audit state in Iceberg through Impala, and replaces the corresponding
document chunks in `QDRANT_POLICY_COLLECTION`.

The Job is a PoC fallback for the target NiFi/CDE flow. It is not an additional CAI Application.

## Non-goals

- Candidate CV ingestion remains owned by `jobs/cv_ingestion`.
- Qdrant is not the policy system of record.
- This change does not implement the frontend upload-to-S3 route.
- It does not infer binding legal interpretations or approval decisions from policy text.

## Acceptance criteria

- Input, processed, review and failed prefixes are environment configured.
- S3 URI plus source ETag/fingerprint makes completed and review-required objects idempotent.
- PDF page, DOCX heading and XLSX sheet context are retained in citation metadata.
- Guardrails prevent empty, unsupported, suspicious or metadata-incomplete documents from indexing.
- Successful documents are registered in Iceberg and replace previous Qdrant chunks by document ID.
- Observability events contain operational metadata only, never raw policy text or credentials.
- The backend can list, inspect and download dynamically ingested policy documents through the
  existing document endpoints when `DATA_MODE=impala`.
- Dry-run performs extraction and guardrails without writing or moving any object.
