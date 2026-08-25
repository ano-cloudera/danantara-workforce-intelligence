import logging
import time
import uuid
from contextvars import ContextVar

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)
_context: ContextVar[dict] = ContextVar("observability_context", default={})


class ObservabilityClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def set_context(self, *, session_id: str | None = None, user_id: str | None = None, request_id: str | None = None):
        _context.set({"session_id": session_id, "user_id": user_id, "request_id": request_id})

    def emit(self, event_type: str, name: str, metadata: dict | None = None):
        payload = {
            "event_id": str(uuid.uuid4()),
            "ts": time.time(),
            "event_type": event_type,
            "name": name,
            "metadata": metadata or {},
            **_context.get(),
        }
        logger.info("OBS %s", payload)
        if not self.settings.observability_url:
            return
        headers = {}
        if self.settings.observability_api_key:
            headers["X-API-Key"] = self.settings.observability_api_key
        try:
            httpx.post(f"{self.settings.observability_url.rstrip('/')}/events", json=payload, headers=headers, timeout=2.5)
        except Exception as exc:
            logger.warning("Observability gateway unavailable: %s", exc)
