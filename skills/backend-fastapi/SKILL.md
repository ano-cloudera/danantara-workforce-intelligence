# Skill: backend-fastapi

Implement stable backend API behavior.

## Rules
- Keep endpoints under `/api/v1`.
- Return Pydantic structured responses.
- Use service abstractions for Gemini, Qdrant, CDW, guardrails and observability.
- Add timeouts and graceful optional-service failures.
- Do not put business scoring inside prompts.
