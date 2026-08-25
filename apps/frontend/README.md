# Workforce Frontend

A lightweight custom enterprise UI hosted as a separate Cloudera AI Application. It intentionally avoids a Node build dependency so the PoC can start reliably in a Python CAI Runtime.

The frontend proxies `/api-proxy/*` to the configured backend and forwards the trusted `REMOTE-USER` identity header when available.
