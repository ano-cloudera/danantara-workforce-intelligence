# Workforce Frontend

A lightweight custom enterprise UI hosted as a separate Cloudera AI Application. It intentionally avoids a Node build dependency so the PoC can start reliably in a Python CAI Runtime.

The frontend proxies `/api-proxy/*` to the configured backend and forwards the trusted `REMOTE-USER` identity header when available.

In Cloudera AI it binds to `127.0.0.1:${CDSW_APP_PORT}`. Port precedence is
`CDSW_APP_PORT -> PORT -> 8080` (local only). Set `BACKEND_BASE_URL` to the backend Application URL
assigned by CAI; a blank value is valid only for local fallback behavior.

The launcher supports CAI interpreter execution where `__file__` is unavailable by resolving the
Application directory from `CDSW_PROJECT_DIR` or the project working directory.
