from __future__ import annotations

import re
from datetime import datetime, timezone

from .config import PolicyJobSettings
from .models import PolicyDocument, SourceObject

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _table(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe table identifier: {value!r}")
    return value


class PolicyImpalaRepository:
    def __init__(self, settings: PolicyJobSettings):
        self.settings = settings
        self.documents = _table(settings.policy_document_table)
        self.audit = _table(settings.policy_audit_table)

    def _connect(self):
        from impala.dbapi import connect

        kwargs = {
            "host": self.settings.impala_host,
            "port": self.settings.impala_port,
            "database": self.settings.impala_database,
            "auth_mechanism": self.settings.impala_auth_mechanism,
            "user": self.settings.impala_user,
            "password": self.settings.impala_password,
            "use_ssl": self.settings.impala_use_ssl,
        }
        if self.settings.impala_use_http_transport:
            kwargs["use_http_transport"] = True
            kwargs["http_path"] = self.settings.impala_http_path
        return connect(**kwargs)

    def execute_ddl(self, ddl: str) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            for statement in (part.strip() for part in ddl.split(";") if part.strip()):
                cursor.execute(statement)

    def is_finalized(self, item: SourceObject) -> bool:
        sql = (
            f"SELECT count(*) FROM {self.audit} WHERE s3_uri=%s AND s3_etag=%s "
            "AND pipeline_status IN ('COMPLETED','REVIEW_REQUIRED')"
        )
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, (item.uri, item.etag))
            return int(cursor.fetchone()[0]) > 0

    def replace_document(
        self,
        ingestion_id: str,
        source: SourceObject,
        document: PolicyDocument,
        *,
        extraction_status: str,
        guardrail_status: str,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"DELETE FROM {self.documents} WHERE document_id=%s", (document.document_id,)
            )
            cursor.execute(
                f"INSERT INTO {self.documents} "
                "(document_id,entity,title,document_type,document_version,file_name,"
                "source_s3_uri,source_etag,content_hash,page_count,chunk_count,ingestion_id,"
                "extraction_status,guardrail_status,created_at,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    document.document_id,
                    document.entity,
                    document.title,
                    document.document_type,
                    document.version,
                    document.file_name,
                    source.uri,
                    source.etag,
                    document.content_hash,
                    document.page_count,
                    len(document.chunks),
                    ingestion_id,
                    extraction_status,
                    guardrail_status,
                    now,
                    now,
                ),
            )

    def record_audit(
        self,
        ingestion_id: str,
        item: SourceObject,
        status: str,
        *,
        document_id: str | None = None,
        sha256: str | None = None,
        guardrail_reasons: tuple[str, ...] = (),
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"DELETE FROM {self.audit} WHERE s3_uri=%s AND s3_etag=%s",
                (item.uri, item.etag),
            )
            cursor.execute(
                f"INSERT INTO {self.audit} "
                "(ingestion_id,document_id,s3_uri,s3_etag,content_hash,file_name,"
                "file_size_bytes,pipeline_status,guardrail_reasons,extractor_version,"
                "received_at,processed_at,error_code,error_message) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    ingestion_id,
                    document_id,
                    item.uri,
                    item.etag,
                    sha256,
                    item.key.rsplit("/", 1)[-1],
                    item.size,
                    status,
                    ",".join(guardrail_reasons) or None,
                    "policy-extractor-v1",
                    now,
                    now if status in {"COMPLETED", "REVIEW_REQUIRED", "FAILED"} else None,
                    error_type,
                    (error_message or "")[:1000] or None,
                ),
            )
