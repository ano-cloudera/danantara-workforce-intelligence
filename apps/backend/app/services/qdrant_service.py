import logging
import os
import socket
import time
import uuid
from urllib.parse import quote, urlsplit

import httpx

from app.config import Settings
from app.models import PolicySource

logger = logging.getLogger(__name__)


class QdrantRestClient:
    """Small Qdrant REST adapter that works reliably through CAI's Envoy proxy."""

    def __init__(self, base_url: str, api_key: str | None, timeout: float, trust_env: bool):
        headers = {"api-key": api_key} if api_key else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout, trust_env=trust_env
        )

    def request(self, method: str, path: str, **kwargs) -> dict:
        response = self._client.request(method, path, **kwargs)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise RuntimeError("Qdrant returned a non-ok response")
        return payload

    def get_collections(self) -> list[str]:
        payload = self.request("GET", "/collections")
        return [item["name"] for item in payload.get("result", {}).get("collections", [])]

    def get_collection(self, name: str) -> dict:
        return self.request("GET", f"/collections/{quote(name, safe='')}").get("result", {})

    def create_collection(self, name: str, vector_size: int) -> None:
        self.request(
            "PUT",
            f"/collections/{quote(name, safe='')}",
            json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        )

    def upsert(self, name: str, points: list[dict]) -> None:
        self.request(
            "PUT",
            f"/collections/{quote(name, safe='')}/points",
            params={"wait": "true"},
            json={"points": points},
        )

    def query(self, name: str, vector: list[float], limit: int) -> list[dict]:
        payload = self.request(
            "POST",
            f"/collections/{quote(name, safe='')}/points/query",
            json={"query": vector, "limit": limit, "with_payload": True},
        )
        return payload.get("result", {}).get("points", [])


class QdrantService:
    def __init__(self, settings: Settings, gemini, observability=None):
        self.settings = settings
        self.gemini = gemini
        self.observability = observability
        self.client: QdrantRestClient | None = None
        if settings.qdrant_mode == "disabled":
            return
        if not settings.qdrant_base_url:
            if settings.qdrant_mode == "required":
                raise RuntimeError("QDRANT_BASE_URL is required when QDRANT_MODE=required")
            return
        try:
            self.client = QdrantRestClient(
                settings.qdrant_base_url,
                settings.qdrant_api_key,
                settings.qdrant_timeout_seconds,
                settings.qdrant_trust_env,
            )
        except Exception as exc:
            logger.warning(
                "Qdrant REST client initialization failed: error_type=%s url_configured=%s",
                type(exc).__name__,
                bool(settings.qdrant_base_url),
            )
            if settings.qdrant_mode == "required":
                raise

    def healthy(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.get_collections()
            return True
        except Exception as exc:
            source = getattr(exc, "source", None)
            logger.warning(
                "Qdrant health check failed: error_type=%s source_type=%s timeout_seconds=%s",
                type(exc).__name__,
                type(source).__name__ if source is not None else "none",
                self.settings.qdrant_timeout_seconds,
            )
            return False

    def diagnostics(self) -> dict:
        result = {
            "configured": bool(self.settings.qdrant_base_url),
            "transport": "rest",
            "client_healthy": self.healthy(),
            "dns": {"ok": False, "error_type": None},
            "proxy_environment": {
                "http_proxy_configured": bool(os.getenv("HTTP_PROXY") or os.getenv("http_proxy")),
                "https_proxy_configured": bool(os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")),
                "no_proxy_configured": bool(os.getenv("NO_PROXY") or os.getenv("no_proxy")),
            },
            "http_probes": [],
        }
        if not self.settings.qdrant_base_url:
            return result

        parsed = urlsplit(self.settings.qdrant_base_url)
        try:
            socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            result["dns"]["ok"] = True
        except Exception as exc:
            result["dns"]["error_type"] = type(exc).__name__

        headers = {"api-key": self.settings.qdrant_api_key} if self.settings.qdrant_api_key else {}
        probe_url = f"{self.settings.qdrant_base_url.rstrip('/')}/collections"
        probe_timeout = min(self.settings.qdrant_timeout_seconds, 20.0)
        for trust_env in (False, True):
            started = time.monotonic()
            probe = {
                "trust_env": trust_env,
                "ok": False,
                "status_code": None,
                "error_type": None,
                "elapsed_ms": None,
            }
            try:
                with httpx.Client(
                    timeout=probe_timeout, trust_env=trust_env, follow_redirects=False
                ) as client:
                    response = client.get(probe_url, headers=headers)
                probe["status_code"] = response.status_code
                probe["ok"] = response.status_code == 200
            except Exception as exc:
                probe["error_type"] = type(exc).__name__
            probe["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            result["http_probes"].append(probe)
        return result

    @property
    def required_collections(self) -> tuple[str, str, str]:
        return (
            self.settings.qdrant_nifi_collection,
            self.settings.qdrant_candidate_collection,
            self.settings.qdrant_policy_collection,
        )

    def ensure_collection(self, name: str) -> bool:
        if not self.client:
            return False
        if name in set(self.client.get_collections()):
            collection = self.client.get_collection(name)
            vectors = collection.get("config", {}).get("params", {}).get("vectors", {})
            existing_size = vectors.get("size") if isinstance(vectors, dict) else None
            if existing_size is not None and existing_size != self.settings.gemini_embed_dim:
                raise RuntimeError(
                    f"Collection {name!r} has vector size {existing_size}; "
                    f"expected {self.settings.gemini_embed_dim}"
                )
            return False
        self.client.create_collection(name, self.settings.gemini_embed_dim)
        return True

    def ensure_required_collections(self) -> dict[str, bool]:
        return {name: self.ensure_collection(name) for name in self.required_collections}

    def index_policy_chunks(self, chunks: list[dict]):
        if not self.client or not chunks:
            return 0
        self.ensure_collection(self.settings.qdrant_policy_collection)
        vectors = self.gemini.embed([c["text"] for c in chunks], task_type="RETRIEVAL_DOCUMENT")
        points = [
            {"id": str(uuid.uuid4()), "vector": vector, "payload": chunk}
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.upsert(self.settings.qdrant_policy_collection, points)
        return len(points)

    def search_policies(self, query: str, top_k: int | None = None) -> list[PolicySource]:
        if not self.client:
            return []
        vector = self.gemini.embed([query], task_type="RETRIEVAL_QUERY")[0]
        points = self.client.query(
            self.settings.qdrant_policy_collection,
            vector,
            top_k or self.settings.qdrant_top_k,
        )
        sources = []
        for point in points:
            payload = point.get("payload") or {}
            sources.append(
                PolicySource(
                    source_id=str(point.get("id")),
                    entity=payload.get("entity"),
                    title=payload.get("title", "Policy Document"),
                    page=payload.get("page"),
                    score=float(point["score"]) if point.get("score") is not None else None,
                    text_excerpt=payload.get("text", "")[:1200],
                )
            )
        if self.observability:
            self.observability.emit(
                "retriever",
                "qdrant-policy-search",
                {"top_k": top_k or self.settings.qdrant_top_k, "hits": len(sources)},
            )
        return sources
