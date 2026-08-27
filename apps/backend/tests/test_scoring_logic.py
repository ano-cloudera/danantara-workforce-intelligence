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


def test_get_position_by_title_raises_when_ambiguous_across_entities():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    try:
        gateway.get_position(title="Senior Data Engineer")
        assert False, "expected ValueError for an ambiguous title"
    except ValueError as exc:
        assert "BNS" in str(exc) and "ENP" in str(exc)


def test_get_position_by_title_and_entity_resolves_uniquely():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    position = gateway.get_position(title="Senior Data Engineer", entity="ENP")

    assert position.position_id == "REQ-ENP-002"
    assert position.entity == "ENP"


def test_ambiguous_title_with_no_entity_scores_each_candidate_against_their_own_entity_position():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    positions = gateway.get_positions_by_title("Senior Data Engineer")
    assert {p.entity for p in positions} == {"BNS", "ENP"}
    bns_position = next(p for p in positions if p.entity == "BNS")
    enp_position = next(p for p in positions if p.entity == "ENP")
    assert bns_position.required_skills != enp_position.required_skills

    request = TalentMatchRequest(position_title="Senior Data Engineer", top_n=20)
    flow = TalentMatchingFlow(request, gateway, gemini=None, guardrails=None, observability=_NullObservability())
    flow.load_and_score()

    assert flow.state.position["title"] == "Senior Data Engineer"
    assert set(flow.state.position["matched_entities"]) == {"BNS", "ENP"}

    scored_by_candidate = {item["candidate"]["candidate_id"]: item for item in flow.state.scored}
    other_positions = [p for p in gateway.list_positions() if p.title != "Senior Data Engineer"]
    for candidate in gateway.list_candidates():
        item = scored_by_candidate.get(candidate.candidate_id)
        if candidate.company == "BNS":
            assert item is not None
            assert item["position_id"] == bns_position.position_id
        elif candidate.company == "ENP":
            assert item is not None
            assert item["position_id"] == enp_position.position_id
        else:
            assert item is None


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
