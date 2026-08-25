# Skill: frontend-ui

Continue the enterprise HR UI without turning it into a chatbot shell.

## Rules
- Keep Talent Intelligence result-first.
- Keep Policy Intelligence citation-first.
- Use same-origin frontend proxy for backend calls.
- Resolve the proxy target from `BACKEND_BASE_URL`; require it in CAI and retain loopback fallback
  only for local development.
- Never expose backend secrets in browser configuration.
- CDV remains the primary management dashboard.
