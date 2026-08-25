from app.config import Settings
from app.models import PolicySource


class PolicyFallback:
    def __init__(self, settings: Settings):
        self.root = settings.project_root / "data" / "demo" / "policies"

    def search(self, query: str, entities: list[str] | None = None, top_k: int = 6) -> list[PolicySource]:
        words = {w.lower() for w in query.split() if len(w) > 3}
        rows = []
        for path in self.root.glob("*.txt"):
            entity = path.name.split("_", 1)[0]
            if entities and entity.lower() not in {e.lower() for e in entities}:
                continue
            text = path.read_text()
            score = sum(text.lower().count(w) for w in words)
            rows.append((score, PolicySource(source_id=path.name, entity=entity, title=path.stem.replace('_',' '), score=float(score), text_excerpt=text[:1200])))
        rows.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in rows[:top_k]]
