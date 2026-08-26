import re

from app.config import Settings
from app.models import PolicySource
from app.services.policy_documents import load_policy_chunks


class PolicyFallback:
    def __init__(self, settings: Settings):
        self.chunks = load_policy_chunks(settings)

    def search(
        self,
        query: str,
        entities: list[str] | None = None,
        top_k: int = 6,
        document_types: list[str] | None = None,
    ) -> list[PolicySource]:
        words = {word.lower() for word in re.findall(r"[A-Za-z0-9]+", query) if len(word) > 2}
        synonyms = {
            "annual": {"tahunan"},
            "leave": {"cuti"},
            "overtime": {"lembur"},
            "notice": {"pemberitahuan"},
            "salary": {"gaji", "upah"},
            "probation": {"percobaan"},
            "recruitment": {"rekrutmen"},
        }
        words.update(term for word in list(words) for term in synonyms.get(word, set()))
        allowed_entities = {entity.lower() for entity in entities or []}
        allowed_types = {value.lower() for value in document_types or []}
        rows = []
        for chunk in self.chunks:
            entity = chunk.get("entity")
            if allowed_entities and (entity or "").lower() not in allowed_entities:
                continue
            if allowed_types and (chunk.get("document_type") or "").lower() not in allowed_types:
                continue
            text = chunk.get("text", "")
            score = sum(text.lower().count(word) for word in words)
            rows.append(
                (
                    score,
                    PolicySource(
                        source_id=chunk["chunk_id"],
                        document_id=chunk["document_id"],
                        entity=entity,
                        title=chunk["title"],
                        document_type=chunk.get("document_type"),
                        page=chunk.get("page"),
                        section=chunk.get("section"),
                        score=float(score),
                        text_excerpt=text[:1200],
                        view_url=f'/api/v1/documents/{chunk["document_id"]}',
                        download_url=f'/api/v1/documents/{chunk["document_id"]}/download',
                    ),
                )
            )
        rows.sort(key=lambda item: (item[0], item[1].entity or ""), reverse=True)
        selected: list[PolicySource] = []
        if entities:
            for requested_entity in entities:
                match = next(
                    (
                        source
                        for _, source in rows
                        if (source.entity or "").lower() == requested_entity.lower()
                        and source not in selected
                    ),
                    None,
                )
                if match:
                    selected.append(match)
        for _, source in rows:
            if len(selected) >= top_k:
                break
            if source not in selected:
                selected.append(source)
        return selected[:top_k]
