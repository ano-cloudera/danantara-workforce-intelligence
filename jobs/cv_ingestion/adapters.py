from __future__ import annotations

import hashlib
import io
import json
import logging
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from .config import JobSettings
from .models import CandidateProfile, S3Object

logger = logging.getLogger(__name__)


class S3Adapter:
    def __init__(self, settings: JobSettings):
        import boto3

        self.settings = settings
        self.client = boto3.client("s3", region_name=settings.aws_region)

    def list_pdf_objects(self) -> list[S3Object]:
        bucket, prefix = self.settings.split_s3_uri(self.settings.input_uri)
        paginator = self.client.get_paginator("list_objects_v2")
        objects: list[S3Object] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.lower().endswith(".pdf"):
                    objects.append(
                        S3Object(
                            bucket=bucket,
                            key=key,
                            etag=str(item.get("ETag", "")).strip('"'),
                            size=int(item.get("Size", 0)),
                        )
                    )
                    if len(objects) >= self.settings.max_objects:
                        return objects
        return objects

    def read(self, item: S3Object) -> bytes:
        return self.client.get_object(Bucket=item.bucket, Key=item.key)["Body"].read()

    def copy_to(self, item: S3Object, destination_uri: str) -> S3Object:
        destination_bucket, destination_prefix = self.settings.split_s3_uri(destination_uri)
        destination_key = f"{destination_prefix.rstrip('/')}/{item.key.rsplit('/', 1)[-1]}"
        self.client.copy_object(
            Bucket=destination_bucket,
            Key=destination_key,
            CopySource={"Bucket": item.bucket, "Key": item.key},
        )
        return S3Object(destination_bucket, destination_key, item.etag, item.size)

    def delete(self, item: S3Object) -> None:
        self.client.delete_object(Bucket=item.bucket, Key=item.key)


