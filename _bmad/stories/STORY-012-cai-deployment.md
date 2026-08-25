# CAI deployment and demo rehearsal

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Application variables, startup scripts, health checks and demo runbook are documented and validated.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- All four Applications resolve `CDSW_APP_PORT -> PORT -> local default`, bind to loopback in CAI,
  and contain no fixed CAI exposed ports.
- `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and `OBSERVABILITY_BASE_URL` use CAI-assigned URLs.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
