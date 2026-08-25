# Skill: observability-langfuse

Trace application behavior without creating a runtime dependency.

## Rules
- Emit structured events to the observability gateway.
- Include session/user IDs but avoid raw PII.
- Capture latency, tool/retrieval/generation/guardrail events.
- Keep local storage operational if Langfuse is disabled.
- Forward to Langfuse only when credentials are configured.
- In CAI, bind the gateway to `127.0.0.1:${CDSW_APP_PORT}` and have backend clients use
  `OBSERVABILITY_BASE_URL`; retain the local port only as a development fallback.
