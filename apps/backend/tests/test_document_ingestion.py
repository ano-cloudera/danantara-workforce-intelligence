from unittest.mock import MagicMock

from app.config import Settings
from app.services.document_ingestion import DocumentIngestionService


def _service(tmp_path, **overrides):
    settings = Settings(
        _env_file=None,
        upload_dir=str(tmp_path / "uploads"),
        sqlite_path=str(tmp_path / "state.db"),
        **overrides,
    )
    store = MagicMock()
    store.add_upload.return_value = "upload-1"
    service = DocumentIngestionService(settings, qdrant=None, store=store)
    return service, store


def test_local_mode_still_writes_to_upload_dir(tmp_path):
    service, store = _service(tmp_path, upload_access_mode="local")

    result = service.save_and_process("resume.pdf", b"%PDF-1.4 fake", entity="BNS", doc_type="Candidate CV")

    assert result["status"] == "processed_backend_fallback"
    assert (tmp_path / "uploads" / "resume.pdf").exists()
    store.add_upload.assert_called_once()


def test_datalake_mode_routes_cv_document_type_to_cv_landing(tmp_path, monkeypatch):
    service, store = _service(
        tmp_path,
        upload_access_mode="datalake",
        s3_cv_landing_uri="s3a://bucket/data/cv-collect/",
        s3_policy_landing_uri="s3a://bucket/data/policy-collect/",
    )
    calls = []
    monkeypatch.setattr(service, "_run_hadoop_fs", lambda *args: calls.append(args))

    result = service.save_and_process("resume.pdf", b"%PDF-1.4 fake", entity="BNS", doc_type="Candidate CV")

    assert result["status"] == "landed_datalake"
    assert result["routing"] == "awaiting_cv_ingestion_job"
    assert result["path"] == "s3a://bucket/data/cv-collect/resume.pdf"
    put_call = next(c for c in calls if c[0] == "-put")
    assert put_call[-1] == "s3a://bucket/data/cv-collect/resume.pdf"
    store.add_upload.assert_called_once()
    assert store.add_upload.call_args[0][2] == "landed_datalake"


def test_datalake_mode_routes_policy_document_type_to_policy_landing(tmp_path, monkeypatch):
    service, store = _service(
        tmp_path,
        upload_access_mode="datalake",
        s3_cv_landing_uri="s3a://bucket/data/cv-collect/",
        s3_policy_landing_uri="s3a://bucket/data/policy-collect/",
    )
    monkeypatch.setattr(service, "_run_hadoop_fs", lambda *args: None)

    result = service.save_and_process("group_policy.pdf", b"%PDF-1.4 fake", entity="BNS", doc_type="Group HR Policy")

    assert result["routing"] == "awaiting_policy_ingestion_job"
    assert result["path"] == "s3a://bucket/data/policy-collect/group_policy.pdf"


def test_datalake_mode_raises_when_landing_uri_missing(tmp_path):
    service, _ = _service(tmp_path, upload_access_mode="datalake")

    try:
        service.save_and_process("resume.pdf", b"data", entity="BNS", doc_type="Candidate CV")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "S3_CV_LANDING_URI" in str(exc)


def test_datalake_mode_sanitizes_unsafe_filenames(tmp_path, monkeypatch):
    service, _ = _service(
        tmp_path,
        upload_access_mode="datalake",
        s3_cv_landing_uri="s3a://bucket/data/cv-collect/",
        s3_policy_landing_uri="s3a://bucket/data/policy-collect/",
    )
    monkeypatch.setattr(service, "_run_hadoop_fs", lambda *args: None)

    result = service.save_and_process("../../evil name!.pdf", b"data", entity="BNS", doc_type="Candidate CV")

    assert result["path"] == "s3a://bucket/data/cv-collect/evil_name_.pdf"
