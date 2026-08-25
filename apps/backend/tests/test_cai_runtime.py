import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from config.cai_runtime import CAI_BIND_HOST, resolve_app_port, resolve_bind_host  # noqa: E402

LAUNCHERS = (
    ROOT / "apps/frontend/run_cai.py",
    ROOT / "apps/backend/run_cai.py",
    ROOT / "apps/qdrant/run_cai.py",
    ROOT / "apps/observability/run_cai.py",
)


def test_cdsw_app_port_takes_precedence():
    assert resolve_app_port(8000, {"CDSW_APP_PORT": "12001", "PORT": "12002"}) == 12001


def test_port_environment_is_second_precedence():
    assert resolve_app_port(8000, {"PORT": "12002"}) == 12002


def test_local_port_fallback_still_works():
    assert resolve_app_port(8000, {}) == 8000


def test_cai_always_binds_to_loopback():
    env = {"CDSW_APP_PORT": "12001", "APP_BIND_HOST": "0.0.0.0"}
    assert resolve_bind_host(env) == CAI_BIND_HOST


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_launcher_uses_shared_cai_port_resolution(launcher):
    source = launcher.read_text()
    assert "resolve_app_port" in source
    assert "resolve_bind_host" in source
    assert "parse_known_args" in source
    assert "CML_APP_PORT" not in source


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_launcher_loads_without_dunder_file(monkeypatch, tmp_path, launcher):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CDSW_PROJECT_DIR", str(ROOT))
    namespace = {"__name__": "cai_entrypoint_test"}

    exec(compile(launcher.read_text(), launcher.name, "exec"), namespace)

    assert namespace["HERE"] == launcher.parent


@pytest.mark.parametrize("launcher", LAUNCHERS)
def test_launcher_without_dunder_file_falls_back_to_project_cwd(monkeypatch, launcher):
    monkeypatch.chdir(ROOT)
    monkeypatch.delenv("CDSW_PROJECT_DIR", raising=False)
    namespace = {"__name__": "cai_entrypoint_test"}

    exec(compile(launcher.read_text(), launcher.name, "exec"), namespace)

    assert namespace["HERE"] == launcher.parent


def test_qdrant_launcher_is_standalone_in_cai_interpreter(monkeypatch, tmp_path):
    launcher = ROOT / "apps/qdrant/run_cai.py"
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CDSW_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CDSW_APP_PORT", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    namespace = {"__name__": "cai_entrypoint_test"}

    exec(compile(launcher.read_text(), launcher.name, "exec"), namespace)

    assert namespace["HERE"] == tmp_path
    assert namespace["ROOT"] == tmp_path
    assert namespace["resolve_app_port"](6333) == 6333


def test_cai_does_not_assume_local_inter_app_urls(monkeypatch):
    monkeypatch.setenv("CDSW_APP_PORT", "12001")
    monkeypatch.delenv("QDRANT_BASE_URL", raising=False)
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("OBSERVABILITY_BASE_URL", raising=False)
    monkeypatch.delenv("OBSERVABILITY_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.qdrant_base_url is None
    assert settings.observability_base_url is None


def test_local_inter_app_url_fallbacks_still_work(monkeypatch):
    for name in (
        "CDSW_APP_PORT",
        "QDRANT_BASE_URL",
        "QDRANT_URL",
        "OBSERVABILITY_BASE_URL",
        "OBSERVABILITY_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.qdrant_base_url == "http://127.0.0.1:6333"
    assert settings.observability_base_url == "http://127.0.0.1:8100"


def test_qdrant_launcher_maps_resolved_port_to_http_api():
    source = (ROOT / "apps/qdrant/run_cai.py").read_text()
    assert 'os.environ["QDRANT__SERVICE__HTTP_PORT"] = str(port)' in source
    assert "validate_binary(binary)" in source
    assert "run_qdrant(binary)" in source
    assert "os.execv" not in source


def test_inter_app_url_variables_are_declared_and_consumed():
    env_example = (ROOT / ".env.example").read_text()
    for name in ("BACKEND_BASE_URL", "QDRANT_BASE_URL", "OBSERVABILITY_BASE_URL"):
        assert f"{name}=" in env_example

    frontend_source = (ROOT / "apps/frontend/app/main.py").read_text()
    assert "BACKEND_BASE_URL" in frontend_source

    settings_source = (ROOT / "apps/backend/app/config.py").read_text()
    assert "QDRANT_BASE_URL" in settings_source
    assert "OBSERVABILITY_BASE_URL" in settings_source
