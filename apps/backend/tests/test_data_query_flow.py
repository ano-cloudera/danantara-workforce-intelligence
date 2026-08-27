from unittest.mock import MagicMock

from app.config import Settings
from app.orchestration.data_query_flow import DataQueryFlow, QUERY_REGISTRY
from app.services.data_gateway import DataGateway


class _NullObservability:
    def emit(self, *args, **kwargs):
        pass


class _FakeGemini:
    def __init__(self, classify_response, narration="Here is your answer."):
        self.classify_response = classify_response
        self.narration = narration

    def generate_json(self, prompt, name="gemini-json"):
        return self.classify_response

    def generate_text(self, prompt, name="gemini-text"):
        return self.narration


def _mock_impala_connection(rows: list[tuple]) -> MagicMock:
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    return connection


def test_unknown_query_id_from_gemini_is_rejected_not_executed():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "drop_all_tables", "entity": None})
    flow = DataQueryFlow("do something bad", None, gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert flow.state.query_id == ""
    assert flow.state.result == {}


def test_null_query_id_from_gemini_falls_through_cleanly():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": None, "entity": None})
    flow = DataQueryFlow("what's the weather", None, gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert flow.state.result == {}


def test_candidate_count_query_runs_against_demo_data():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "candidate_count", "entity": None})
    flow = DataQueryFlow("how many candidates do we have?", None, gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert flow.state.query_id == "candidate_count"
    assert flow.state.result["summary"]["total"] == len(gateway.list_candidates())
    assert flow.state.result["chart"]["items"]


def test_candidate_count_with_entity_skips_chart():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "candidate_count", "entity": None})
    flow = DataQueryFlow("how many BNS candidates?", "BNS", gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert flow.state.result["summary"]["entity"] == "BNS"
    assert flow.state.result["chart"] is None


def test_narrate_produces_answer_via_gemini():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "candidate_count", "entity": None}, narration="We have 4 candidates.")
    flow = DataQueryFlow("how many candidates?", None, gateway, gemini, _NullObservability())

    result = flow.classify_and_run()
    answer = flow.narrate(result)

    assert answer == "We have 4 candidates."
    assert flow.state.answer == "We have 4 candidates."


def test_narrate_falls_back_when_gemini_fails():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    class _BrokenGemini(_FakeGemini):
        def generate_text(self, prompt, name="gemini-text"):
            raise RuntimeError("gemini down")

    gemini = _BrokenGemini({"query_id": "candidate_count", "entity": None})
    flow = DataQueryFlow("how many candidates?", None, gateway, gemini, _NullObservability())

    result = flow.classify_and_run()
    answer = flow.narrate(result)

    assert answer
    assert "candidates" in flow.state.answer.lower() or "total" in flow.state.answer.lower()


def test_open_positions_summary_runs_against_demo_data():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "open_positions_summary", "entity": None})
    flow = DataQueryFlow("how many open positions?", None, gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert flow.state.result["summary"]["open_positions"] >= 0


def test_recruitment_stage_breakdown_runs_against_demo_data():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    gemini = _FakeGemini({"query_id": "recruitment_stage_breakdown", "entity": None})
    flow = DataQueryFlow("what's the pipeline breakdown?", None, gateway, gemini, _NullObservability())

    flow.classify_and_run()

    assert "by_stage" in flow.state.result["summary"]


def test_all_registry_query_ids_have_a_handler():
    from app.orchestration.data_query_flow import QUERY_HANDLERS

    assert set(QUERY_REGISTRY) == set(QUERY_HANDLERS)


def test_impala_candidates_by_month_groups_and_orders(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    connection = _mock_impala_connection([("2026-06", 3), ("2026-07", 5)])
    monkeypatch.setattr(gateway, "_connect", lambda: connection)

    rows = gateway._impala_candidates_by_month()

    assert rows == [("2026-06", 3), ("2026-07", 5)]


def test_candidates_by_month_demo_mode_returns_empty():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    assert gateway.candidates_by_month() == []


def test_candidates_by_month_falls_back_to_empty_on_impala_error(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)

    def broken_connect():
        raise RuntimeError("no route to host")

    monkeypatch.setattr(gateway, "_connect", broken_connect)

    assert gateway.candidates_by_month() == []


def test_policy_query_response_kind_defaults_to_grounded():
    from app.models import GuardrailResult, PolicyQueryResponse

    response = PolicyQueryResponse(
        request_id="r1", session_id="s1", answer="answer", sources=[],
        guardrail=GuardrailResult(allowed=True, reasons=[]),
    )

    assert response.response_kind == "grounded"


def test_policy_query_response_accepts_conversational_kind_with_no_chart_or_sources():
    from app.models import GuardrailResult, PolicyQueryResponse

    response = PolicyQueryResponse(
        request_id="r1", session_id="s1", answer="Hello!", sources=[],
        guardrail=GuardrailResult(allowed=True, reasons=[]),
        response_kind="conversational",
    )

    assert response.response_kind == "conversational"
    assert response.chart is None
    assert response.sources == []
