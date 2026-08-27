from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceObject:
    bucket: str
    key: str
    etag: str
    size: int = 0

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


@dataclass
class PolicyChunk:
    chunk_id: str
    document_id: str
    entity: str
    title: str
    document_type: str
    page: int | None
    section: str | None
    text: str
    source_s3_uri: str = ""
    source_etag: str = ""

    def payload(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "entity": self.entity,
            "title": self.title,
            "document_type": self.document_type,
            "page": self.page,
            "section": self.section,
            "text": self.text,
            "source_s3_uri": self.source_s3_uri,
            "source_etag": self.source_etag,
        }


@dataclass
class PolicyDocument:
    document_id: str
    entity: str | None
    title: str
    document_type: str | None
    version: str | None
    file_name: str
    page_count: int
    chunks: list[PolicyChunk] = field(default_factory=list)
    content_hash: str | None = None


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    reasons: tuple[str, ...] = ()
    human_review_required: bool = False


class DocumentValidationError(ValueError):
    """The source cannot be processed safely and should be isolated."""
