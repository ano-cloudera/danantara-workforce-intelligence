CREATE TABLE IF NOT EXISTS danantara.recruitment_pipeline (
  application_id STRING,
  candidate_id STRING,
  entity STRING,
  position_id STRING,
  stage STRING,
  status STRING,
  match_score DECIMAL(5,1),
  salary_compliance STRING,
  updated_at TIMESTAMP
) STORED BY ICEBERG
TBLPROPERTIES ('format-version'='2');

CREATE VIEW IF NOT EXISTS danantara.v_recruitment_pipeline_api AS
SELECT
  application_id,
  candidate_id,
  entity,
  position_id,
  stage,
  status,
  match_score,
  salary_compliance,
  updated_at
FROM danantara.recruitment_pipeline;
