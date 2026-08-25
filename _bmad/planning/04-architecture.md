# Architecture Decision Record

## Runtime topology
Four CAI Applications: frontend, backend, qdrant, observability.

## Backend
FastAPI + CrewAI Flows + direct Google Gen AI SDK calls. This avoids dependence on Agent Studio provider support while keeping orchestration inside Cloudera AI.

## Data
Iceberg is the system-of-record lakehouse. CDW/Impala is the SQL serving layer. Qdrant stores vectors. SQLite stores application state.

### Shared Qdrant workload boundaries

The single Qdrant deployment is shared by two independent demos. NiFi owns
`QDRANT_NIFI_COLLECTION` (`nifi_documents` by default). Workforce Intelligence owns
`QDRANT_CANDIDATE_COLLECTION` and `QDRANT_POLICY_COLLECTION` (`workforce_candidates` and
`workforce_policies`). These names are environment-configured, non-empty and mutually unique;
backend indexing and retrieval must never embed collection literals.

Local files follow the matching ownership boundary: `data/nifi-demo/` is reserved for the NiFi
team and `data/workforce-app/` contains Workforce demo fixtures, uploads and application state.
The shared `data/qdrant-storage/` directory is an implementation detail of the Qdrant deployment,
not an isolation mechanism.

## Guardrails
Guardrails are executed as middleware/service checks before workflow execution and before returning the final answer.

## Observability
Backend emits structured events to a small observability gateway. The gateway remains functional without third-party services and can optionally forward to Langfuse.
