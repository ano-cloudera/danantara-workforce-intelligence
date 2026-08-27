from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class JobSettings:
    aws_region: str
    input_uri: str
    processed_uri: str
    failed_uri: str
    max_objects: int
    gemini_api_key: str
    gemini_text_model: str
    gemini_embedding_model: str
    gemini_embed_dim: int
    qdrant_base_url: str
    qdrant_api_key: str | None
    qdrant_candidate_collection: str
    qdrant_timeout_seconds: float
    qdrant_trust_env: bool
    impala_host: str
    impala_port: int
    impala_database: str
    impala_auth_mechanism: str
    impala_user: str | None
    impala_password: str | None
    impala_use_ssl: bool
    impala_use_http_transport: bool
    impala_http_path: str
    candidate_master_table: str
    candidate_skills_table: str
    candidate_experience_table: str
    ingestion_audit_table: str
    observability_base_url: str | None
    observability_api_key: str | None

    @classmethod
    def from_env(cls) -> "JobSettings":
        settings = cls(
            aws_region=os.getenv("AWS_REGION", "ap-southeast-3"),
            input_uri=_required("S3_CV_INPUT_URI"),
            processed_uri=_required("S3_CV_PROCESSED_URI"),
            failed_uri=_required("S3_CV_FAILED_URI"),
            max_objects=int(os.getenv("CV_JOB_MAX_OBJECTS", "20")),
            gemini_api_key=_required("GEMINI_API_KEY"),
            gemini_text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
            gemini_embedding_model=os.getenv(
                "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
            ),
            gemini_embed_dim=int(os.getenv("GEMINI_EMBED_DIM", "768")),
            qdrant_base_url=_required("QDRANT_BASE_URL").rstrip("/"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
            qdrant_candidate_collection=_required("QDRANT_CANDIDATE_COLLECTION"),
            qdrant_timeout_seconds=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "20")),
            qdrant_trust_env=_bool("QDRANT_TRUST_ENV", False),
            impala_host=_required("IMPALA_HOST"),
            impala_port=int(os.getenv("IMPALA_PORT", "443")),
            impala_database=os.getenv("IMPALA_DATABASE", "default"),
            impala_auth_mechanism=_required("IMPALA_AUTH_MECHANISM"),
            impala_user=os.getenv("IMPALA_USER") or None,
            impala_password=os.getenv("IMPALA_PASSWORD") or None,
            impala_use_ssl=_bool("IMPALA_USE_SSL", True),
            impala_use_http_transport=os.getenv("IMPALA_TRANSPORT_MODE", "http") == "http",
            impala_http_path=os.getenv("IMPALA_HTTP_PATH", "cliservice"),
            candidate_master_table=os.getenv(
                "ICEBERG_CANDIDATE_MASTER_TABLE", "danantara.candidate_master"
            ),
            candidate_skills_table=os.getenv(
                "ICEBERG_CANDIDATE_SKILLS_TABLE", "danantara.candidate_skills"
            ),
            candidate_experience_table=os.getenv(
                "ICEBERG_CANDIDATE_EXPERIENCE_TABLE", "danantara.candidate_experience"
            ),
            ingestion_audit_table=os.getenv(
                "ICEBERG_INGESTION_AUDIT_TABLE", "danantara.cv_ingestion_audit"
            ),
            observability_base_url=(os.getenv("OBSERVABILITY_BASE_URL") or "").rstrip("/") or None,
            observability_api_key=os.getenv("OBSERVABILITY_API_KEY") or None,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        for name, uri in (
            ("S3_CV_INPUT_URI", self.input_uri),
            ("S3_CV_PROCESSED_URI", self.processed_uri),
            ("S3_CV_FAILED_URI", self.failed_uri),
        ):
            parsed = urlsplit(uri)
            if parsed.scheme != "s3" or not parsed.netloc:
                raise ValueError(f"{name} must be an s3:// URI")
        if self.max_objects < 1 or self.max_objects > 1000:
            raise ValueError("CV_JOB_MAX_OBJECTS must be between 1 and 1000")
        if self.gemini_embed_dim < 1:
            raise ValueError("GEMINI_EMBED_DIM must be positive")
        if not self.qdrant_candidate_collection.strip():
            raise ValueError("QDRANT_CANDIDATE_COLLECTION must not be empty")

    @staticmethod
    def split_s3_uri(uri: str) -> tuple[str, str]:
        parsed = urlsplit(uri)
        return parsed.netloc, parsed.path.lstrip("/")
