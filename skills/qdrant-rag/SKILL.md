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
- Use the Qdrant REST adapter through `httpx` for backend health, collection management, indexing,
  and retrieval so CAI Istio/Envoy transport behavior is consistent. Do not make SDK health the
  production readiness signal.
- Policy ingestion must delete existing points by `document_id` before upserting stable chunk IDs
  into the configured `QDRANT_POLICY_COLLECTION`; every chunk carries governed citation metadata.
