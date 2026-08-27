import logging
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from pypdf import PdfReader

from app.config import Settings

logger = logging.getLogger(__name__)

CV_DOCUMENT_TYPES = {"Candidate CV"}


class DocumentIngestionService:
    def __init__(self, settings: Settings, qdrant, store, observability=None):
        self.settings = settings
        self.qdrant = qdrant
        self.store = store
        self.observability = observability
        settings.upload_path.mkdir(parents=True, exist_ok=True)

    def save_and_process(self, file_name: str, content: bytes, entity: str | None = None, doc_type: str | None = None) -> dict:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(file_name).name)

        if self.settings.upload_access_mode == "datalake":
            return self._save_to_datalake(safe, content, entity, doc_type)

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

    def _save_to_datalake(self, safe_name: str, content: bytes, entity: str | None, doc_type: str | None) -> dict:
        is_cv = (doc_type or "") in CV_DOCUMENT_TYPES
        landing_uri = self.settings.s3_cv_landing_uri if is_cv else self.settings.s3_policy_landing_uri
        if not landing_uri:
            raise RuntimeError(
                f"{'S3_CV_LANDING_URI' if is_cv else 'S3_POLICY_LANDING_URI'} is not configured"
            )
        parsed = urlsplit(landing_uri)
        if parsed.scheme not in {"s3", "s3a"} or not parsed.netloc:
            raise RuntimeError("Landing URI must be a governed s3a:// or s3:// path")
        governed_dir = f"s3a://{parsed.netloc}/{parsed.path.lstrip('/')}".rstrip("/")
        governed_path = f"{governed_dir}/{safe_name}"

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe_name).suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            self._run_hadoop_fs("-mkdir", "-p", governed_dir)
            self._run_hadoop_fs("-put", "-f", tmp_path, governed_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        upload_id = self.store.add_upload(
            safe_name, governed_path, "landed_datalake", {"entity": entity, "doc_type": doc_type}
        )
        target = "cv" if is_cv else "policy"
        return {
            "upload_id": upload_id,
            "status": "landed_datalake",
            "path": governed_path,
            "routing": f"awaiting_{target}_ingestion_job",
        }

    def _run_hadoop_fs(self, *arguments: str) -> None:
        try:
            subprocess.run(
                [*shlex.split(self.settings.hadoop_fs_command), *arguments],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.settings.source_command_timeout_seconds,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("Governed upload failed: arguments=%s error_type=%s", arguments, type(exc).__name__)
            raise RuntimeError("Governed S3A upload failed") from exc

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
