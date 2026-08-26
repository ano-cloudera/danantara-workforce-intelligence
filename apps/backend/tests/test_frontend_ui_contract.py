from pathlib import Path

from app.config import Settings
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

    assert (ROOT / "assets/logo.webp").is_file()
    assert 'href="/assets/logo.webp"' in html
    assert html.count('src="/assets/logo.webp"') == 2
    assert 'app.mount("/assets"' in frontend_server
    assert "sparkles" not in html.lower()
    assert 'icon("sparkles")' not in javascript
    assert ".primary [data-icon] svg" in styles
    assert "stroke: #fff !important" in styles
