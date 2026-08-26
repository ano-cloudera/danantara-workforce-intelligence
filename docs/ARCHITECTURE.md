# Technical Architecture

## Data plane

1. NiFi ingests structured/unstructured sources and performs routing/OCR/extraction where designed.
2. Raw data lands in S3-backed Iceberg tables.
3. CDE Spark job validates/transforms raw data into curated Iceberg tables.
4. CDW/Impala reads curated Iceberg without treating CDW as a duplicate system-of-record.
5. Qdrant stores vector representations for semantic retrieval.
6. Cloudera AI Applications host the custom UX, backend orchestration, vector service and observability service.

## CAI application networking

All application entrypoints bind to loopback (`127.0.0.1`) in Cloudera AI Workbench. Listener
ports follow `CDSW_APP_PORT -> PORT -> local development default`; only the last option uses the
documented local ports. Frontend-to-backend, backend-to-Qdrant, and backend-to-observability calls
use `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and `OBSERVABILITY_BASE_URL`, respectively.

## Runtime request flows

### Talent Intelligence
Frontend -> Backend -> input guardrail -> CrewAI Talent Flow -> CDW candidate/position retrieval -> deterministic scoring -> Gemini reasoning -> output guardrail -> response -> observability.

### Policy Intelligence
Frontend conversational workspace -> Backend session state -> input guardrail -> CrewAI Policy Flow
-> Gemini query embedding -> Qdrant retrieval -> Gemini grounded generation -> citation validation
-> output guardrail -> response/feedback/PDF export -> observability. Original source files remain
governed artifacts; Qdrant stores chunks and source metadata, not the policy system of record.

### Global search

The frontend calls the backend through its same-origin proxy. Search groups safe candidate
summaries, positions, skills, and policy metadata. It does not search direct candidate identifiers
or expose unrestricted document paths.

## Identity
Prefer CAI/enterprise SSO. Frontend can read trusted CAI identity headers and forward a user identifier to backend. This PoC does not implement password authentication.

## State
SQLite persists application sessions, Policy conversation messages, feedback and upload metadata.
It does not store candidate system-of-record data. Replace it with a shared transactional store
before backend multi-replica/HA deployment.
