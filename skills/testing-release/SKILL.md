# Skill: testing-release

Validate changes before PoC freeze.

## Rules
- Run preflight.
- Run backend unit tests.
- Smoke-test all `/health` endpoints.
- Test with missing optional Qdrant/Langfuse.
- Update project state and demo runbook.
- Verify `CDSW_APP_PORT -> PORT -> local default`, loopback binding in CAI, absence of exposed-port
  literals in launchers, and environment-configured cross-Application URLs.
- Import every CAI launcher in a namespace without `__file__` to simulate Workbench interpreter
  execution.
