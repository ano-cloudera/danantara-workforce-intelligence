# PoC data, Policy chat, and global search specification

## Scope

Use the supplied `sample/data` and `sample/additional` package to power the existing six-page
Workforce Intelligence frontend. Extend the current API without changing the four-Application CAI
topology or removing the existing Talent and Policy endpoints.

## Non-goals

- No production-scale or historical values may be fabricated.
- Candidate source-of-record data remains in Iceberg/CDW; SQLite stores Application sessions,
  messages, feedback, uploads, and other PoC state only.
- No generic chatbot replaces the enterprise application shell. Policy Intelligence becomes a
  citation-first conversational workspace.
- No browser-facing endpoint exposes secrets, unrestricted filesystem paths, or sensitive candidate
  identity fields.

## Data contract

- Candidate summaries expose role, entity, experience, education, skills, safe application status,
  salary-band compliance, and source labels. Date of birth, gender, marital status, NIK, address,
  email, phone, and expected salary are excluded from public list/search responses.
- Positions expose entity, grade, department, openings, status, open date, and competencies.
- Dashboard data is a current PoC snapshot. Historical series are returned only when a real source
  exists.
- Policy sources use stable document IDs and include title, entity, document type, page/section,
  excerpt, retrieval score, and same-origin view/download links where available.

## API extensions

- `GET /api/v1/search` returns grouped candidate, position, skill, and policy results.
- `GET /api/v1/candidates/{candidate_id}` returns the safe enriched candidate profile.
- `POST /api/v1/policy/chat` preserves Policy sessions and returns grounded answer metadata.
- `GET /api/v1/policy/sessions/{session_id}` returns Policy conversation history.
- `POST /api/v1/policy/export` generates a PDF from a server-stored answer.
- `GET /api/v1/documents/{document_id}` and `/download` expose only allowlisted PoC documents.
- Existing `/policy/query`, `/policy/compare`, `/feedback`, `/candidates`, `/positions`, and Talent
  contracts remain compatible.

## UX acceptance criteria

- Desktop search is aligned and sized independently of the sidebar brand column.
- Tablet/mobile search remains available through a search trigger and full-width overlay.
- Search results are grouped and keyboard accessible.
- Policy supports multi-turn questions, inline citations, a source panel, source download/view,
  copy, thumbs up/down, and PDF export.
- On narrow screens Policy filters and sources stack without horizontal overflow; the composer
  remains usable.
- All data-dependent states include loading, empty, success, and error behavior.

## Verification

- Unit tests cover sample import, enriched summaries, search grouping, Policy message persistence,
  export, feedback compatibility, document allowlisting, and legacy Policy endpoints.
- Frontend contract tests cover responsive search, Policy chat controls, citations, export, and
  Lucide icon constraints.
- Run the repository preflight and local backend/frontend smoke checks.
