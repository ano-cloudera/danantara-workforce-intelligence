import uuid

from app.config import Settings
from app.models import PolicySource


class QdrantService:
    def __init__(self, settings: Settings, gemini, observability=None):
        self.settings = settings
        self.gemini = gemini
        self.observability = observability
        self.client = None
        if settings.qdrant_mode != "disabled":
            if not settings.qdrant_base_url:
                if settings.qdrant_mode == "required":
                    raise RuntimeError("QDRANT_BASE_URL is required when QDRANT_MODE=required")
                return
            try:
                from qdrant_client import QdrantClient

                self.client = QdrantClient(
                    url=settings.qdrant_base_url,
                    api_key=settings.qdrant_api_key,
                    timeout=5.0,
                )
            except Exception:
                if settings.qdrant_mode == "required":
                    raise

    def healthy(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

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
        from qdrant_client.models import Distance, VectorParams

        existing = {x.name for x in self.client.get_collections().collections}
        if name in existing:
            collection = self.client.get_collection(name)
            vectors = collection.config.params.vectors
            existing_size = getattr(vectors, "size", None)
            if existing_size is not None and existing_size != self.settings.gemini_embed_dim:
                raise RuntimeError(
                    f"Collection {name!r} has vector size {existing_size}; "
                    f"expected {self.settings.gemini_embed_dim}"
                )
            return False

        self.client.create_collection(
            name,
            vectors_config=VectorParams(
                size=self.settings.gemini_embed_dim, distance=Distance.COSINE
            ),
        )
        return True

    def ensure_required_collections(self) -> dict[str, bool]:
        return {name: self.ensure_collection(name) for name in self.required_collections}

    def index_policy_chunks(self, chunks: list[dict]):
        if not self.client or not chunks:
            return 0
        from qdrant_client.models import PointStruct

        self.ensure_collection(self.settings.qdrant_policy_collection)
        vectors = self.gemini.embed([c["text"] for c in chunks], task_type="RETRIEVAL_DOCUMENT")
        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=chunk))
        self.client.upsert(self.settings.qdrant_policy_collection, points=points, wait=True)
        return len(points)

    def search_policies(self, query: str, top_k: int | None = None) -> list[PolicySource]:
        if not self.client:
            return []
        vector = self.gemini.embed([query], task_type="RETRIEVAL_QUERY")[0]
        result = self.client.query_points(
            collection_name=self.settings.qdrant_policy_collection,
            query=vector,
            limit=top_k or self.settings.qdrant_top_k,
            with_payload=True,
        ).points
        sources = []
        for point in result:
            p = point.payload or {}
            sources.append(
                PolicySource(
                    source_id=str(point.id),
                    entity=p.get("entity"),
                    title=p.get("title", "Policy Document"),
                    page=p.get("page"),
                    score=float(point.score) if point.score is not None else None,
                    text_excerpt=p.get("text", "")[:1200],
                )
            )
        if self.observability:
            self.observability.emit(
                "retriever",
                "qdrant-policy-search",
                {"top_k": top_k or self.settings.qdrant_top_k, "hits": len(sources)},
            )
        return sources
