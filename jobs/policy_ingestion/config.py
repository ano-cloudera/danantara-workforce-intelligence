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
class PolicyJobSettings:
    storage_access_mode: str
    hadoop_fs_command: str
    storage_command_timeout_seconds: float
    aws_region: str
    input_uri: str
    processed_uri: str
    review_uri: str
    failed_uri: str
    max_objects: int
    max_file_bytes: int
    max_chunks: int
    gemini_api_key: str
    gemini_text_model: str
    gemini_embedding_model: str
    gemini_embed_dim: int
    qdrant_base_url: str
    qdrant_api_key: str | None
    qdrant_policy_collection: str
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
    policy_document_table: str
    policy_audit_table: str
    observability_base_url: str | None
    observability_api_key: str | None

    @classmethod
    def from_env(cls) -> "PolicyJobSettings":
        settings = cls(
            storage_access_mode=os.getenv("S3_ACCESS_MODE", "boto3").strip().lower(),
            hadoop_fs_command=os.getenv("HADOOP_FS_COMMAND", "hadoop fs").strip(),
            storage_command_timeout_seconds=float(os.getenv("S3_COMMAND_TIMEOUT_SECONDS", "120")),
            aws_region=os.getenv("AWS_REGION", "ap-southeast-3"),
            input_uri=_required("S3_POLICY_INPUT_URI"),
            processed_uri=_required("S3_POLICY_PROCESSED_URI"),
            review_uri=_required("S3_POLICY_REVIEW_URI"),
            failed_uri=_required("S3_POLICY_FAILED_URI"),
            max_objects=int(os.getenv("POLICY_JOB_MAX_OBJECTS", "20")),
            max_file_bytes=int(os.getenv("POLICY_JOB_MAX_FILE_BYTES", str(50 * 1024 * 1024))),
            max_chunks=int(os.getenv("POLICY_JOB_MAX_CHUNKS", "500")),
            gemini_api_key=_required("GEMINI_API_KEY"),
            gemini_text_model=os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
            gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            gemini_embed_dim=int(os.getenv("GEMINI_EMBED_DIM", "768")),
            qdrant_base_url=_required("QDRANT_BASE_URL").rstrip("/"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
            qdrant_policy_collection=_required("QDRANT_POLICY_COLLECTION"),
            qdrant_timeout_seconds=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "20")),
            qdrant_trust_env=_bool("QDRANT_TRUST_ENV", False),
            impala_host=_required("IMPALA_HOST"),
            impala_port=int(os.getenv("IMPALA_PORT", "443")),
            impala_database=os.getenv("IMPALA_DATABASE", "danantara"),
            impala_auth_mechanism=_required("IMPALA_AUTH_MECHANISM"),
            impala_user=os.getenv("IMPALA_USER") or None,
            impala_password=os.getenv("IMPALA_PASSWORD") or None,
            impala_use_ssl=_bool("IMPALA_USE_SSL", True),
            impala_use_http_transport=os.getenv("IMPALA_TRANSPORT_MODE", "http") == "http",
            impala_http_path=os.getenv("IMPALA_HTTP_PATH", "cliservice"),
            policy_document_table=os.getenv(
                "ICEBERG_POLICY_DOCUMENT_TABLE", "danantara.policy_documents"
            ),
            policy_audit_table=os.getenv(
                "ICEBERG_POLICY_AUDIT_TABLE", "danantara.policy_ingestion_audit"
            ),
            observability_base_url=(os.getenv("OBSERVABILITY_BASE_URL") or "").rstrip("/") or None,
            observability_api_key=os.getenv("OBSERVABILITY_API_KEY") or None,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.storage_access_mode not in {"boto3", "datalake"}:
            raise ValueError("S3_ACCESS_MODE must be boto3 or datalake")
        if not 1 <= self.max_objects <= 1000:
            raise ValueError("POLICY_JOB_MAX_OBJECTS must be between 1 and 1000")
        if self.max_file_bytes < 1 or self.max_chunks < 1 or self.gemini_embed_dim < 1:
            raise ValueError("Policy Job limits and embedding dimension must be positive")
        for name, uri in (
            ("S3_POLICY_INPUT_URI", self.input_uri),
            ("S3_POLICY_PROCESSED_URI", self.processed_uri),
            ("S3_POLICY_REVIEW_URI", self.review_uri),
            ("S3_POLICY_FAILED_URI", self.failed_uri),
        ):
            parsed = urlsplit(uri)
            allowed = {"s3"} if self.storage_access_mode == "boto3" else {"s3", "s3a"}
            if parsed.scheme not in allowed or not parsed.netloc:
                raise ValueError(f"{name} must be a governed S3 URI")

    @staticmethod
    def split_s3_uri(uri: str) -> tuple[str, str]:
        parsed = urlsplit(uri)
        return parsed.netloc, parsed.path.lstrip("/")

    @staticmethod
    def as_s3a_uri(uri: str) -> str:
        parsed = urlsplit(uri)
        return f"s3a://{parsed.netloc}/{parsed.path.lstrip('/')}"
