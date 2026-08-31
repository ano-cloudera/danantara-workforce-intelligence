from pathlib import Path
from unittest.mock import MagicMock

from app.config import Settings
from app.models import Candidate
from app.services.data_gateway import DataGateway
from app.services.policy_fallback import PolicyFallback


ROOT = Path(__file__).resolve().parents[3]
STATIC = ROOT / "apps/frontend/app/static"


def test_frontend_contains_all_six_experience_pages():
    html = (STATIC / "index.html").read_text()

    for page in ("overview", "talent", "policy", "dashboard", "sources", "settings"):
        assert f'id="page-{page}"' in html


def test_frontend_uses_named_lucide_react_imports_without_raw_svg():
    html = (STATIC / "index.html").read_text()
    icons = (STATIC / "icons.js").read_text()

    assert "from \"https://esm.sh/lucide-react" in icons
    assert "import {" in icons
    assert "size: 20, strokeWidth: 1.75" in icons
    assert "size: 16, strokeWidth: 2" in icons
    assert "size: 24, strokeWidth: 1.5" in icons
    assert "<svg" not in html
    assert "<svg" not in icons


def test_frontend_and_demo_data_exclude_reference_only_values():
    visible_sources = "\n".join(
        (STATIC / name).read_text() for name in ("index.html", "app.js", "styles.css")
    ) + (ROOT / "data/workforce-app/demo/candidates.json").read_text()

    for forbidden in (
        "NHS",
        "Fahri Ananda",
        "Dewi Lestari",
        "Rizky Permana",
        "Siti Nurhaliza",
        "Bagas Prasetyo",
        "12,845",
    ):
        assert forbidden not in visible_sources


def test_demo_dashboard_summary_uses_real_fixture_counts():
    settings = Settings(_env_file=None, data_mode="demo")
    gateway = DataGateway(settings)

    summary = gateway.dashboard_summary()

    assert summary["total_candidates"] == 4
    assert summary["active_recruitment_requests"] == 6
    assert summary["active_openings"] == 8
    assert summary["entities"] == 2
    assert summary["policy_documents"] == 6


def _mock_impala_connection(rows: list[tuple]) -> MagicMock:
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    connection = MagicMock()
    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    return connection


