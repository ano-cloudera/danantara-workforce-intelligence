# Qdrant vector store

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Policy/CV vectors can be indexed and retrieved with configurable collections and dimension.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- One shared deployment uses separate, environment-configured collections for NiFi documents,
  Workforce candidates and Workforce policies.
- Backend Qdrant operations contain no hardcoded collection names.
- An idempotent utility creates all three collections when missing using the configured embedding
  dimension.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
