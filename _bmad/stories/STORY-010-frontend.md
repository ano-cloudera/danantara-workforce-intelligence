# Frontend experience

**Status:** scaffolded / environment validation pending

## Acceptance criteria
- Talent, Policy, Data Sources and Settings pages operate against backend API through frontend proxy.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- The frontend binds to `127.0.0.1:${CDSW_APP_PORT}` in CAI and proxies only to the configured
  `BACKEND_BASE_URL`.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