class DataLakeS3AAdapter:
    """Use the CAI Hadoop filesystem so S3A access is governed by IDBroker/Ranger."""

    def __init__(self, settings: JobSettings, runner=None):
        self.settings = settings
        self.command = shlex.split(settings.hadoop_fs_command)
        self.runner = runner or subprocess.run

    def _execute(self, *arguments: str) -> bytes:
        completed = self.runner(
            [*self.command, *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.settings.storage_command_timeout_seconds,
        )
        return completed.stdout

    @staticmethod
    def _fingerprint(path: str, size: int, modified_date: str, modified_time: str) -> str:
        value = f"{path}\0{size}\0{modified_date}\0{modified_time}".encode()
        return hashlib.sha256(value).hexdigest()

    def list_pdf_objects(self) -> list[S3Object]:
        uri = self.settings.as_s3a_uri(self.settings.input_uri)
        try:
            output = self._execute("-ls", "-R", uri).decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
            if "No such file or directory" in stderr or "does not exist" in stderr:
                return []
            raise

        objects: list[S3Object] = []
        for line in output.splitlines():
            fields = line.split(None, 7)
            if len(fields) != 8 or fields[0].startswith("d"):
                continue
            size = int(fields[4])
            path = fields[7]
            if not path.lower().endswith(".pdf"):
                continue
            bucket, key = self.settings.split_s3_uri(path)
            objects.append(
                S3Object(
                    bucket=bucket,
                    key=key,
                    etag=self._fingerprint(path, size, fields[5], fields[6]),
                    size=size,
                )
            )
            if len(objects) >= self.settings.max_objects:
                break
        return objects

    def read(self, item: S3Object) -> bytes:
        return self._execute("-cat", self.settings.as_s3a_uri(item.uri))

    def copy_to(self, item: S3Object, destination_uri: str) -> S3Object:
        destination_bucket, destination_prefix = self.settings.split_s3_uri(destination_uri)
        destination_key = f"{destination_prefix.rstrip('/')}/{item.key.rsplit('/', 1)[-1]}"
        destination_directory = self.settings.as_s3a_uri(destination_uri).rstrip("/")
        destination_path = self.settings.as_s3a_uri(
            f"s3://{destination_bucket}/{destination_key}"
        )
        self._execute("-mkdir", "-p", destination_directory)
        self._execute("-cp", "-f", self.settings.as_s3a_uri(item.uri), destination_path)
        return S3Object(destination_bucket, destination_key, item.etag, item.size)

    def delete(self, item: S3Object) -> None:
        self._execute("-rm", "-f", self.settings.as_s3a_uri(item.uri))


def build_storage_adapter(settings: JobSettings):
    if settings.storage_access_mode == "datalake":
        return DataLakeS3AAdapter(settings)
    return S3Adapter(settings)


class GeminiExtractor:
    def __init__(self, settings: JobSettings):
        from google import genai

        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)

    @staticmethod
    def _pdf_text(content: bytes) -> str:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()

    def extract(self, item: S3Object, content: bytes) -> CandidateProfile:
        from google.genai import types

        text = self._pdf_text(content)
        if not text:
            raise ValueError("PDF contains no extractable text")
        prompt = f"""Extract a professional candidate profile from the CV below.
Return JSON only with this shape:
{{
  "candidate_id": "stable ID from the filename/document or empty",
  "full_name": "candidate name",
  "entity": "target Danantara entity if explicitly present or null",
  "current_title": "latest role or null",
  "years_experience": 0.0,
  "city": null,
  "education_level": null,
  "education_institution": null,
  "professional_summary": "short evidence-based professional summary",
  "email": null,
  "phone": null,
  "skills": [{{"name":"Python","proficiency":null,"years_experience":null,"evidence":""}}],
  "experiences": [{{"employer":"","role":"","start_date":null,"end_date":null,"is_current":false,"summary":""}}],
  "education": [{{"institution":"","level":null,"field_of_study":null,"start_year":null,"end_year":null}}],
  "extraction_confidence": 0.0
}}
Do not infer protected attributes. Do not fabricate dates, proficiency, or experience. Use null when
the CV does not support a value. Source filename: {item.key.rsplit('/', 1)[-1]}

CV text:
{text[:50000]}"""
        response = self.client.models.generate_content(
            model=self.settings.gemini_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        payload = json.loads(response.text or "{}")
        if not payload.get("candidate_id"):
            filename = item.key.rsplit("/", 1)[-1]
            payload["candidate_id"] = filename.split("_", 1)[0]
        return _profile_from_dict(payload)

    def embed(self, text: str) -> list[float]:
        from google.genai import types

        config = types.EmbedContentConfig(
            output_dimensionality=self.settings.gemini_embed_dim,
            task_type="RETRIEVAL_DOCUMENT",
        )
        response = self.client.models.embed_content(
            model=self.settings.gemini_embedding_model,
            contents=[text],
            config=config,
        )
        embeddings = response.embeddings or []
        if not embeddings:
            raise RuntimeError("Gemini returned no embedding")
        return list(embeddings[0].values)


def _profile_from_dict(payload: dict[str, Any]) -> CandidateProfile:
    from .models import Education, Experience, Skill

    return CandidateProfile(
        candidate_id=str(payload["candidate_id"]),
        full_name=str(payload.get("full_name") or "Unknown"),
        entity=payload.get("entity"),
        current_title=payload.get("current_title"),
        years_experience=float(payload.get("years_experience") or 0),
        city=payload.get("city"),
        education_level=payload.get("education_level"),
        education_institution=payload.get("education_institution"),
        professional_summary=str(payload.get("professional_summary") or ""),
        email=payload.get("email"),
        phone=payload.get("phone"),
        skills=[
            Skill(
                name=str(item.get("name") or "").strip(),
                proficiency=item.get("proficiency"),
                years_experience=item.get("years_experience"),
                evidence=str(item.get("evidence") or ""),
            )
            for item in payload.get("skills", [])
            if item.get("name")
        ],
        experiences=[
            Experience(
                employer=str(item.get("employer") or ""),
                role=str(item.get("role") or ""),
                start_date=item.get("start_date"),
                end_date=item.get("end_date"),
                is_current=bool(item.get("is_current", False)),
                summary=str(item.get("summary") or ""),
            )
            for item in payload.get("experiences", [])
        ],
        education=[
            Education(
                institution=str(item.get("institution") or ""),
                level=item.get("level"),
                field_of_study=item.get("field_of_study"),
                start_year=item.get("start_year"),
                end_year=item.get("end_year"),
            )
            for item in payload.get("education", [])
        ],
        extraction_confidence=payload.get("extraction_confidence"),
    )


class QdrantAdapter:
    def __init__(self, settings: JobSettings):
        self.settings = settings
        headers = {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else {}
        self.client = httpx.Client(
            base_url=settings.qdrant_base_url,
            headers=headers,
            timeout=settings.qdrant_timeout_seconds,
            trust_env=settings.qdrant_trust_env,
        )

    def upsert(self, profile: CandidateProfile, item: S3Object, vector: list[float]) -> None:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item.uri}#{item.etag}"))
        payload = {
            "candidate_id": profile.candidate_id,
            "entity": profile.entity,
            "document_type": "CV",
            "s3_uri": item.uri,
            "source_etag": item.etag,
            "chunk_index": 0,
            "text": profile.qdrant_text(),
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        collection = quote(self.settings.qdrant_candidate_collection, safe="")
        response = self.client.put(
            f"/collections/{collection}/points",
            params={"wait": "true"},
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        )
        response.raise_for_status()
        if response.json().get("status") != "ok":
            raise RuntimeError("Qdrant returned a non-ok upsert response")


class ObservabilityAdapter:
    def __init__(self, settings: JobSettings):
        self.base_url = settings.observability_base_url
        self.api_key = settings.observability_api_key

    def emit(self, name: str, metadata: dict[str, Any]) -> None:
        logger.info("pipeline_event name=%s metadata=%s", name, metadata)
        if not self.base_url:
            return
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            httpx.post(
                f"{self.base_url}/events",
                headers=headers,
                timeout=5,
                json={
                    "event_id": str(uuid.uuid4()),
                    "ts": time.time(),
                    "event_type": "pipeline",
                    "name": name,
                    "request_id": metadata.get("ingestion_id"),
                    "metadata": metadata,
                },
            ).raise_for_status()
        except Exception as exc:
            logger.warning("Observability unavailable: error_type=%s", type(exc).__name__)


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
