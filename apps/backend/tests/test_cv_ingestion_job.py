import subprocess
from types import SimpleNamespace

from jobs.cv_ingestion.adapters import DataLakeS3AAdapter
from jobs.cv_ingestion.models import CandidateProfile, Experience, S3Object, Skill
from jobs.cv_ingestion.pipeline import CvIngestionPipeline


class FakeS3:
    def __init__(self, objects):
        self.objects = objects
        self.copied = []
        self.deleted = []

    def list_pdf_objects(self):
        return self.objects

    def read(self, item):
        return b"candidate cv"

    def copy_to(self, item, destination):
        copied = S3Object("bucket", f"processed/{item.key.rsplit('/', 1)[-1]}", item.etag)
        self.copied.append((item, destination))
        return copied

    def delete(self, item):
        self.deleted.append(item)


class FakeExtractor:
    def __init__(self, fail=False):
        self.fail = fail

    def extract(self, item, content):
        if self.fail:
            raise ValueError("invalid PDF")
        return CandidateProfile(
            candidate_id="CAND-001",
            full_name="Example Candidate",
            entity="BNS",
            current_title="Data Engineer",
            skills=[Skill("Python")],
            experiences=[Experience("Example Co", "Engineer")],
        )

    def embed(self, text):
        return [0.1, 0.2]


class FakeRepository:
    def __init__(self, completed=False):
        self.completed = completed
        self.audit = []
        self.candidates = []

    def is_completed(self, item):
        return self.completed

    def record_audit(self, ingestion_id, item, status, **kwargs):
        self.audit.append(status)

    def replace_candidate(self, ingestion_id, item, profile):
        self.candidates.append(profile.candidate_id)


class FakeQdrant:
    def __init__(self):
        self.candidates = []

    def upsert(self, profile, item, vector):
        self.candidates.append(profile.candidate_id)


class FakeObservability:
    def __init__(self):
        self.events = []

    def emit(self, name, metadata):
        self.events.append((name, metadata))


def settings():
    return SimpleNamespace(processed_uri="s3://bucket/processed/", failed_uri="s3://bucket/failed/")


def test_successful_ingestion_writes_all_destinations_and_archives_source():
    item = S3Object("bucket", "incoming/candidate.pdf", "etag-1", 12)
    s3 = FakeS3([item])
    repository = FakeRepository()
    qdrant = FakeQdrant()
    obs = FakeObservability()
    result = CvIngestionPipeline(
        settings(), s3, FakeExtractor(), repository, qdrant, obs
    ).run()

    assert result.processed == 1
    assert result.failed == 0
    assert repository.audit == ["PROCESSING", "COMPLETED"]
    assert repository.candidates == ["CAND-001"]
    assert qdrant.candidates == ["CAND-001"]
    assert s3.deleted == [item]
    assert obs.events[-1][0] == "cv-ingestion-batch-completed"


def test_completed_object_is_skipped_without_mutation():
    item = S3Object("bucket", "incoming/candidate.pdf", "etag-1")
    s3 = FakeS3([item])
    repository = FakeRepository(completed=True)
    qdrant = FakeQdrant()
    result = CvIngestionPipeline(
        settings(), s3, FakeExtractor(), repository, qdrant, FakeObservability()
    ).run()

    assert result.skipped == 1
    assert repository.audit == []
    assert qdrant.candidates == []
    assert s3.deleted == []


def test_failed_object_is_audited_and_isolated():
    item = S3Object("bucket", "incoming/broken.pdf", "etag-2")
    s3 = FakeS3([item])
    repository = FakeRepository()
    result = CvIngestionPipeline(
        settings(), s3, FakeExtractor(fail=True), repository, FakeQdrant(), FakeObservability()
    ).run()

    assert result.failed == 1
    assert repository.audit == ["PROCESSING", "FAILED"]
    assert s3.copied[-1][1] == settings().failed_uri
    assert s3.deleted == [item]


def test_qdrant_projection_excludes_direct_contact_details_and_name():
    profile = CandidateProfile(
        candidate_id="CAND-001",
        full_name="Sensitive Person",
        email="person@example.com",
        phone="+621234567",
        current_title="Data Engineer",
        professional_summary="Builds governed pipelines.",
        skills=[Skill("Python")],
    )

    text = profile.qdrant_text()
    assert "Sensitive Person" not in text
    assert "person@example.com" not in text
    assert "+621234567" not in text
    assert "Data Engineer" in text
    assert "Python" in text


def datalake_settings():
    return SimpleNamespace(
        hadoop_fs_command="hadoop fs",
        storage_command_timeout_seconds=120,
        input_uri="s3a://bucket/data/cv-collect/",
        max_objects=2,
        as_s3a_uri=lambda uri: uri.replace("s3://", "s3a://", 1),
        split_s3_uri=lambda uri: (
            uri.split("://", 1)[1].split("/", 1)[0],
            uri.split("://", 1)[1].split("/", 1)[1],
        ),
    )


def test_datalake_adapter_lists_and_reads_with_hadoop_s3a():
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if "-ls" in command:
            stdout = (
                b"-rw-r--r-- 1 user group 12 2026-08-27 10:00 "
                b"s3a://bucket/data/cv-collect/candidate.pdf\n"
                b"-rw-r--r-- 1 user group 4 2026-08-27 10:00 "
                b"s3a://bucket/data/cv-collect/ignore.txt\n"
            )
        else:
            stdout = b"candidate cv"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

    adapter = DataLakeS3AAdapter(datalake_settings(), runner=runner)
    objects = adapter.list_pdf_objects()

    assert len(objects) == 1
    assert objects[0].uri == "s3://bucket/data/cv-collect/candidate.pdf"
    assert adapter.read(objects[0]) == b"candidate cv"
    assert calls[0] == [
        "hadoop",
        "fs",
        "-ls",
        "-R",
        "s3a://bucket/data/cv-collect/",
    ]


def test_datalake_adapter_archives_and_deletes_with_hadoop_s3a():
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    adapter = DataLakeS3AAdapter(datalake_settings(), runner=runner)
    item = S3Object("bucket", "data/cv-collect/candidate.pdf", "fingerprint", 12)
    copied = adapter.copy_to(item, "s3a://bucket/data/cv-processed/")
    adapter.delete(item)

    assert copied.uri == "s3://bucket/data/cv-processed/candidate.pdf"
    assert calls == [
        ["hadoop", "fs", "-mkdir", "-p", "s3a://bucket/data/cv-processed"],
        [
            "hadoop",
            "fs",
            "-cp",
            "-f",
            "s3a://bucket/data/cv-collect/candidate.pdf",
            "s3a://bucket/data/cv-processed/candidate.pdf",
        ],
        [
            "hadoop",
            "fs",
            "-rm",
            "-f",
            "s3a://bucket/data/cv-collect/candidate.pdf",
        ],
    ]
