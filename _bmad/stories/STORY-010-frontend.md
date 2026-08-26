# Frontend experience

**Status:** redesigned / local and CAI environment validation pending

## Acceptance criteria
- Talent, Policy, Data Sources and Settings pages operate against backend API through frontend proxy.
- Overview and the operational Dashboard use current PoC backend summaries without fabricated
  enterprise-scale metrics; Cloudera Data Visualization remains the primary analytics destination.
- All six pages share the supplied enterprise visual language, responsive navigation, explicit
  async states, and named `lucide-react` icon imports.
- Global search groups candidates, positions, skills, and policies and remains available through a
  compact overlay on tablet/mobile layouts.
- Policy Intelligence is a citation-first multi-turn workspace with source access, feedback, and
  PDF export; it does not turn the overall product into a generic chatbot shell.
- Reference-only candidates and the incorrect `NHS` entity are excluded; demo fixtures use BNS,
  ENP, and NSH.
- Configuration is documented.
- Failure behavior is explicit.
- No secrets are committed.
- The frontend binds to `127.0.0.1:${CDSW_APP_PORT}` in CAI and proxies only to the configured
  `BACKEND_BASE_URL`.

## Dev handoff
Read the relevant skill under `/skills` before modifying this story. Update `PROJECT_STATE.md` after a material architecture decision.
