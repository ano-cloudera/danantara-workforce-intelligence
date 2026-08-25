# Technical Architecture

## Data plane

1. NiFi ingests structured/unstructured sources and performs routing/OCR/extraction where designed.
2. Raw data lands in S3-backed Iceberg tables.
3. CDE Spark job validates/transforms raw data into curated Iceberg tables.
4. CDW/Impala reads curated Iceberg without treating CDW as a duplicate system-of-record.
5. Qdrant stores vector representations for semantic retrieval.
6. Cloudera AI Applications host the custom UX, backend orchestration, vector service and observability service.

## Runtime request flows

### Talent Intelligence
Frontend -> Backend -> input guardrail -> CrewAI Talent Flow -> CDW candidate/position retrieval -> deterministic scoring -> Gemini reasoning -> output guardrail -> response -> observability.

### Policy Intelligence
Frontend -> Backend -> input guardrail -> CrewAI Policy Flow -> Gemini query embedding -> Qdrant retrieval -> Gemini grounded generation -> citation validation -> output guardrail -> response -> observability.

## Identity
Prefer CAI/enterprise SSO. Frontend can read trusted CAI identity headers and forward a user identifier to backend. This PoC does not implement password authentication.

## State
SQLite persists application sessions, feedback and upload metadata. Replace with PostgreSQL before backend multi-replica/HA deployment.
