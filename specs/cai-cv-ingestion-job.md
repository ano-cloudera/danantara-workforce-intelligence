# CAI CV ingestion job

## Scope

Provide a one-shot Cloudera AI Workbench Job that discovers new CV PDFs in the configured S3
landing prefix, extracts a structured candidate profile, writes governed Iceberg tables through
Impala, indexes a sanitized professional profile in the Workforce candidate Qdrant collection,
and emits sanitized operational events to the observability Application.

## Non-goals

- The Job does not replace the NiFi team flow or change the four-Application topology.
- Qdrant is not a candidate system of record and must not contain direct contact details or raw CV
  text.
- The Job does not use SQLite for candidate data.
- The Job does not assume interactive browser authentication or embed customer endpoints/secrets.
- The Job does not run an internal infinite polling loop; CAI scheduling invokes one batch per run.

## Acceptance criteria

- S3 input, processed and failed prefixes are configurable.
- Storage access is selectable: `datalake` uses the CAI Hadoop/S3A path governed by
  IDBroker/Ranger, while `boto3` remains the local-development fallback.
- An S3 URI plus ETag is the idempotency key; completed objects are skipped.
- Candidate master, skill, experience and ingestion-audit records are written to Iceberg tables
  through configurable Impala connectivity.
- Candidate embeddings are deterministically upserted into `QDRANT_CANDIDATE_COLLECTION` read from
  configuration.
- Failures are recorded in the audit table and do not prevent remaining objects from processing.
- Observability receives only identifiers, counts, status, latency and error types.
- `--dry-run` validates discovery/extraction without mutating Impala or Qdrant.
- Unit tests cover completed-object skipping, successful ingestion and failure isolation.

## Implementation plan

1. Add an independent `jobs/cv_ingestion` package with configuration, adapters and orchestration.
2. Add Iceberg DDL and a CAI Job entrypoint.
3. Add a governed S3A adapter without removing the boto3 fallback.
4. Document Job environment variables and Workbench scheduling.
5. Add fake-adapter tests and repository preflight coverage.

## Verification

- `pytest`
- `python scripts/preflight.py`
- Local dry-run using fake/test adapters
- CAI Job target smoke test against one object before enabling the schedule
