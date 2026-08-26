import socket
import sys
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


def test_qdrant_timeout_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("QDRANT_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("QDRANT_CHECK_COMPATIBILITY", "false")
    monkeypatch.setenv("QDRANT_TRUST_ENV", "false")

    settings = Settings(_env_file=None)

    assert settings.qdrant_timeout_seconds == 20
    assert settings.qdrant_check_compatibility is False
    assert settings.qdrant_trust_env is False


def test_qdrant_client_uses_configured_timeout(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules, "qdrant_client", SimpleNamespace(QdrantClient=fake_client)
    )
    settings = Settings(
        _env_file=None,
        qdrant_base_url="https://qdrant.example.test",
        qdrant_timeout_seconds=20,
    )

    QdrantService(settings, gemini=None)

    assert captured["timeout"] == 20
    assert captured["check_compatibility"] is False
    assert captured["trust_env"] is False


def test_qdrant_health_logs_safe_error_type(caplog):
    settings = Settings(
        _env_file=None,
        qdrant_mode="disabled",
        qdrant_api_key="do-not-log-this-key",
        qdrant_timeout_seconds=20,
    )
    service = QdrantService(settings, gemini=None)
    service.client = SimpleNamespace(
        get_collections=lambda: (_ for _ in ()).throw(TimeoutError("connection timed out"))
    )

    assert service.healthy() is False
    assert "error_type=TimeoutError" in caplog.text
    assert "source_type=none" in caplog.text
    assert "do-not-log-this-key" not in caplog.text


def test_qdrant_health_logs_wrapped_source_type(caplog):
    class WrappedTransportError(Exception):
        def __init__(self):
            self.source = TimeoutError("connection timed out")

    settings = Settings(_env_file=None, qdrant_mode="disabled")
    service = QdrantService(settings, gemini=None)
    service.client = SimpleNamespace(
        get_collections=lambda: (_ for _ in ()).throw(WrappedTransportError())
    )

    assert service.healthy() is False
    assert "error_type=WrappedTransportError" in caplog.text
    assert "source_type=TimeoutError" in caplog.text


def test_qdrant_diagnostics_never_exposes_endpoint_or_api_key(monkeypatch):
    settings = Settings(
        _env_file=None,
        qdrant_mode="disabled",
        qdrant_base_url="https://secret-qdrant.example.test",
        qdrant_api_key="do-not-expose-this-key",
    )
    service = QdrantService(settings, gemini=None)
    monkeypatch.setattr(
        "app.services.qdrant_service.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )

    class FakeResponse:
        status_code = 200

    class FakeHttpClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _url, headers):
            assert headers == {"api-key": "do-not-expose-this-key"}
            return FakeResponse()

    monkeypatch.setattr("app.services.qdrant_service.httpx.Client", FakeHttpClient)

    result = service.diagnostics()
    serialized = str(result)

    assert result["dns"]["ok"] is True
    assert all(probe["ok"] for probe in result["http_probes"])
    assert "secret-qdrant.example.test" not in serialized
    assert "do-not-expose-this-key" not in serialized


def test_qdrant_client_minor_matches_server_release():
    requirements = (Settings(_env_file=None).project_root / "apps/backend/requirements.txt").read_text()

    assert "qdrant-client>=1.19,<1.20" in requirements


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
