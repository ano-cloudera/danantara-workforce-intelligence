# Configuration and CAI entrypoints

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- All four applications start from repository scripts; ports and secrets are environment-driven.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- Qdrant collection ownership is configured with `QDRANT_NIFI_COLLECTION`,
  `QDRANT_CANDIDATE_COLLECTION` and `QDRANT_POLICY_COLLECTION`; values are non-empty and unique.
- Local workload files remain under their owner-specific `data/nifi-demo/` or
  `data/workforce-app/` root.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
