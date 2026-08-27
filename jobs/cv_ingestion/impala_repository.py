from __future__ import annotations

import re
from datetime import datetime, timezone

from .config import JobSettings
from .models import CandidateProfile, S3Object

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _table(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe table identifier: {value!r}")
    return value


class ImpalaRepository:
    def __init__(self, settings: JobSettings):
        self.settings = settings
        self.master = _table(settings.candidate_master_table)
        self.skills = _table(settings.candidate_skills_table)
        self.experience = _table(settings.candidate_experience_table)
        self.audit = _table(settings.ingestion_audit_table)

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

    def is_completed(self, item: S3Object) -> bool:
        sql = (
            f"SELECT count(*) FROM {self.audit} "
            "WHERE s3_uri=%s AND s3_etag=%s AND pipeline_status='COMPLETED'"
        )
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, (item.uri, item.etag))
            return int(cursor.fetchone()[0]) > 0

    def record_audit(
        self,
        ingestion_id: str,
        item: S3Object,
        status: str,
        *,
        candidate_id: str | None = None,
        sha256: str | None = None,
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
                "(ingestion_id,candidate_id,s3_uri,s3_etag,content_hash,file_name,"
                "file_size_bytes,pipeline_status,extractor_version,received_at,processed_at,"
                "error_code,error_message) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    ingestion_id,
                    candidate_id,
                    item.uri,
                    item.etag,
                    sha256,
                    item.key.rsplit("/", 1)[-1],
                    item.size,
                    status,
                    "gemini-v1",
                    now,
                    now if status in {"COMPLETED", "FAILED"} else None,
                    error_type,
                    (error_message or "")[:1000] or None,
                ),
            )

    def replace_candidate(
        self,
        ingestion_id: str,
        item: S3Object,
        profile: CandidateProfile,
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"DELETE FROM {self.master} WHERE candidate_id=%s", (profile.candidate_id,)
            )
            cursor.execute(
                f"INSERT INTO {self.master} "
                "(candidate_id,entity,full_name,current_title,years_experience,city,"
                "education_level,education_institution,professional_summary,email,phone,"
                "source_cv_s3_uri,source_etag,ingestion_id,extraction_status,"
                "extraction_confidence,created_at,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    profile.candidate_id,
                    profile.entity,
                    profile.full_name,
                    profile.current_title,
                    profile.years_experience,
                    profile.city,
                    profile.education_level,
                    profile.education_institution,
                    profile.professional_summary,
                    profile.email,
                    profile.phone,
                    item.uri,
                    item.etag,
                    ingestion_id,
                    "COMPLETED",
                    profile.extraction_confidence,
                    now,
                    now,
                ),
            )
            cursor.execute(
                f"DELETE FROM {self.skills} WHERE candidate_id=%s", (profile.candidate_id,)
            )
            for skill in profile.skills:
                cursor.execute(
                    f"INSERT INTO {self.skills} "
                    "(candidate_id,skill_name,normalized_skill_name,proficiency_score,"
                    "years_experience,evidence_text,confidence_score,ingestion_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        profile.candidate_id,
                        skill.name,
                        skill.name.strip().lower(),
                        skill.proficiency,
                        skill.years_experience,
                        skill.evidence,
                        profile.extraction_confidence,
                        ingestion_id,
                    ),
                )
            cursor.execute(
                f"DELETE FROM {self.experience} WHERE candidate_id=%s", (profile.candidate_id,)
            )
            for sequence, experience in enumerate(profile.experiences, start=1):
                cursor.execute(
                    f"INSERT INTO {self.experience} "
                    "(candidate_id,experience_sequence,employer,role_title,start_date,end_date,"
                    "is_current,description,ingestion_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        profile.candidate_id,
                        sequence,
                        experience.employer,
                        experience.role,
                        experience.start_date,
                        experience.end_date,
                        experience.is_current,
                        experience.summary,
                        ingestion_id,
                    ),
                )
