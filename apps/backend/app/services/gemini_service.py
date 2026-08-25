import json
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings


class GeminiService:
    def __init__(self, settings: Settings, observability=None):
        self.settings = settings
        self.observability = observability
        if settings.gemini_backend == "vertex_ai":
            self.client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
        else:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_text(self, prompt: str, name: str = "gemini-generation") -> str:
        started = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.settings.gemini_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.settings.gemini_temperature,
            ),
        )
        text = response.text or ""
        if self.observability:
            self.observability.emit(
                "generation", name,
                {"model": self.settings.gemini_text_model, "latency_ms": round((time.perf_counter()-started)*1000,2), "output_chars": len(text)},
            )
        return text

    def generate_json(self, prompt: str, name: str = "gemini-json") -> Any:
        started = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.settings.gemini_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.settings.gemini_temperature,
                response_mime_type="application/json",
            ),
        )
        raw = response.text or "{}"
        if self.observability:
            self.observability.emit(
                "generation", name,
                {"model": self.settings.gemini_text_model, "latency_ms": round((time.perf_counter()-started)*1000,2), "json": True},
            )
        return json.loads(raw)

    def embed(self, texts: list[str], task_type: str | None = None) -> list[list[float]]:
        config = types.EmbedContentConfig(output_dimensionality=self.settings.gemini_embed_dim)
        if task_type:
            try:
                config.task_type = task_type
            except Exception:
                pass
        response = self.client.models.embed_content(
            model=self.settings.gemini_embedding_model,
            contents=texts,
            config=config,
        )
        vectors = [list(item.values) for item in (response.embeddings or [])]
        if self.observability:
            self.observability.emit("embedding", "gemini-embedding", {"model": self.settings.gemini_embedding_model, "count": len(texts), "dimension": self.settings.gemini_embed_dim})
        return vectors

    def health(self) -> dict:
        return {
            "backend": self.settings.gemini_backend,
            "text_model": self.settings.gemini_text_model,
            "embedding_model": self.settings.gemini_embedding_model,
            "configured": bool(self.settings.gemini_api_key) if self.settings.gemini_backend == "gemini_api" else bool(self.settings.google_cloud_project),
        }
