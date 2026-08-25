# API Contract

Base prefix: `/api/v1`

- `GET /health`
- `GET /config/public`
- `POST /talent/match`
- `POST /policy/query`
- `POST /policy/compare`
- `GET /candidates`
- `GET /positions`
- `POST /sources/upload`
- `POST /sources/candidate`
- `POST /feedback`
- `GET /dashboard/summary`

All AI endpoints return `session_id`, `human_review_required`, `guardrail` metadata and a request identifier.
