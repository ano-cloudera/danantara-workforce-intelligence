import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"), extra="ignore", populate_by_name=True
    )

    environment: str = "poc"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    auth_mode: Literal["cai", "demo"] = "cai"
    demo_user: str = "demo.hr@danantara.local"

    gemini_backend: Literal["gemini_api", "vertex_ai"] = "gemini_api"
    gemini_api_key: str | None = None
    gemini_text_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embed_dim: int = 768
    gemini_temperature: float = 0.2
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"

    orchestrator_mode: Literal["crewai", "native"] = "crewai"
    data_mode: Literal["demo", "impala"] = "demo"
    ingest_mode: Literal["backend", "nifi"] = "backend"
    sqlite_path: str = "./data/workforce-app/app_state.db"
    upload_dir: str = "./data/workforce-app/uploads"
    cors_origins: str = "*"

    qdrant_mode: Literal["required", "optional", "disabled"] = "optional"
    qdrant_base_url: str | None = Field(
        default=None, validation_alias=AliasChoices("QDRANT_BASE_URL", "QDRANT_URL")
    )
    qdrant_api_key: str | None = None
    qdrant_timeout_seconds: float = Field(default=5.0, gt=0, le=120)
    qdrant_nifi_collection: str = "nifi_documents"
    qdrant_candidate_collection: str = "workforce_candidates"
    qdrant_policy_collection: str = "workforce_policies"
    qdrant_top_k: int = 6

    impala_host: str | None = None
    impala_port: int = 443
    impala_database: str = "default"
    impala_auth_mechanism: str = "PLAIN"
    impala_user: str | None = None
    impala_password: str | None = None
    impala_use_ssl: bool = True
    impala_candidate_table: str = "curated_candidate_profiles"
    impala_position_table: str = "curated_job_positions"

    nifi_ingest_url: str | None = None
    nifi_bearer_token: str | None = None

    guardrails_mode: Literal["builtin", "off"] = "builtin"
    guardrails_max_input_chars: int = 12000
    guardrails_require_policy_citations: bool = True

    observability_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OBSERVABILITY_BASE_URL", "OBSERVABILITY_URL"),
    )
    observability_api_key: str | None = None

    @field_validator("qdrant_base_url", "observability_base_url", mode="before")
    @classmethod
    def normalize_optional_base_url(cls, value):
        if isinstance(value, str):
            value = value.strip().rstrip("/")
            return value or None
        return value

    @model_validator(mode="after")
    def validate_qdrant_collection_names(self):
        names = {
            "QDRANT_NIFI_COLLECTION": self.qdrant_nifi_collection,
            "QDRANT_CANDIDATE_COLLECTION": self.qdrant_candidate_collection,
            "QDRANT_POLICY_COLLECTION": self.qdrant_policy_collection,
        }
        if any(not name.strip() for name in names.values()):
            raise ValueError("Qdrant collection names must not be empty")
        if len(set(names.values())) != len(names):
            raise ValueError("Qdrant collection names must be unique across demo workloads")
        if not os.getenv("CDSW_APP_PORT"):
            self.qdrant_base_url = self.qdrant_base_url or "http://127.0.0.1:6333"
            self.observability_base_url = self.observability_base_url or "http://127.0.0.1:8100"
        return self

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def sqlite_file(self) -> Path:
        p = Path(self.sqlite_path)
        return p if p.is_absolute() else self.project_root / p

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        return p if p.is_absolute() else self.project_root / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
