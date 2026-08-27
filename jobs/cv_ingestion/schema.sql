CREATE TABLE IF NOT EXISTS danantara.candidate_master (
  candidate_id STRING,
  entity STRING,
  full_name STRING,
  current_title STRING,
  years_experience DECIMAL(5,1),
  city STRING,
  education_level STRING,
  education_institution STRING,
  professional_summary STRING,
  email STRING,
  phone STRING,
  source_cv_s3_uri STRING,
  source_etag STRING,
  ingestion_id STRING,
  extraction_status STRING,
  extraction_confidence DECIMAL(5,4),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS danantara.candidate_skills (
  candidate_id STRING,
  skill_name STRING,
  normalized_skill_name STRING,
  proficiency_score INT,
  years_experience DECIMAL(5,1),
  evidence_text STRING,
  confidence_score DECIMAL(5,4),
  ingestion_id STRING
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS danantara.candidate_experience (
  candidate_id STRING,
  experience_sequence INT,
  employer STRING,
  role_title STRING,
  start_date STRING,
  end_date STRING,
  is_current BOOLEAN,
  description STRING,
  ingestion_id STRING
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE TABLE IF NOT EXISTS danantara.cv_ingestion_audit (
  ingestion_id STRING,
  candidate_id STRING,
  s3_uri STRING,
  s3_etag STRING,
  content_hash STRING,
  file_name STRING,
  file_size_bytes BIGINT,
  pipeline_status STRING,
  extractor_version STRING,
  received_at TIMESTAMP,
  processed_at TIMESTAMP,
  error_code STRING,
  error_message STRING
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE VIEW IF NOT EXISTS danantara.v_candidates_api AS
SELECT
  master.candidate_id,
  master.full_name AS name,
  master.entity AS company,
  master.current_title,
  master.years_experience,
  master.city,
  master.education_level,
  master.education_institution,
  GROUP_CONCAT(skills.skill_name, ',') AS skills,
  master.professional_summary AS summary
FROM danantara.candidate_master master
LEFT JOIN danantara.candidate_skills skills
  ON master.candidate_id = skills.candidate_id
GROUP BY
  master.candidate_id,
  master.full_name,
  master.entity,
  master.current_title,
  master.years_experience,
  master.city,
  master.education_level,
  master.education_institution,
  master.professional_summary;
