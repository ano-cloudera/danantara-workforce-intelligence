import sys
from types import ModuleType

from app.config import Settings
from app.models import TalentMatchRequest
from app.orchestration.talent_flow import TalentMatchingFlow
from app.services.data_gateway import DataGateway


def test_demo_data_loads():
    d = DataGateway(Settings(data_mode='demo'))
    assert len(d.list_candidates()) >= 3
    assert len(d.list_positions()) >= 2


class _NullObservability:
    def emit(self, *args, **kwargs):
        pass


def test_skills_keywords_do_not_pollute_required_skills_or_gaps():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    position = gateway.list_positions()[0]
    original_required = list(position.required_skills)

    request = TalentMatchRequest(
        position_id=position.position_id,
        skills_keywords=["machine learning engineer"],
        top_n=5,
    )
    flow = TalentMatchingFlow(request, gateway, gemini=None, guardrails=None, observability=_NullObservability())
    flow.load_and_score()

    assert flow.state.position["required_skills"] == original_required
    for item in flow.state.scored:
        assert "machine learning engineer" not in item["skill_gaps"]
        assert "machine learning engineer" not in item["matched_skills"]


def test_skills_keywords_boost_score_without_shrinking_skill_denominator():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    position = gateway.list_positions()[0]
    candidate = gateway.list_candidates()[0]
    keyword = candidate.skills[0].lower()

    baseline_request = TalentMatchRequest(position_id=position.position_id, top_n=20)
    baseline_flow = TalentMatchingFlow(
        baseline_request, gateway, gemini=None, guardrails=None, observability=_NullObservability()
    )
    baseline_flow.load_and_score()
    baseline_score = next(
        item["match_score"]
        for item in baseline_flow.state.scored
        if item["candidate"]["candidate_id"] == candidate.candidate_id
    )

    boosted_request = TalentMatchRequest(
        position_id=position.position_id, skills_keywords=[keyword], top_n=20
    )
    boosted_flow = TalentMatchingFlow(
        boosted_request, gateway, gemini=None, guardrails=None, observability=_NullObservability()
    )
    boosted_flow.load_and_score()
    boosted_item = next(
        item
        for item in boosted_flow.state.scored
        if item["candidate"]["candidate_id"] == candidate.candidate_id
    )

    assert boosted_item["match_score"] >= baseline_score
    assert keyword in [k.lower() for k in boosted_item["keyword_matches"]]


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
