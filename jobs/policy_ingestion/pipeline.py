from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from .adapters import content_hash
from .models import DocumentValidationError, PolicyDocument, SourceObject

logger = logging.getLogger(__name__)


@dataclass
class PolicyJobResult:
    discovered: int = 0
    processed: int = 0
    review_required: int = 0
    skipped: int = 0
    failed: int = 0


class PolicyIngestionPipeline:
    """Run one bounded, retry-safe policy ingestion batch."""

    def __init__(
        self,
        settings,
        storage,
        extractor,
        guardrails,
        repository,
        embedder,
        qdrant,
        observability,
    ):
        self.settings = settings
        self.storage = storage
        self.extractor = extractor
        self.guardrails = guardrails
        self.repository = repository
        self.embedder = embedder
        self.qdrant = qdrant
        self.observability = observability

    @staticmethod
    def _attach_source(document: PolicyDocument, item: SourceObject) -> None:
        for chunk in document.chunks:
            chunk.source_s3_uri = item.uri
            chunk.source_etag = item.etag

    def run(self, *, dry_run: bool = False) -> PolicyJobResult:
        started = time.monotonic()
        result = PolicyJobResult()
        objects = self.storage.list_objects()
        result.discovered = len(objects)
        self.observability.emit(
            "policy-ingestion-batch-started",
            {"discovered": result.discovered, "dry_run": dry_run},
        )
        for item in objects:
            if self.repository.is_finalized(item):
                result.skipped += 1
                continue
            self._process(item, result, dry_run=dry_run)
        self.observability.emit(
            "policy-ingestion-batch-completed",
            {
                "discovered": result.discovered,
                "processed": result.processed,
                "review_required": result.review_required,
                "skipped": result.skipped,
                "failed": result.failed,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "dry_run": dry_run,
            },
        )
        return result

    def _process(self, item: SourceObject, result: PolicyJobResult, *, dry_run: bool) -> None:
        ingestion_id = str(uuid.uuid4())
        digest = None
        document = None
        try:
            source_decision = self.guardrails.validate_source(item)
            if not source_decision.allowed:
                raise DocumentValidationError(",".join(source_decision.reasons))
            if not dry_run:
                self.repository.record_audit(ingestion_id, item, "PROCESSING")
            content = self.storage.read(item)
            digest = content_hash(content)
            document = self.extractor.extract(item, content)
            document.content_hash = digest
            self.observability.emit(
                "policy-extraction-completed",
                {
                    "ingestion_id": ingestion_id,
                    "document_id": document.document_id,
                    "chunk_count": len(document.chunks),
                    "page_count": document.page_count,
                },
            )
            decision = self.guardrails.validate_document(document)
            if (
                decision.human_review_required
                and "prompt_injection_pattern" not in decision.reasons
                and set(decision.reasons)
                <= {"missing_entity", "missing_document_type"}
            ):
                try:
                    document = self.embedder.complete_metadata(document)
                    decision = self.guardrails.validate_document(document)
                except Exception as exc:
                    logger.warning(
                        "Policy metadata completion unavailable: error_type=%s",
                        type(exc).__name__,
                    )
            self.observability.emit(
                "policy-guardrail-completed",
                {
                    "ingestion_id": ingestion_id,
                    "document_id": document.document_id,
                    "allowed": decision.allowed,
                    "review_required": decision.human_review_required,
                    "reason_codes": list(decision.reasons),
                },
            )
            if dry_run:
                result.review_required += int(decision.human_review_required)
                result.processed += int(decision.allowed)
                self.observability.emit(
                    "policy-ingestion-dry-run",
                    {
                        "ingestion_id": ingestion_id,
                        "document_id": document.document_id,
                        "review_required": decision.human_review_required,
                        "chunk_count": len(document.chunks),
                    },
                )
                return
            if decision.human_review_required:
                review_item = self.storage.copy_to(item, self.settings.review_uri)
                self._attach_source(document, review_item)
                self.repository.replace_document(
                    ingestion_id,
                    review_item,
                    document,
                    extraction_status="EXTRACTED",
                    guardrail_status="REVIEW_REQUIRED",
                )
                self.repository.record_audit(
                    ingestion_id,
                    item,
                    "REVIEW_REQUIRED",
                    document_id=document.document_id,
                    sha256=digest,
                    guardrail_reasons=decision.reasons,
                )
                self.storage.delete(item)
                result.review_required += 1
                self.observability.emit(
                    "policy-ingestion-review-required",
                    {
                        "ingestion_id": ingestion_id,
                        "document_id": document.document_id,
                        "reason_codes": list(decision.reasons),
                    },
                )
                return

            vectors = self.embedder.embed([chunk.text for chunk in document.chunks])
            processed_item = self.storage.copy_to(item, self.settings.processed_uri)
            self._attach_source(document, processed_item)
            post_decision = self.guardrails.validate_vectors(document, vectors)
            if not post_decision.allowed:
                raise RuntimeError(",".join(post_decision.reasons))
            self.repository.replace_document(
                ingestion_id,
                processed_item,
                document,
                extraction_status="COMPLETED",
                guardrail_status="PASSED",
            )
            indexed = self.qdrant.replace(document, vectors)
            if indexed != len(document.chunks):
                raise RuntimeError("qdrant_write_count_mismatch")
            self.repository.record_audit(
                ingestion_id,
                item,
                "COMPLETED",
                document_id=document.document_id,
                sha256=digest,
            )
            self.storage.delete(item)
            result.processed += 1
            self.observability.emit(
                "policy-ingestion-completed",
                {
                    "ingestion_id": ingestion_id,
                    "document_id": document.document_id,
                    "chunk_count": indexed,
                    "guardrail_status": "PASSED",
                },
            )
        except DocumentValidationError as exc:
            result.failed += 1
            self._record_failure(
                ingestion_id,
                item,
                document,
                digest,
                exc,
                archive_invalid=not dry_run,
            )
        except Exception as exc:
            # Keep the landing object in place. Impala and Qdrant operations are replace-based,
            # so the next scheduled run can safely reconcile a partial external write.
            result.failed += 1
            logger.exception("Retryable policy ingestion failure for %s", item.uri)
            if not dry_run:
                try:
                    self.repository.record_audit(
                        ingestion_id,
                        item,
                        "FAILED",
                        document_id=document.document_id if document else None,
                        sha256=digest,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                except Exception as audit_exc:
                    logger.error(
                        "Could not record policy ingestion failure: error_type=%s",
                        type(audit_exc).__name__,
                    )
            self.observability.emit(
                "policy-ingestion-failed",
                {
                    "ingestion_id": ingestion_id,
                    "document_id": document.document_id if document else None,
                    "error_type": type(exc).__name__,
                    "retryable": True,
                },
            )

    def _record_failure(
        self,
        ingestion_id,
        item,
        document,
        digest,
        exc,
        *,
        archive_invalid: bool,
    ) -> None:
        logger.warning(
            "Rejected policy document %s: error_type=%s", item.uri, type(exc).__name__
        )
        if archive_invalid:
            try:
                self.repository.record_audit(
                    ingestion_id,
                    item,
                    "FAILED",
                    document_id=document.document_id if document else None,
                    sha256=digest,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                self.storage.copy_to(item, self.settings.failed_uri)
                self.storage.delete(item)
            except Exception as archive_exc:
                logger.error(
                    "Could not archive rejected policy document: error_type=%s",
                    type(archive_exc).__name__,
                )
        self.observability.emit(
            "policy-ingestion-failed",
            {
                "ingestion_id": ingestion_id,
                "document_id": document.document_id if document else None,
                "error_type": type(exc).__name__,
                "retryable": False,
            },
        )