def test_impala_dashboard_summary_uses_recruitment_pipeline_table(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    monkeypatch.setattr(gateway, "list_candidates", lambda: [])
    monkeypatch.setattr(gateway, "list_positions", lambda: [])
    monkeypatch.setattr(gateway, "list_documents", lambda policy_only=False: [])
    connection = _mock_impala_connection(
        [("APP-1", "CAND-1", "NSH", "REQ-1", "Screening", "Active", 91, "WITHIN_BAND")]
    )
    monkeypatch.setattr(gateway, "_connect", lambda: connection)

    summary = gateway.dashboard_summary()

    assert summary["recruitment_stages"] == [("Screening", 1)]
    assert summary["salary_compliance"] == [("WITHIN_BAND", 1)]
    assert summary["average_match_score"] == 91.0


def test_impala_dashboard_summary_falls_back_to_demo_when_table_unreachable(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    monkeypatch.setattr(gateway, "list_candidates", lambda: [])
    monkeypatch.setattr(gateway, "list_positions", lambda: [])
    monkeypatch.setattr(gateway, "list_documents", lambda policy_only=False: [])

    def broken_connect():
        raise RuntimeError("no route to host")

    monkeypatch.setattr(gateway, "_connect", broken_connect)

    summary = gateway.dashboard_summary()

    assert summary["recruitment_stages"]
    assert summary["average_match_score"] is not None


def test_impala_candidate_skill_proficiency_keeps_skills_with_null_score(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    connection = _mock_impala_connection(
        [("Apache Kafka", None), ("Python", 80)]
    )
    monkeypatch.setattr(gateway, "_connect", lambda: connection)

    proficiency = gateway._impala_candidate_skill_proficiency("CAND-1")

    assert proficiency == {"Apache Kafka": 0, "Python": 80}


def test_impala_candidates_include_profile_detail_columns(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    connection = _mock_impala_connection(
        [
            (
                "CAND-1",
                "Aditya Nugraha",
                "BNS",
                "Senior Data Engineer",
                7.0,
                "Jakarta",
                "S1",
                "Universitas Indonesia",
                "Python,SQL",
                "Data engineer",
            )
        ]
    )
    monkeypatch.setattr(gateway, "_connect", lambda: connection)

    candidates = gateway.list_candidates()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.current_title == "Senior Data Engineer"
    assert candidate.city == "Jakarta"
    assert candidate.education_level == "S1"
    assert candidate.education_institution == "Universitas Indonesia"
    assert candidate.skills == ["Python", "SQL"]


def test_get_candidate_enriches_impala_result_with_skills_and_experience(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    monkeypatch.setattr(
        gateway,
        "list_candidates",
        lambda: [Candidate(candidate_id="CAND-1", name="Aditya Nugraha", company="BNS")],
    )
    monkeypatch.setattr(
        gateway, "_impala_candidate_skill_proficiency", lambda candidate_id: {"Python": 90}
    )
    monkeypatch.setattr(
        gateway,
        "_impala_candidate_experiences",
        lambda candidate_id: [
            {
                "employer": "Bank Nusantara",
                "role_title": "Data Engineer",
                "start_date": "2020-01",
                "end_date": None,
                "is_current": True,
                "description": "Built streaming pipelines.",
            }
        ],
    )
    monkeypatch.setattr(gateway, "recruitment_pipeline", lambda: [])

    candidate = gateway.get_candidate("CAND-1")

    assert candidate.skill_proficiency == {"Python": 90}
    assert candidate.experiences[0]["employer"] == "Bank Nusantara"


def test_get_candidate_fills_application_fields_from_recruitment_pipeline(monkeypatch):
    settings = Settings(_env_file=None, data_mode="impala", impala_host="impala.example.com")
    gateway = DataGateway(settings)
    monkeypatch.setattr(
        gateway,
        "list_candidates",
        lambda: [Candidate(candidate_id="CAND-1", name="Aditya Nugraha", company="BNS")],
    )
    monkeypatch.setattr(gateway, "_impala_candidate_skill_proficiency", lambda candidate_id: {})
    monkeypatch.setattr(gateway, "_impala_candidate_experiences", lambda candidate_id: [])
    monkeypatch.setattr(
        gateway,
        "recruitment_pipeline",
        lambda: [
            {
                "application_id": "APP-1",
                "candidate_id": "CAND-1",
                "position_id": "REQ-BNS-003",
                "stage": "Final Interview",
                "status": "Active",
                "salary_compliance_demo": "WITHIN_BAND",
            }
        ],
    )

    candidate = gateway.get_candidate("CAND-1")

    assert candidate.application_id == "APP-1"
    assert candidate.position_id == "REQ-BNS-003"
    assert candidate.application_stage == "Final Interview"
    assert candidate.application_status == "Active"
    assert candidate.salary_compliance == "WITHIN_BAND"


def test_policy_fallback_uses_supplied_policy_documents():
    settings = Settings(_env_file=None)
    fallback = PolicyFallback(settings)

    sources = fallback.search("annual leave", ["BNS", "ENP"])

    assert {source.entity for source in sources} == {"BNS", "ENP"}
    assert all(source.document_id for source in sources)
    assert all(source.download_url for source in sources)


def test_policy_flow_has_provider_failure_fallback():
    source = (ROOT / "apps/backend/app/orchestration/policy_flow.py").read_text()

    assert "Gemini synthesis is temporarily unavailable" in source
    assert '"excerpts are returned for human review' in source


def test_frontend_has_responsive_global_search_and_policy_chat_controls():
    html = (STATIC / "index.html").read_text()
    javascript = (STATIC / "app.js").read_text()
    styles = (STATIC / "styles.css").read_text()

    for expected in (
        'id="mobile-search"',
        'id="global-search-results"',
        'id="policy-conversation"',
        'id="policy-form"',
        'id="policy-source-list"',
        'id="new-policy-chat"',
    ):
        assert expected in html
    assert 'api.post("policy/chat"' in javascript
    assert 'api.download("policy/export"' in javascript
    assert 'api.post("feedback"' in javascript
    assert 'class="match-activity-table"' in javascript
    assert "state.matchPosition = data.position" in javascript
    assert ".global-search-wrap.open" in styles
    assert ".policy-chat-layout" in styles
    assert ".match-activity-row" in styles


def test_frontend_uses_official_logo_and_professional_action_icons():
    html = (STATIC / "index.html").read_text()
    javascript = (STATIC / "app.js").read_text()
    styles = (STATIC / "styles.css").read_text()
    frontend_server = (ROOT / "apps/frontend/app/main.py").read_text()

    assert (ROOT / "assets/cloudera-logo.png").is_file()
    assert 'href="/assets/cloudera-logo.png"' in html
    assert html.count('src="/assets/cloudera-logo.png"') == 2
    assert 'app.mount("/assets"' in frontend_server
    assert "sparkles" not in html.lower()
    assert 'icon("sparkles")' not in javascript
    assert ".primary [data-icon] svg" in styles
    assert "stroke: #fff !important" in styles
