import json
import logging
import re
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from app.config import Settings
from app.models import Candidate, Position

logger = logging.getLogger(__name__)
_TABLE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


class DataGateway:
    def __init__(self, settings: Settings, observability=None):
        self.settings = settings
        self.observability = observability
        self.demo_root = settings.project_root / "data" / "workforce-app" / "demo"

    def _demo_json(self, name: str, default=None):
        path = self.demo_root / name
        if not path.exists():
            return [] if default is None else default
        return json.loads(path.read_text(encoding="utf-8"))

    def list_candidates(self, company: str | None = None) -> list[Candidate]:
        if self.settings.data_mode == "impala":
            return self._impala_candidates(company)
        rows = self._demo_json("candidates.json")
        items = [Candidate(**r) for r in rows]
        if company:
            items = [c for c in items if (c.company or "").lower() == company.lower()]
        return items

    def list_positions(self) -> list[Position]:
        if self.settings.data_mode == "impala":
            return self._impala_positions()
        rows = self._demo_json("positions.json")
        return [Position(**r) for r in rows]

    def get_candidate(self, candidate_id: str) -> Candidate:
        for candidate in self.list_candidates():
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError("Candidate not found")

    def list_documents(self, policy_only: bool = False) -> list[dict]:
        if self.settings.data_mode == "impala":
            try:
                documents = self._impala_documents()
            except Exception as exc:
                logger.warning(
                    "Impala policy metadata unavailable; using demo metadata: error_type=%s",
                    type(exc).__name__,
                )
                documents = self._demo_json("documents.json")
        else:
            documents = self._demo_json("documents.json")
        if policy_only:
            allowed = {"PKB", "Group Policy", "Salary Policy"}
            documents = [item for item in documents if item.get("document_type") in allowed]
        return documents

    def get_document(self, document_id: str) -> dict:
        for document in self.list_documents():
            if document.get("document_id") == document_id:
                return document
        raise ValueError("Document not found")

    def document_path(self, document_id: str):
        document = self.get_document(document_id)
        path = (self.settings.project_root / document["relative_path"]).resolve()
        sample_root = (self.settings.project_root / "sample" / "data").resolve()
        if sample_root not in path.parents or not path.is_file():
            raise ValueError("Document file is unavailable")
        return path

    def read_document(self, document_id: str) -> tuple[str, bytes]:
        document = self.get_document(document_id)
        if document.get("relative_path"):
            path = self.document_path(document_id)
            return path.name, path.read_bytes()
        source_uri = document.get("source_s3_uri")
        if not source_uri or self.settings.policy_source_access_mode != "datalake":
            raise ValueError("Document source is unavailable")
        parsed = urlsplit(source_uri)
        if parsed.scheme not in {"s3", "s3a"} or not parsed.netloc:
            raise ValueError("Document source URI is invalid")
        governed_uri = f"s3a://{parsed.netloc}/{parsed.path.lstrip('/')}"
        try:
            completed = subprocess.run(
                [*shlex.split(self.settings.hadoop_fs_command), "-cat", governed_uri],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.settings.source_command_timeout_seconds,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning(
                "Governed document read failed: document_id=%s error_type=%s",
                document_id,
                type(exc).__name__,
            )
            raise ValueError("Document file is unavailable") from exc
        return Path(document.get("file_name") or parsed.path).name, completed.stdout

    def search(self, query: str, types: set[str] | None = None, limit: int = 5) -> dict:
        needle = query.strip().lower()
        selected = types or {"candidate", "position", "skill", "policy"}
        groups: dict[str, list[dict]] = {
            "candidates": [],
            "positions": [],
            "skills": [],
            "policies": [],
        }

        if "candidate" in selected:
            for candidate in self.list_candidates():
                haystack = " ".join(
                    [candidate.name, candidate.company or "", candidate.current_title or ""]
                    + candidate.skills
                ).lower()
                if needle in haystack:
                    groups["candidates"].append(
                        {
                            "id": candidate.candidate_id,
                            "title": candidate.name,
                            "subtitle": " · ".join(
                                value
                                for value in (candidate.current_title, candidate.company)
                                if value
                            ),
                            "type": "candidate",
                            "page": "talent",
                        }
                    )

        if "position" in selected:
            for position in self.list_positions():
                haystack = " ".join(
                    [position.title, position.entity or "", position.department or ""]
                    + position.required_skills
                ).lower()
                if needle in haystack:
                    groups["positions"].append(
                        {
                            "id": position.position_id,
                            "title": position.title,
                            "subtitle": " · ".join(
                                value for value in (position.entity, position.grade) if value
                            ),
                            "type": "position",
                            "page": "talent",
                        }
                    )

        if "skill" in selected:
            counts: dict[str, int] = {}
            for candidate in self.list_candidates():
                for skill in candidate.skills:
                    if needle in skill.lower():
                        counts[skill] = counts.get(skill, 0) + 1
            groups["skills"] = [
                {
                    "id": skill,
                    "title": skill,
                    "subtitle": f"{count} candidate profile(s)",
                    "type": "skill",
                    "page": "talent",
                }
                for skill, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]

        if "policy" in selected:
            matched_document_names = {
                row.get("source_document")
                for row in self._demo_json("policy_rules.json")
                if needle
                in " ".join(
                    [
                        row.get("entity", ""),
                        row.get("grade", ""),
                        row.get("rule_type", "").replace("_", " "),
                        row.get("source_document", ""),
                    ]
                ).lower()
            }
            for document in self.list_documents(policy_only=True):
                haystack = " ".join(
                    [
                        document.get("title", ""),
                        document.get("entity") or "",
                        document.get("document_type", ""),
                    ]
                ).lower()
                if needle in haystack or document.get("file_name") in matched_document_names:
                    groups["policies"].append(
                        {
                            "id": document["document_id"],
                            "title": document["title"],
                            "subtitle": " · ".join(
                                value
                                for value in (
                                    document.get("entity"),
                                    document.get("document_type"),
                                )
                                if value
                            ),
                            "type": "policy",
                            "page": "policy",
                        }
                    )

        return {
            "query": query,
            "groups": {name: values[:limit] for name, values in groups.items()},
            "total": sum(min(len(values), limit) for values in groups.values()),
        }

    def get_position(self, position_id: str | None = None, title: str | None = None) -> Position:
        positions = self.list_positions()
        for p in positions:
            if position_id and p.position_id == position_id:
                return p
            if title and p.title.lower() == title.lower():
                return p
        if title:
            return Position(
                position_id="CUSTOM", title=title, required_skills=[], preferred_skills=[]
            )
        raise ValueError("Position not found")

    def _connect(self):
        from impala.dbapi import connect

        if not self.settings.impala_host:
            raise RuntimeError("IMPALA_HOST is required when DATA_MODE=impala")
        kwargs = {
            "host": self.settings.impala_host,
            "port": self.settings.impala_port,
            "database": self.settings.impala_database,
            "auth_mechanism": self.settings.impala_auth_mechanism,
            "user": self.settings.impala_user,
            "password": self.settings.impala_password,
            "use_ssl": self.settings.impala_use_ssl,
        }
        if self.settings.impala_transport_mode == "http":
            kwargs["use_http_transport"] = True
            kwargs["http_path"] = self.settings.impala_http_path
        return connect(**kwargs)

    def _impala_candidates(self, company: str | None) -> list[Candidate]:
        sql = f"SELECT candidate_id,name,company,years_experience,skills,summary FROM {self.settings.impala_candidate_table}"
        params: tuple = ()
        if company:
            sql += " WHERE lower(company)=lower(%s)"
            params = (company,)
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
        result = []
        for candidate_id, name, company, years, skills, summary in rows:
            parsed_skills = (
                skills
                if isinstance(skills, list)
                else [x.strip() for x in str(skills or "").split(",") if x.strip()]
            )
            result.append(
                Candidate(
                    candidate_id=str(candidate_id),
                    name=name,
                    company=company,
                    years_experience=float(years or 0),
                    skills=parsed_skills,
                    summary=summary or "",
                )
            )
        return result

    def _impala_positions(self) -> list[Position]:
        sql = f"SELECT position_id,title,required_skills,preferred_skills,min_years_experience FROM {self.settings.impala_position_table}"
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()

        def parse_skills(value):
            if isinstance(value, list):
                return value
            return [x.strip() for x in str(value or "").split(",") if x.strip()]

        out = []
        for pid, title, req, pref, years in rows:
            out.append(
                Position(
                    position_id=str(pid),
                    title=title,
                    required_skills=parse_skills(req),
                    preferred_skills=parse_skills(pref),
                    min_years_experience=float(years or 0),
                )
            )
        return out

    def _impala_documents(self) -> list[dict]:
        table = self.settings.impala_policy_document_table
        if not _TABLE_IDENTIFIER.fullmatch(table):
            raise ValueError("Unsafe policy document table identifier")
        sql = (
            "SELECT document_id,title,entity,document_type,version,file_name,source_s3_uri,"
            f"extraction_status,guardrail_status,page_count,chunk_count,updated_at FROM {table}"
        )
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        return [
            {
                "document_id": str(document_id),
                "title": title,
                "entity": entity,
                "document_type": document_type,
                "version": version,
                "file_name": file_name,
                "source_s3_uri": source_s3_uri,
                "extraction_status": extraction_status,
                "guardrail_status": guardrail_status,
                "page_count": int(page_count or 0),
                "chunk_count": int(chunk_count or 0),
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            }
            for (
                document_id,
                title,
                entity,
                document_type,
                version,
                file_name,
                source_s3_uri,
                extraction_status,
                guardrail_status,
                page_count,
                chunk_count,
                updated_at,
            ) in rows
        ]

    def _impala_recruitment_pipeline(self) -> list[dict]:
        table = self.settings.impala_recruitment_table
        if not _TABLE_IDENTIFIER.fullmatch(table):
            raise ValueError("Unsafe recruitment pipeline table identifier")
        sql = (
            "SELECT application_id,candidate_id,entity,position_id,stage,status,"
            f"match_score,salary_compliance FROM {table}"
        )
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        return [
            {
                "application_id": str(application_id),
                "candidate_id": candidate_id,
                "entity": entity,
                "position_id": position_id,
                "stage": stage,
                "status": status,
                "match_score_demo": str(match_score) if match_score is not None else None,
                "salary_compliance_demo": salary_compliance,
            }
            for (
                application_id,
                candidate_id,
                entity,
                position_id,
                stage,
                status,
                match_score,
                salary_compliance,
            ) in rows
        ]

    def _recruitment_pipeline(self) -> list[dict]:
        if self.settings.data_mode == "impala":
            try:
                rows = self._impala_recruitment_pipeline()
                if rows:
                    return rows
            except Exception as exc:
                logger.warning(
                    "Impala recruitment pipeline unavailable; using demo metadata: error_type=%s",
                    type(exc).__name__,
                )
        return self._demo_json("recruitment_status.json")

    def dashboard_summary(self) -> dict:
        candidates = self.list_candidates()
        positions = self.list_positions()
        applications = self._recruitment_pipeline()
        by_company: dict[str, int] = {}
        skills: dict[str, int] = {}
        for c in candidates:
            by_company[c.company or "Unknown"] = by_company.get(c.company or "Unknown", 0) + 1
            for s in c.skills:
                skills[s] = skills.get(s, 0) + 1
        stage_distribution: dict[str, int] = {}
        salary_compliance: dict[str, int] = {}
        scores = []
        for application in applications:
            stage = application.get("stage") or "Unknown"
            compliance = application.get("salary_compliance_demo") or "UNKNOWN"
            stage_distribution[stage] = stage_distribution.get(stage, 0) + 1
            salary_compliance[compliance] = salary_compliance.get(compliance, 0) + 1
            if application.get("match_score_demo"):
                scores.append(float(application["match_score_demo"]))
        open_positions = [position for position in positions if position.status.lower() == "open"]
        policy_documents = self.list_documents(policy_only=True)
        return {
            "total_candidates": len(candidates),
            "active_recruitment_requests": len(open_positions),
            "active_openings": sum(position.openings for position in open_positions),
            "entities": len(by_company),
            "policy_documents": len(policy_documents),
            "average_match_score": round(sum(scores) / len(scores), 1) if scores else None,
            "by_company": sorted(by_company.items(), key=lambda x: x[1], reverse=True),
            "top_skills": sorted(skills.items(), key=lambda x: x[1], reverse=True)[:10],
            "recruitment_stages": sorted(stage_distribution.items()),
            "salary_compliance": sorted(salary_compliance.items()),
            "historical_series": [],
            "historical_series_status": "not_available_in_sample",
        }
