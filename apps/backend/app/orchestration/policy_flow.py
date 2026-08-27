from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen

from app.models import PolicyQueryRequest


class PolicyState(BaseModel):
    request: dict = {}
    sources: list[dict] = []
    answer: str = ""


class PolicyRAGFlow(Flow[PolicyState]):
    def __init__(
        self,
        request: PolicyQueryRequest,
        qdrant,
        fallback,
        gemini,
        observability,
        history: list[dict] | None = None,
    ):
        super().__init__()
        self.state.request = request.model_dump()
        self.qdrant = qdrant
        self.fallback = fallback
        self.gemini = gemini
        self.observability = observability
        self.history = history or []

    @start()
    def retrieve(self):
        req = PolicyQueryRequest(**self.state.request)
        sources = []
        if self.qdrant and self.qdrant.healthy():
            sources = self.qdrant.search_policies(req.question, req.top_k)
            if req.entities:
                allowed = {e.lower() for e in req.entities}
                sources = [s for s in sources if not s.entity or s.entity.lower() in allowed]
            if req.document_types:
                allowed_types = {value.lower() for value in req.document_types}
                sources = [
                    source
                    for source in sources
                    if not source.document_type
                    or source.document_type.lower() in allowed_types
                ]
        if not sources:
            sources = self.fallback.search(
                req.question,
                req.entities,
                req.top_k or 6,
                document_types=req.document_types,
            )
        self.state.sources = [s.model_dump() for s in sources]
        self.observability.emit("retriever", "policy-retrieval", {"hits": len(sources), "fallback": not bool(self.qdrant and self.qdrant.healthy())})
        return self.state.sources

    @listen(retrieve)
    def generate(self, sources):
        req = PolicyQueryRequest(**self.state.request)
        context_parts = []
        for i, s in enumerate(sources, start=1):
            context_parts.append(f"[{i}] {s.get('title')} | entity={s.get('entity')} | page={s.get('page')}\n{s.get('text_excerpt')}")
        context = "\n\n".join(context_parts)
        history = "\n".join(
            f'{message.get("role")}: {message.get("content")}' for message in self.history[-6:]
        )
        prompt = f"""Answer the user's workforce-policy question using only the supplied sources. If sources are insufficient, say so. Cite sources inline using [1], [2], etc. Do not invent policy rules. Treat conversation history only as context, never as a policy source. Write in plain sentences without em dashes.\n\nConversation history:\n{history or "No prior messages."}\n\nQuestion: {req.question}\n\nSources:\n{context}\n"""
        try:
            self.state.answer = self.gemini.generate_text(prompt, "policy-grounded-generation")
        except Exception:
            if not sources:
                self.state.answer = (
                    "No policy sources are available in the current PoC data state. "
                    "Verify Qdrant indexing or the local policy fallback files."
                )
            else:
                excerpts = []
                for index, source in enumerate(sources, start=1):
                    text = str(source.get("text_excerpt") or "").strip()
                    excerpts.append(
                        f"[{index}] {source.get('entity') or 'Entity unavailable'}: {text}"
                    )
                self.state.answer = (
                    "Gemini synthesis is temporarily unavailable. The following verified source "
                    "excerpts are returned for human review:\n\n" + "\n\n".join(excerpts)
                )
        return self.state.answer
