# Skill: qdrant-rag

Implement vector indexing and retrieval safely.

## Rules
- Collection dimension must match Gemini embedding dimension.
- Store source metadata and chunk IDs in payload.
- Return source labels/page metadata for citations.
- Treat Qdrant as complementary storage, not system-of-record.
- Support optional Qdrant mode during early development.
- Treat one Qdrant deployment as shared infrastructure. Reserve `QDRANT_NIFI_COLLECTION` for the
  NiFi demo and use `QDRANT_CANDIDATE_COLLECTION` / `QDRANT_POLICY_COLLECTION` for Workforce.
- Read every collection name from `Settings`; never place collection-name literals in backend
  indexing or retrieval services.
- Require the three collection names to be non-empty and unique. Filesystem folders are not a
  Qdrant workload-isolation mechanism.
- Use the idempotent collection initialization utility after deploying or reconfiguring Qdrant.
- In CAI, expose Qdrant HTTP on `127.0.0.1:${CDSW_APP_PORT}` and connect through the configured
  `QDRANT_BASE_URL`; `6333` is local-development fallback only.
