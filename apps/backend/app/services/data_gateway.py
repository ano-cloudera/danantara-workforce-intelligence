import json

from app.config import Settings
from app.models import Candidate, Position


class DataGateway:
    def __init__(self, settings: Settings, observability=None):
        self.settings = settings
        self.observability = observability
        self.demo_root = settings.project_root / "data" / "workforce-app" / "demo"

    def list_candidates(self, company: str | None = None) -> list[Candidate]:
        if self.settings.data_mode == "impala":
            return self._impala_candidates(company)
        rows = json.loads((self.demo_root / "candidates.json").read_text())
        items = [Candidate(**r) for r in rows]
        if company:
            items = [c for c in items if (c.company or "").lower() == company.lower()]
        return items

    def list_positions(self) -> list[Position]:
        if self.settings.data_mode == "impala":
            return self._impala_positions()
        rows = json.loads((self.demo_root / "positions.json").read_text())
        return [Position(**r) for r in rows]

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
        return connect(
            host=self.settings.impala_host,
            port=self.settings.impala_port,
            database=self.settings.impala_database,
            auth_mechanism=self.settings.impala_auth_mechanism,
            user=self.settings.impala_user,
            password=self.settings.impala_password,
            use_ssl=self.settings.impala_use_ssl,
        )

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

    def dashboard_summary(self) -> dict:
        candidates = self.list_candidates()
        by_company: dict[str, int] = {}
        skills: dict[str, int] = {}
        for c in candidates:
            by_company[c.company or "Unknown"] = by_company.get(c.company or "Unknown", 0) + 1
            for s in c.skills:
                skills[s] = skills.get(s, 0) + 1
        return {
            "total_candidates": len(candidates),
            "by_company": sorted(by_company.items(), key=lambda x: x[1], reverse=True),
            "top_skills": sorted(skills.items(), key=lambda x: x[1], reverse=True)[:10],
        }
