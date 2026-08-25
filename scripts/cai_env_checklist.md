# CAI Environment Checklist

All Applications: use injected `CDSW_APP_PORT`; do not set a fixed exposed port.
Backend secrets/config: Gemini, `QDRANT_BASE_URL`, `OBSERVABILITY_BASE_URL`, optional Impala and NiFi.
Frontend config: `BACKEND_BASE_URL` and optional CDV URL.
Qdrant config: API key, storage path, optional custom binary/download URL.
Observability config: API key and optional Langfuse credentials.
Networking: bind to `127.0.0.1`; validate the CAI Application URL `/health` after deployment.
