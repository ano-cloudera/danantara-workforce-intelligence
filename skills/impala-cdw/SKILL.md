# Skill: impala-cdw

Integrate the application with governed Cloudera Data Warehouse data.

## Rules
- Use configurable Impala connection settings.
- Keep SQL parameterized or constrained by application code.
- Use curated business tables/views, not raw data.
- Maintain demo fallback until CDW connectivity is validated.
- Ranger/SDX authorization remains authoritative.
- Store policy originals in governed S3, safe metadata/audit state in Iceberg, and serve dynamic
  policy metadata through a curated Impala view. Read source files through IDBroker/Ranger S3A.
