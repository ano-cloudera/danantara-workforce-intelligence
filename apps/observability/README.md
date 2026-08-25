# Observability Gateway

A PoC-safe LLM/agent monitoring application that is fully runnable inside Cloudera AI without requiring Langfuse infrastructure.

It stores sanitized trace events in SQLite and exposes a small dashboard. When Langfuse credentials are configured, events are also forwarded to Langfuse.

This keeps observability useful even when third-party monitoring is unavailable during the demo.

In Cloudera AI it binds to `127.0.0.1:${CDSW_APP_PORT}`. Port precedence is
`CDSW_APP_PORT -> PORT -> 8100` (local only). The backend reaches this service through the
CAI-assigned URL in `OBSERVABILITY_BASE_URL`.
