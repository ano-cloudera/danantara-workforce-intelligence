from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass

from .adapters import content_hash

logger = logging.getLogger(__name__)

_CANDIDATE_ENTITY_PATTERN = re.compile(r"^CAND-([A-Z0-9]+)-\d+$", re.IGNORECASE)


def normalize_candidate_identity(profile, source_key: str) -> None:
    """Fill stable candidate identity fields before writing any downstream sink."""
    profile.candidate_id = profile.candidate_id.strip()
    if profile.entity and profile.entity.strip():
        profile.entity = profile.entity.strip().upper()
        return

    source_candidate_id = source_key.rsplit("/", 1)[-1].split("_", 1)[0]
    for candidate_id in (profile.candidate_id, source_candidate_id):
        match = _CANDIDATE_ENTITY_PATTERN.fullmatch(candidate_id.strip())
        if match:
            profile.entity = match.group(1).upper()
            return


@dataclass
class JobResult:
    discovered: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0


class CvIngestionPipeline:
    """Orchestrate one bounded batch; scheduling is owned by Cloudera AI."""

    def __init__(self, settings, s3, extractor, repository, qdrant, observability):
        self.settings = settings
        self.s3 = s3
        self.extractor = extractor
        self.repository = repository
        self.qdrant = qdrant
        self.observability = observability

    def run(self, *, dry_run: bool = False) -> JobResult:
        started = time.monotonic()
        result = JobResult()
        objects = self.s3.list_pdf_objects()
        result.discovered = len(objects)
        self.observability.emit(
            "cv-ingestion-batch-started",
            {"discovered": result.discovered, "dry_run": dry_run},
        )
        for item in objects:
            if self.repository.is_completed(item):
                result.skipped += 1
                continue
            ingestion_id = str(uuid.uuid4())
            digest = None
            candidate_id = None
            try:
                if not dry_run:
                    self.repository.record_audit(ingestion_id, item, "PROCESSING")
                content = self.s3.read(item)
                digest = content_hash(content)
                profile = self.extractor.extract(item, content)
                normalize_candidate_identity(profile, item.key)
                candidate_id = profile.candidate_id
                if dry_run:
                    result.processed += 1
                    self.observability.emit(
                        "cv-ingestion-dry-run",
                        {
                            "ingestion_id": ingestion_id,
                            "candidate_id": candidate_id,
                            "entity": profile.entity,
                            "skill_count": len(profile.skills),
                            "experience_count": len(profile.experiences),
                        },
                    )
                    continue

                processed_item = self.s3.copy_to(item, self.settings.processed_uri)
                self.repository.replace_candidate(
                    ingestion_id, processed_item, profile
                )
                vector = self.extractor.embed(profile.qdrant_text())
                self.qdrant.upsert(profile, processed_item, vector)
                self.repository.record_audit(
                    ingestion_id,
                    item,
                    "COMPLETED",
                    candidate_id=candidate_id,
                    sha256=digest,
                )
                self.s3.delete(item)
                result.processed += 1
                self.observability.emit(
                    "cv-ingestion-completed",
                    {
                        "ingestion_id": ingestion_id,
                        "candidate_id": candidate_id,
                        "entity": profile.entity,
                        "skill_count": len(profile.skills),
                        "experience_count": len(profile.experiences),
                    },
                )
            except Exception as exc:
                result.failed += 1
                logger.exception("CV ingestion failed for %s", item.uri)
                if not dry_run:
                    try:
                        self.repository.record_audit(
                            ingestion_id,
                            item,
                            "FAILED",
                            candidate_id=candidate_id,
                            sha256=digest,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    except Exception as audit_exc:
                        logger.error(
                            "Could not record ingestion failure: error_type=%s",
                            type(audit_exc).__name__,
                        )
                    try:
                        self.s3.copy_to(item, self.settings.failed_uri)
                        self.s3.delete(item)
                    except Exception as archive_exc:
                        logger.error(
                            "Could not archive failed object: error_type=%s",
                            type(archive_exc).__name__,
                        )
                self.observability.emit(
                    "cv-ingestion-failed",
                    {
                        "ingestion_id": ingestion_id,
                        "candidate_id": candidate_id,
                        "error_type": type(exc).__name__,
                    },
                )
        self.observability.emit(
            "cv-ingestion-batch-completed",
            {
                "discovered": result.discovered,
                "processed": result.processed,
                "skipped": result.skipped,
                "failed": result.failed,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "dry_run": dry_run,
            },
        )
        return result
