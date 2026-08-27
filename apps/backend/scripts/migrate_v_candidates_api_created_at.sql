-- Run this once against Impala to add created_at to the existing
-- v_candidates_api view, needed for the "candidates by month" chat chart.
-- Impala does not support CREATE OR REPLACE VIEW, so this drops and
-- recreates the view; safe to re-run.

DROP VIEW IF EXISTS danantara.v_candidates_api;

CREATE VIEW danantara.v_candidates_api AS
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
  master.professional_summary AS summary,
  master.created_at
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
  master.professional_summary,
  master.created_at;
