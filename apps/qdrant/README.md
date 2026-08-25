# Qdrant CAI Application

This launcher runs the official Qdrant binary as a Cloudera AI Application. Version and download URL are configurable.

Default validated project value: `QDRANT_VERSION=1.19.0`.

If target CAI egress blocks GitHub downloads, upload the matching Qdrant binary to `apps/qdrant/bin/qdrant` and make it executable. The launcher prefers the local binary.

Set a strong `QDRANT_API_KEY` in hidden Application variables.

This is one shared Qdrant deployment. Workload isolation is provided by three unique collection
settings, not by separate storage folders:

- `QDRANT_NIFI_COLLECTION=nifi_documents`
- `QDRANT_CANDIDATE_COLLECTION=workforce_candidates`
- `QDRANT_POLICY_COLLECTION=workforce_policies`

Use `QDRANT_STORAGE_PATH=./data/qdrant-storage` for local persistent storage. From
`apps/backend`, run `python scripts/init_qdrant_collections.py` after Qdrant starts to create any
missing collections with `GEMINI_EMBED_DIM` as the vector size. Existing collections are retained;
the utility fails clearly if an existing vector size is incompatible.

In Cloudera AI, the HTTP API listens on `127.0.0.1:${CDSW_APP_PORT}` through
`QDRANT__SERVICE__HTTP_PORT`. Port precedence is `CDSW_APP_PORT -> PORT -> 6333`, where `6333` is
strictly the local-development fallback. Backend clients use `QDRANT_BASE_URL` set to the CAI
Application URL and never infer this listener port.

The launcher also supports CAI interpreter execution where `__file__` is unavailable by resolving
`apps/qdrant` from `CDSW_PROJECT_DIR` or the current project directory. If Workbench executes the
source as interpreter code without either location, the launcher bootstraps from the interpreter
working directory instead of failing path discovery. Validate the deployed
service through `/healthz` and `/readyz`.
