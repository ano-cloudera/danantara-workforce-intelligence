# NiFi ingestion integration

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Data Sources upload can POST to configured NiFi endpoint; backend ingestion remains as fallback.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- NiFi demo files are reserved under `data/nifi-demo/` and vectors are written only to the
  collection configured by `QDRANT_NIFI_COLLECTION`.
- The NiFi collection remains distinct from both Workforce-owned collections in the shared
  Qdrant deployment.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
