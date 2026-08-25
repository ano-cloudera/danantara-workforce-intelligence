# Skill: backend-fastapi

Implement stable backend API behavior.

## Rules
- Keep endpoints under `/api/v1`.
- Return Pydantic structured responses.
- Use service abstractions for Gemini, Qdrant, CDW, guardrails and observability.
- Add timeouts and graceful optional-service failures.
- Do not put business scoring inside prompts.
- In CAI, bind FastAPI to `127.0.0.1:${CDSW_APP_PORT}` and resolve Qdrant/observability only from
  `QDRANT_BASE_URL` and `OBSERVABILITY_BASE_URL` (legacy aliases may remain compatibility-only).
