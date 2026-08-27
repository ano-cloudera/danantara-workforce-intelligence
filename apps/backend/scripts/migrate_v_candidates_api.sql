-- Run this once against Impala to widen the existing v_candidates_api view
-- with current_title/city/education fields already present in
-- candidate_master. Safe to re-run (CREATE OR REPLACE).

CREATE OR REPLACE VIEW danantara.v_candidates_api AS
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
