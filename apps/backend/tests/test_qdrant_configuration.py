from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.qdrant_service import QdrantService


def test_qdrant_collection_defaults_are_workload_isolated(monkeypatch):
    for name in (
        "QDRANT_NIFI_COLLECTION",
        "QDRANT_CANDIDATE_COLLECTION",
        "QDRANT_POLICY_COLLECTION",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)

    assert settings.qdrant_nifi_collection == "nifi_documents"
    assert settings.qdrant_candidate_collection == "workforce_candidates"
    assert settings.qdrant_policy_collection == "workforce_policies"


def test_qdrant_collection_names_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("QDRANT_NIFI_COLLECTION", "demo_nifi")
    monkeypatch.setenv("QDRANT_CANDIDATE_COLLECTION", "demo_candidates")
    monkeypatch.setenv("QDRANT_POLICY_COLLECTION", "demo_policies")

    settings = Settings(_env_file=None)

    assert settings.qdrant_nifi_collection == "demo_nifi"
    assert settings.qdrant_candidate_collection == "demo_candidates"
    assert settings.qdrant_policy_collection == "demo_policies"


def test_inter_app_base_urls_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("QDRANT_BASE_URL", "https://qdrant.example.test/")
    monkeypatch.setenv("OBSERVABILITY_BASE_URL", "https://observability.example.test/")

    settings = Settings(_env_file=None)

    assert settings.qdrant_base_url == "https://qdrant.example.test"
    assert settings.observability_base_url == "https://observability.example.test"


def test_qdrant_collection_names_must_be_unique():
    with pytest.raises(ValidationError, match="must be unique"):
        Settings(
            _env_file=None,
            qdrant_nifi_collection="shared_documents",
            qdrant_candidate_collection="shared_documents",
        )


def test_policy_search_uses_configured_collection_name():
    settings = Settings(
        _env_file=None,
        qdrant_mode="disabled",
        qdrant_policy_collection="custom_workforce_policies",
    )
    gemini = SimpleNamespace(embed=lambda *_args, **_kwargs: [[0.1] * settings.gemini_embed_dim])
    service = QdrantService(settings, gemini)

    class FakeClient:
        def __init__(self):
            self.collection_name = None

        def query_points(self, *, collection_name, **_kwargs):
            self.collection_name = collection_name
            return SimpleNamespace(points=[])

    service.client = FakeClient()
    assert service.search_policies("leave policy") == []
    assert service.client.collection_name == "custom_workforce_policies"


def test_initializer_targets_all_configured_collections():
    settings = Settings(_env_file=None, qdrant_mode="disabled")
    service = QdrantService(settings, gemini=None)
    visited = []
    service.ensure_collection = lambda name: visited.append(name) or True

    results = service.ensure_required_collections()

    assert visited == [
        settings.qdrant_nifi_collection,
        settings.qdrant_candidate_collection,
        settings.qdrant_policy_collection,
    ]
    assert all(results.values())
