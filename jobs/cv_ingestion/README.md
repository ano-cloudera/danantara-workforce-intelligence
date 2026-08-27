# CAI CV ingestion Job

This one-shot Workbench Job polls the configured S3 landing prefix, extracts structured CV data,
writes governed Iceberg tables through Impala, upserts a sanitized professional profile into the
configured Workforce Qdrant candidate collection, emits operational events, and exits. Configure
the CAI scheduler to invoke it again; do not wrap it in an infinite loop.

## Workbench Job

- Script: `jobs/cv_ingestion/run_cai_job.py`
- Runtime: Python 3.10 or newer, CPU. Enable the Spark 3 runtime add-on when using the governed
  `datalake` S3A mode so the Workbench supplies its Hadoop configuration and IDBroker context.
- Schedule: start with the minimum interval supported by the Workbench, then use one minute only
  if the environment supports and needs that frequency.
- Schema run: set `CV_JOB_INIT_SCHEMA=true`, execute once, then restore it to `false`.
- First ingestion run: set `CV_JOB_DRY_RUN=true` and `CV_JOB_MAX_OBJECTS=1`.

The bootstrap installs dependencies into `.venv-cv-ingestion` with pip isolated/no-user mode.

## Storage access modes

For Cloudera AI, use the governed Data Lake path:

```env
S3_ACCESS_MODE=datalake
S3_CV_INPUT_URI=s3a://example-bucket/data/cv-collect/
S3_CV_PROCESSED_URI=s3a://example-bucket/data/cv-processed/
S3_CV_FAILED_URI=s3a://example-bucket/data/cv-failed/
HADOOP_FS_COMMAND=hadoop fs
```

The executing user or service account must have an IDBroker mapping and Ranger `cm_s3` read/write
policy for those prefixes. The adapter invokes the runtime-provided Hadoop filesystem command, so
it does not fall back to the shared Kubernetes worker-node IAM role. Use `S3_ACCESS_MODE=boto3`
with `s3://` URIs only for local development or an explicitly scoped AWS workload role.

## Initialization

Run the Workbench Job once with:

```env
CV_JOB_INIT_SCHEMA=true
```

Restore it to `false` before running ingestion. The same operation can be invoked manually with
`jobs/cv_ingestion/.venv-cv-ingestion/bin/python jobs/cv_ingestion/init_schema.py` after the
bootstrap has created the virtualenv.

The default DDL creates Iceberg format-version 2 tables inside the existing `danantara` database
because idempotent replacement uses row deletes before inserts. The executing identity needs
Ranger permissions for S3, table/view creation during initialization, and DML during scheduled
runs.

## Required environment

See `.env.example`. Important groups are:

- `S3_ACCESS_MODE`, `S3_CV_*`, `AWS_REGION`
- `GEMINI_*`
- `IMPALA_*` and `ICEBERG_*_TABLE`
- `QDRANT_BASE_URL`, `QDRANT_API_KEY`, `QDRANT_CANDIDATE_COLLECTION`
- optional `OBSERVABILITY_BASE_URL`, `OBSERVABILITY_API_KEY`

`auth=browser` JDBC URLs are for interactive sessions and cannot authenticate an unattended Job.
Use the non-interactive mechanism approved for the CAI workload/service identity.

## Data safety

Iceberg remains the system of record. Qdrant receives candidate ID, entity, S3 reference and
professional evidence only. Email, phone and raw CV text are not included in the Qdrant payload or
observability metadata.
