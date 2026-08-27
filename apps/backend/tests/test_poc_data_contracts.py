from pathlib import Path

from pypdf import PdfReader

from app.config import Settings
from app.services.data_gateway import DataGateway
from app.services.gemini_service import GeminiService
from app.services.pdf_export import build_policy_pdf
from app.services.policy_documents import load_policy_chunks
from app.services.session_store import SessionStore


def test_supplied_sample_fixture_is_normalized_without_sensitive_candidate_fields():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    candidates = gateway.list_candidates()
    positions = gateway.list_positions()

    assert len(candidates) == 4
    assert len(positions) == 8
    assert candidates[0].current_title
    assert candidates[0].experiences
    assert candidates[0].skill_proficiency
    public_fields = set().union(*(candidate.model_dump().keys() for candidate in candidates))
    for forbidden in ("national_id", "nik", "date_of_birth", "marital_status", "email", "phone"):
        assert forbidden not in public_fields


def test_global_search_groups_real_sample_results():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))

    kafka = gateway.search("Kafka")
    leave = gateway.search("annual leave")

    assert kafka["groups"]["candidates"]
    assert kafka["groups"]["positions"]
    assert kafka["groups"]["skills"]
    assert leave["groups"]["policies"]


def test_document_download_is_restricted_to_allowlisted_sample_metadata():
    gateway = DataGateway(Settings(_env_file=None, data_mode="demo"))
    document = gateway.list_documents(policy_only=True)[0]

    path = gateway.document_path(document["document_id"])

    assert path.is_file()
    assert (gateway.settings.project_root / "sample" / "data").resolve() in path.parents


def test_policy_chunks_have_stable_document_and_chunk_metadata():
    chunks = load_policy_chunks(Settings(_env_file=None))

    assert chunks
    assert {chunk["entity"] for chunk in chunks if chunk["entity"]} >= {"BNS", "ENP", "NSH"}
    assert all(chunk["chunk_id"] and chunk["document_id"] and chunk["document_type"] for chunk in chunks)


def test_policy_messages_persist_and_export_as_readable_pdf(tmp_path: Path):
    settings = Settings(_env_file=None, sqlite_path=str(tmp_path / "state.db"))
    store = SessionStore(settings)
    session_id = store.ensure_session(None, "reviewer@example.test")
    request_id = "request-123"
    store.add_policy_message(session_id, "user", "Compare annual leave", request_id=request_id)
    store.add_policy_message(
        session_id,
        "assistant",
        "BNS provides 16 days [1].",
        request_id=request_id,
        sources=[{"title": "BNS PKB", "entity": "BNS", "page": 1}],
    )

    answer = store.get_policy_answer(request_id)
    messages = store.list_policy_messages(answer["session_id"])
    pdf = build_policy_pdf("Policy conversation", messages)
    pdf_path = tmp_path / "policy.pdf"
    pdf_path.write_bytes(pdf)

    assert len(store.list_policy_messages(session_id)) == 2
    assert pdf.startswith(b"%PDF-1.4")
    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1
    full_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Compare annual leave" in full_text
    assert "BNS provides 16 days" in full_text


def test_missing_gemini_credentials_degrade_without_startup_failure():
    service = GeminiService(Settings(_env_file=None, gemini_api_key=None))

    assert service.health()["configured"] is False
    try:
        service.generate_text("hello")
    except RuntimeError as exc:
        assert str(exc) == "Gemini is not configured"
    else:  # pragma: no cover
        raise AssertionError("Unconfigured Gemini call should fail fast")
