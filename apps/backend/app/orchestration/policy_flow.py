from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen

from app.models import PolicyQueryRequest


class PolicyState(BaseModel):
    request: dict = {}
    sources: list[dict] = []
    answer: str = ""


class PolicyRAGFlow(Flow[PolicyState]):
    def __init__(self, request: PolicyQueryRequest, qdrant, fallback, gemini, observability):
        super().__init__()
        self.state.request = request.model_dump()
        self.qdrant = qdrant
        self.fallback = fallback
        self.gemini = gemini
        self.observability = observability

    @start()
    def retrieve(self):
        req = PolicyQueryRequest(**self.state.request)
        sources = []
        if self.qdrant and self.qdrant.healthy():
            sources = self.qdrant.search_policies(req.question, req.top_k)
            if req.entities:
                allowed = {e.lower() for e in req.entities}
                sources = [s for s in sources if not s.entity or s.entity.lower() in allowed]
        if not sources:
            sources = self.fallback.search(req.question, req.entities, req.top_k or 6)
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
        prompt = f"""Answer the user's workforce-policy question using only the supplied sources. If sources are insufficient, say so. Cite sources inline using [1], [2], etc. Do not invent policy rules.\n\nQuestion: {req.question}\n\nSources:\n{context}\n"""
        self.state.answer = self.gemini.generate_text(prompt, "policy-grounded-generation")
        return self.state.answer
