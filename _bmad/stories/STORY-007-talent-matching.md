# Talent matching

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Candidate scoring is deterministic; Gemini adds concise explanation without changing the business score.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- Any candidate-vector indexing or retrieval uses only the collection configured by
  `QDRANT_CANDIDATE_COLLECTION`, isolated from NiFi and policy vectors.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
