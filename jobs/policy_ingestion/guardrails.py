from __future__ import annotations

import re

from .models import GuardrailDecision, PolicyDocument, SourceObject


class PolicyIngestionGuardrails:
    SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx"}
    INJECTION_PATTERNS = (
        r"ignore (all|any|the) previous instructions",
        r"reveal (the )?(system|developer) prompt",
        r"bypass (security|policy|guardrail)",
    )

    def __init__(self, max_file_bytes: int, max_chunks: int, embedding_dimension: int):
        self.max_file_bytes = max_file_bytes
        self.max_chunks = max_chunks
        self.embedding_dimension = embedding_dimension

    def validate_source(self, item: SourceObject) -> GuardrailDecision:
        reasons = []
        suffix = "." + item.key.rsplit(".", 1)[-1].lower() if "." in item.key else ""
        if suffix not in self.SUPPORTED_SUFFIXES:
            reasons.append("unsupported_file_type")
        if item.size <= 0:
            reasons.append("empty_file")
        if item.size > self.max_file_bytes:
            reasons.append("file_too_large")
        return GuardrailDecision(allowed=not reasons, reasons=tuple(reasons))

    def validate_document(self, document: PolicyDocument) -> GuardrailDecision:
        reasons = []
        if not document.document_id or not document.title:
            reasons.append("missing_document_identity")
        if not document.entity:
            reasons.append("missing_entity")
        if not document.document_type:
            reasons.append("missing_document_type")
        if not document.chunks:
            reasons.append("empty_extracted_text")
        if len(document.chunks) > self.max_chunks:
            reasons.append("chunk_limit_exceeded")
        searchable = "\n".join(chunk.text for chunk in document.chunks).lower()
        if any(re.search(pattern, searchable) for pattern in self.INJECTION_PATTERNS):
            reasons.append("prompt_injection_pattern")
        return GuardrailDecision(
            allowed=not reasons,
            reasons=tuple(reasons),
            human_review_required=bool(reasons),
        )

    def validate_vectors(
        self, document: PolicyDocument, vectors: list[list[float]]
    ) -> GuardrailDecision:
        reasons = []
        if len(vectors) != len(document.chunks):
            reasons.append("embedding_count_mismatch")
        if any(len(vector) != self.embedding_dimension for vector in vectors):
            reasons.append("embedding_dimension_mismatch")
        for chunk in document.chunks:
            if not all(
                (
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.title,
                    chunk.document_type,
                    chunk.text,
                    chunk.source_s3_uri,
                    chunk.source_etag,
                )
            ):
                reasons.append("incomplete_citation_metadata")
                break
        return GuardrailDecision(allowed=not reasons, reasons=tuple(reasons))
