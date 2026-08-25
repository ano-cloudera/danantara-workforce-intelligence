# Skill: crewai-flow

Build deterministic application workflows with CrewAI Flows.

## Rules
- Prefer `Flow`, `@start` and `@listen` for API orchestration.
- Use flow state for business workflow state, not enterprise persistence.
- Call the project Gemini provider directly from flow steps.
- Keep retrieval, scoring, reasoning and validation as distinct steps.
- Agent Studio remains a showcase-only path unless project state changes.
