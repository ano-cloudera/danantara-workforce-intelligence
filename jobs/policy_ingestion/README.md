# Policy ingestion Workbench Job

This bounded job is the PoC fallback for policy ingestion. Production ingestion remains owned by
NiFi/CDE. The source document stays governed in S3; Impala stores safe metadata/audit fields and
Qdrant stores citation-ready chunks.

Use `jobs/policy_ingestion/run_cai_job.py` as the Cloudera AI Workbench Job script. Set
`POLICY_JOB_INIT_SCHEMA=true` for the first run only. Then set it to `false`, validate one document
with `POLICY_JOB_DRY_RUN=true`, and finally set dry-run to `false`.

In Cloudera AI use `S3_ACCESS_MODE=datalake` so `hadoop fs` uses IDBroker/Ranger. Grant the Job
identity read/write access to `policy-collect`, `policy-processed`, `policy-review`, and
`policy-failed`. Do not configure static AWS credentials.
