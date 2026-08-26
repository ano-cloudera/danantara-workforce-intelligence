# Danantara Additional Iceberg Sample Sources

This package supplements the existing PoC source files with structured sample datasets for the Data Lakehouse / Iceberg flow.

## Files

- `candidate_master.csv` -> `talent_profile.candidate_master`
- `candidate_skills.csv` -> `talent_profile.candidate_skills`
- `candidate_experience.csv` -> `talent_profile.candidate_experience`
- `recruitment_status.csv` -> `recruitment.recruitment_status`
- `policy_rules.csv` -> `policy_regulation.policy_rules`
- `manifest.json` -> dataset-to-table mapping and implementation notes

## Recommended Flow

Existing source files
-> Cloudera DataFlow / NiFi
-> S3 Raw
-> validation / normalization
-> Iceberg Curated tables
-> CDW / Impala
-> Cloudera Data Visualization / AI application

## Important

`recruitment_status.csv` contains synthetic demo fields (`match_score_demo`, `salary_compliance_demo`) created specifically to make dashboard and PoC workflows more meaningful.

The candidate master, skills, and experience data are derived from the submitted CV samples.

The policy rules dataset contains selected structured facts derived from the submitted Group Policy and BNS/ENP PKB documents.

Keep the original PDF, DOCX, and XLSX files as raw/source artifacts. Do not replace them with these curated CSV files.
