CREATE TABLE IF NOT EXISTS danantara.policy_documents (
  document_id STRING,
  entity STRING,
  title STRING,
  document_type STRING,
  document_version STRING,
  file_name STRING,
  source_s3_uri STRING,
  source_etag STRING,
  content_hash STRING,
  page_count INT,
  chunk_count INT,
  ingestion_id STRING,
  extraction_status STRING,
  guardrail_status STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS danantara.policy_ingestion_audit (
  ingestion_id STRING,
  document_id STRING,
  s3_uri STRING,
  s3_etag STRING,
  content_hash STRING,
  file_name STRING,
  file_size_bytes BIGINT,
  pipeline_status STRING,
  guardrail_reasons STRING,
  extractor_version STRING,
  received_at TIMESTAMP,
  processed_at TIMESTAMP,
  error_code STRING,
  error_message STRING
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE VIEW IF NOT EXISTS danantara.v_policy_documents_api AS
SELECT
  document_id,
  title,
  entity,
  document_type,
  document_version AS version,
  file_name,
  source_s3_uri,
  extraction_status,
  guardrail_status,
  page_count,
  chunk_count,
  updated_at
FROM danantara.policy_documents;
