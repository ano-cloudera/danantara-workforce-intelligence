import sys
from types import ModuleType

from app.config import Settings
from app.services.data_gateway import DataGateway


def test_demo_data_loads():
    d = DataGateway(Settings(data_mode='demo'))
    assert len(d.list_candidates()) >= 3
    assert len(d.list_positions()) >= 2


def test_impala_connection_uses_configured_http_transport(monkeypatch):
    captured = {}
    dbapi = ModuleType("impala.dbapi")
    dbapi.connect = lambda **kwargs: captured.update(kwargs) or object()
    package = ModuleType("impala")
    package.dbapi = dbapi
    monkeypatch.setitem(sys.modules, "impala", package)
    monkeypatch.setitem(sys.modules, "impala.dbapi", dbapi)

    gateway = DataGateway(
        Settings(
            _env_file=None,
            data_mode="impala",
            impala_host="coordinator.example.test",
            impala_port=443,
            impala_database="danantara",
            impala_auth_mechanism="PLAIN",
            impala_transport_mode="http",
            impala_http_path="cliservice",
        )
    )

    gateway._connect()

    assert captured["use_http_transport"] is True
    assert captured["http_path"] == "cliservice"
    assert captured["port"] == 443
