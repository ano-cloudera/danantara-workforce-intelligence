@RTK.md

# Coding Agent Instructions

Before changing code:

1. Read `START_HERE.md`.
2. Read `PROJECT_STATE.md`.
3. Read `_bmad/project-state.yaml`.
4. Read the relevant `skills/*/SKILL.md`.
5. Read the story file under `_bmad/stories/` if the work maps to an existing story.

Rules:

- Preserve the four-application topology unless the architecture story is explicitly reopened.
- Gemini calls must use `from google import genai` in the core provider.
- Do not introduce LangChain into baseline architecture.
- Prefer CrewAI Flows for deterministic orchestration.
- Never store candidate system-of-record data in SQLite.
- Never hardcode secrets or customer endpoints.
- Keep API responses structured and UI-stable.
- Keep guardrails and observability as cross-cutting services, not agent tools.
- All external services must have timeouts and graceful failure behavior.
- Update `PROJECT_STATE.md` and `_bmad/project-state.yaml` after significant implementation decisions.
