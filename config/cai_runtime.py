"""Cloudera AI Workbench application runtime conventions."""

import os
from collections.abc import Mapping

CAI_BIND_HOST = "127.0.0.1"
LOCAL_FRONTEND_PORT = 8080
LOCAL_BACKEND_PORT = 8000
LOCAL_QDRANT_PORT = 6333
LOCAL_OBSERVABILITY_PORT = 8100


def resolve_app_port(local_default: int, environ: Mapping[str, str] | None = None) -> int:
    """Resolve CDSW_APP_PORT -> PORT -> the application local default."""
    env = os.environ if environ is None else environ
    raw_port = env.get("CDSW_APP_PORT") or env.get("PORT") or str(local_default)
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Application port must be an integer, got {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"Application port must be between 1 and 65535, got {port}")
    return port


def resolve_bind_host(environ: Mapping[str, str] | None = None) -> str:
    """Always bind to loopback in CAI; allow an explicit local override outside CAI."""
    env = os.environ if environ is None else environ
    if env.get("CDSW_APP_PORT"):
        return CAI_BIND_HOST
    return env.get("APP_BIND_HOST") or CAI_BIND_HOST
