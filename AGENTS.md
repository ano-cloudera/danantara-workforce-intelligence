@RTK.md

# Coding Agent Instructions

Before changing code:

1. Read `START_HERE.md`.
2. Read `PROJECT_STATE.md`.
3. Read `_bmad/project-state.yaml`.
4. Read `skills/delivery-method-selector/SKILL.md` and select direct, spec-kit, or BMAD delivery.
5. Read the other relevant `skills/*/SKILL.md`.
6. Read a story under `_bmad/stories/` only when BMAD is selected or the task changes that story's
   acceptance criteria.

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
- Do not use BMAD as the default for every change; use the lightest delivery method that safely
  covers the scope.
