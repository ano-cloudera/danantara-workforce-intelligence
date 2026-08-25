import re
from pathlib import Path

import httpx
from pypdf import PdfReader

from app.config import Settings


class DocumentIngestionService:
    def __init__(self, settings: Settings, qdrant, store, observability=None):
        self.settings = settings
        self.qdrant = qdrant
        self.store = store
        self.observability = observability
        settings.upload_path.mkdir(parents=True, exist_ok=True)

    def save_and_process(self, file_name: str, content: bytes, entity: str | None = None, doc_type: str | None = None) -> dict:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(file_name).name)
        path = self.settings.upload_path / safe
        path.write_bytes(content)
        upload_id = self.store.add_upload(file_name, str(path), "uploaded", {"entity": entity, "doc_type": doc_type})
        if self.settings.ingest_mode == "nifi" and self.settings.nifi_ingest_url:
            headers = {"Authorization": f"Bearer {self.settings.nifi_bearer_token}"} if self.settings.nifi_bearer_token else {}
            resp = httpx.post(self.settings.nifi_ingest_url, files={"file": (file_name, content)}, data={"entity": entity or "", "doc_type": doc_type or ""}, headers=headers, timeout=30)
            resp.raise_for_status()
            return {"upload_id": upload_id, "status": "forwarded_to_nifi", "path": str(path)}
        indexed = 0
        if path.suffix.lower() == ".pdf" and self.qdrant and self.qdrant.client:
            chunks = self._pdf_chunks(path, entity=entity)
            indexed = self.qdrant.index_policy_chunks(chunks)
        return {"upload_id": upload_id, "status": "processed_backend_fallback", "indexed_chunks": indexed, "path": str(path)}

    def _pdf_chunks(self, path: Path, entity: str | None):
        reader = PdfReader(str(path))
        chunks = []
        for page_no, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            size = 1800
            overlap = 250
            pos = 0
            while pos < len(text):
                chunk = text[pos:pos+size]
                chunks.append({"entity": entity, "title": path.stem, "page": page_no, "text": chunk, "source_path": str(path)})
                if pos + size >= len(text): break
                pos += size - overlap
        return chunks
