# Observability Gateway

A PoC-safe LLM/agent monitoring application that is fully runnable inside Cloudera AI without requiring Langfuse infrastructure.

It stores sanitized trace events in SQLite and exposes a small dashboard. When Langfuse credentials are configured, events are also forwarded to Langfuse.

This keeps observability useful even when third-party monitoring is unavailable during the demo.
