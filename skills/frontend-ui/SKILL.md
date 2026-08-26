# Skill: frontend-ui

Continue the enterprise HR UI without turning the whole product into a generic chatbot shell.

## Rules
- Keep Talent Intelligence result-first.
- Keep Policy Intelligence citation-first. It may use a conversational, multi-turn workspace when
  every answer retains visible sources, human-review messaging, feedback, and export controls.
- Keep global search available at desktop, tablet, and mobile widths; compact layouts may use a
  search overlay instead of removing the capability.
- Use same-origin frontend proxy for backend calls.
- Resolve the proxy target from `BACKEND_BASE_URL`; require it in CAI and retain loopback fallback
  only for local development.
- Never expose backend secrets in browser configuration.
- CDV remains the primary management dashboard.
- Use `lucide-react` exclusively for interface icons with named imports. Navigation icons use
  `size={20}` / `strokeWidth={1.75}`, buttons use `size={16}` / `strokeWidth={2}`, and stat cards
  use `size={24}` / `strokeWidth={1.5}`; color is controlled through utility classes.
- Treat UI references as layout and visual-language targets only. Render backend/PoC data and show
  explicit unavailable states instead of copying reference values.
