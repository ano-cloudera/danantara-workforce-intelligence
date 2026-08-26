#!/usr/bin/env python3
from app.config import get_settings
from app.services.gemini_service import GeminiService
from app.services.observability import ObservabilityClient
from app.services.policy_documents import load_policy_chunks
from app.services.qdrant_service import QdrantService

settings = get_settings()
obs = ObservabilityClient(settings)
gemini = GeminiService(settings, obs)
qdrant = QdrantService(settings, gemini, obs)
chunks = load_policy_chunks(settings)
count = qdrant.index_policy_chunks(chunks)
print(f"Indexed {count} supplied policy chunks into {settings.qdrant_policy_collection}")
