# Workforce Frontend

A lightweight custom enterprise UI hosted as a separate Cloudera AI Application. It intentionally avoids a Node build dependency so the PoC can start reliably in a Python CAI Runtime.

The frontend proxies `/api-proxy/*` to the configured backend and forwards the trusted `REMOTE-USER` identity header when available.

In Cloudera AI it binds to `127.0.0.1:${CDSW_APP_PORT}`. Port precedence is
`CDSW_APP_PORT -> PORT -> 8080` (local only). Set `BACKEND_BASE_URL` to the backend Application URL
assigned by CAI; a blank value is valid only for local fallback behavior.

The launcher supports CAI interpreter execution where `__file__` is unavailable by resolving the
Application directory from `CDSW_PROJECT_DIR` or the project working directory.

## Frontend structure

- `index.html`: responsive application shell and semantic markup for all six views.
- `styles.css`: CSS-variable design system matching the enterprise reference language.
- `api.js`: same-origin `/api-proxy/*` request helper and structured errors.
- `app.js`: navigation, API-backed rendering, forms, and UI states.
- `icons.js`: named `lucide-react` imports rendered with the required size/stroke tokens.

The icon module is isolated from core UI behavior and loaded from a pinned ESM package. If the CAI
environment blocks public ESM delivery, vendor the pinned React/Lucide modules into `/static`
before production freeze; the textual UI and interactions remain available if icons cannot load.
The current brand mark is an explicit placeholder until the official Danantara logo asset is
provided.

## Page-to-API mapping

| Page | Backend routes |
|---|---|
| Overview | `health`, `config/public`, `candidates`, `positions`, `dashboard/summary` |
| Talent Intelligence | `positions`, `candidates`, `candidates/{id}`, `talent/match` |
| Policy Intelligence | `policy/chat`, `policy/sessions/{id}`, `policy/export`, `feedback`, `documents/{id}` |
| Dashboard | `dashboard/summary`, `health`; `CDV_DASHBOARD_URL` for the primary dashboard |
| Data Sources | `sources`, `sources/upload`, `sources/candidate` |
| Settings | `config/public`, `health` |

The header search calls the grouped backend search endpoint and becomes a full-width overlay on
compact layouts. Policy Intelligence keeps a multi-turn session, visible citations, source
view/download, feedback, and PDF export. Known PoC limitations are still shown directly: historical
recruitment trends and persisted display settings are unavailable, while current recruitment and
salary-compliance values come from the supplied sample snapshot.
