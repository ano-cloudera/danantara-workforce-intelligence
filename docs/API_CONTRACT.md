# API Contract

Base prefix: `/api/v1`

- `GET /health`
- `GET /config/public`
- `POST /talent/match`
- `GET /search`
- `POST /policy/query`
- `POST /policy/compare`
- `POST /policy/chat`
- `GET /policy/sessions/{session_id}`
- `POST /policy/export`
- `GET /candidates`
- `GET /candidates/{candidate_id}`
- `GET /positions`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/download`
- `GET /sources`
- `POST /sources/upload`
- `POST /sources/candidate`
- `POST /feedback`
- `GET /dashboard/summary`

All AI endpoints return `session_id`, `human_review_required`, `guardrail` metadata and a request identifier.

`policy/chat` accepts a message, optional session, source filters, and retrieval options. Its sources
contain stable document/chunk IDs, entity, type, page/section, excerpt, score, and same-origin source
links. Existing Policy Query/Compare contracts remain supported. Policy export accepts only a
server-stored `request_id`; it does not trust arbitrary answer text supplied by the browser.

Candidate list, detail, and search responses exclude direct identifiers and protected HR
attributes. Current-stage and salary-compliance fields are sample snapshot values, not historical
analytics.
