# Frontend redesign specification

## Scope

Redesign the existing vanilla HTML/CSS/JavaScript frontend into the six-page Danantara Workforce
Intelligence enterprise PoC experience shown in the supplied references, without changing the
FastAPI frontend proxy or four-Application CAI topology.

## Non-goals

- No React application migration or Node build pipeline.
- No new authentication, settings persistence, or fabricated production-scale data.
- No change to backend business scoring or AI orchestration.

## Acceptance criteria

- Overview, Talent, Policy, Dashboard, Data Sources, and Settings share one responsive application
  shell and work without full-page reloads.
- Visible business data comes from existing backend responses or is explicitly marked as PoC state.
- The UI uses named `lucide-react` imports with the prescribed icon sizes and stroke widths.
- Talent and Policy preserve result-first and citation-first behavior through `/api-proxy`.
- All async actions expose loading, success, empty, disabled, and error states.
- No secret, `NHS`, screenshot candidate, or unrelated company value is rendered.
- `BACKEND_BASE_URL`, `CDV_DASHBOARD_URL`, `CDSW_APP_PORT`, identity propagation, and the frontend
  proxy contract remain unchanged.

## Verification

Run backend/frontend tests and preflight, start both Applications locally, inspect all six views at
desktop width, and exercise Talent Match, Policy Query/Compare, upload, candidate registration,
dashboard summary, and health paths.
