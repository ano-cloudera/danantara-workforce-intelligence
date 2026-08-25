#!/usr/bin/env python3
from app.config import get_settings
from app.services.gemini_service import GeminiService
from app.services.observability import ObservabilityClient
from app.services.qdrant_service import QdrantService

settings = get_settings()
obs = ObservabilityClient(settings)
gemini = GeminiService(settings, obs)
qdrant = QdrantService(settings, gemini, obs)
chunks = []
for path in (settings.project_root / "data" / "workforce-app" / "demo" / "policies").glob("*.txt"):
    entity = path.name.split("_", 1)[0]
    chunks.append(
        {
            "entity": entity,
            "title": path.stem.replace("_", " "),
            "page": 1,
            "text": path.read_text(),
            "source_path": str(path),
        }
    )
count = qdrant.index_policy_chunks(chunks)
print(f"Indexed {count} demo policy chunks into {settings.qdrant_policy_collection}")
