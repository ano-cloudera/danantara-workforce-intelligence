# Skill: testing-release

Validate changes before PoC freeze.

## Rules
- Run preflight.
- Run backend unit tests.
- Smoke-test all `/health` endpoints.
- Test with missing optional Qdrant/Langfuse.
- Update project state and demo runbook.
