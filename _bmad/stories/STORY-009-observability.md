# Observability

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Workflow/tool/generation events are captured locally and can optionally be forwarded to Langfuse.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- The gateway binds to `127.0.0.1:${CDSW_APP_PORT}` in CAI and backend clients use the configured
  `OBSERVABILITY_BASE_URL`.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
