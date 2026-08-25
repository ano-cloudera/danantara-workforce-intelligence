# Local Development

Recommended initial sequence:

1. Copy `.env.example` to `.env`.
2. Set `GEMINI_API_KEY`.
3. Keep `DATA_MODE=demo` and `QDRANT_MODE=optional`.
4. Start observability, backend and frontend.
5. Add Qdrant when Policy Intelligence vector retrieval is being tested.

Local data ownership is explicit:

- `data/nifi-demo/` is reserved for the NiFi ingestion-to-Qdrant demo.
- `data/workforce-app/` contains Workforce fixtures, uploads and application state.
- `data/qdrant-storage/` backs the shared Qdrant process and does not isolate workloads.

The CAI launchers accept `--local-port` for local use. Outside CAI, `PORT` overrides this value;
inside CAI, `CDSW_APP_PORT` always wins. Local launchers bind to `127.0.0.1` unless
`APP_BIND_HOST` is explicitly set.

Example:

```bash
cd apps/observability && python run_cai.py --local-port 8100
cd apps/backend && python run_cai.py --local-port 8000
cd apps/frontend && BACKEND_BASE_URL=http://127.0.0.1:8000 python run_cai.py --local-port 8080
```

Local backend defaults use `QDRANT_BASE_URL=http://127.0.0.1:6333` and
`OBSERVABILITY_BASE_URL=http://127.0.0.1:8100` when those variables are blank. In Cloudera AI,
blank values remain unconfigured and must be replaced with the platform-assigned Application URLs.

After starting Qdrant, create its configured collections:

```bash
cd apps/backend && python scripts/init_qdrant_collections.py
```
