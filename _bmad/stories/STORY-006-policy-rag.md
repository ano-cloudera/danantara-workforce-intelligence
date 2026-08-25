# Policy RAG

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Questions retrieve relevant policy chunks and return grounded answers with citations.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- Policy indexing and retrieval use only the collection configured by
  `QDRANT_POLICY_COLLECTION`, isolated from NiFi and candidate vectors.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
