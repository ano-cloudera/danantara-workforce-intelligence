from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class S3Object:
    bucket: str
    key: str
    etag: str
    size: int = 0

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


@dataclass
class Skill:
    name: str
    proficiency: int | None = None
    years_experience: float | None = None
    evidence: str = ""


@dataclass
class Experience:
    employer: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    summary: str = ""


@dataclass
class Education:
    institution: str
    level: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None


@dataclass
class CandidateProfile:
    candidate_id: str
    full_name: str
    entity: str | None = None
    current_title: str | None = None
    years_experience: float = 0
    city: str | None = None
    education_level: str | None = None
    education_institution: str | None = None
    professional_summary: str = ""
    email: str | None = None
    phone: str | None = None
    skills: list[Skill] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    extraction_confidence: float | None = None

    def qdrant_text(self) -> str:
        """Return professional content only; exclude contact details and raw CV text."""
        skill_names = ", ".join(skill.name for skill in self.skills)
        roles = "; ".join(
            " - ".join(value for value in (item.role, item.employer, item.summary) if value)
            for item in self.experiences
        )
        return "\n".join(
            value
            for value in (
                f"Current title: {self.current_title}" if self.current_title else "",
                f"Years experience: {self.years_experience}",
                f"Skills: {skill_names}" if skill_names else "",
                f"Summary: {self.professional_summary}" if self.professional_summary else "",
                f"Experience: {roles}" if roles else "",
            )
            if value
        )
