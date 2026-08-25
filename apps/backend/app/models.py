from typing import Any
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    allowed: bool = True
    reasons: list[str] = Field(default_factory=list)
    human_review_required: bool = False


class Candidate(BaseModel):
    candidate_id: str
    name: str
    company: str | None = None
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    summary: str = ""


class Position(BaseModel):
    position_id: str
    title: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: float = 0


class CandidateMatch(BaseModel):
    candidate: Candidate
    match_score: float
    matched_skills: list[str]
    skill_gaps: list[str]
    preferred_skills_matched: list[str] = Field(default_factory=list)
    reasoning: str = ""


class TalentMatchRequest(BaseModel):
    position_id: str | None = None
    position_title: str | None = None
    company: str | None = None
    skills_keywords: list[str] = Field(default_factory=list)
    top_n: int = Field(default=5, ge=1, le=20)
    session_id: str | None = None


class TalentMatchResponse(BaseModel):
    request_id: str
    session_id: str
    position: Position
    matches: list[CandidateMatch]
    guardrail: GuardrailResult
    human_review_required: bool = True


class PolicyQueryRequest(BaseModel):
    question: str
    entities: list[str] = Field(default_factory=list)
    topic: str | None = None
    top_k: int | None = None
    session_id: str | None = None


class PolicySource(BaseModel):
    source_id: str
    entity: str | None = None
    title: str
    page: int | None = None
    score: float | None = None
    text_excerpt: str = ""


class PolicyQueryResponse(BaseModel):
    request_id: str
    session_id: str
    answer: str
    sources: list[PolicySource]
    citations: list[str] = Field(default_factory=list)
    guardrail: GuardrailResult
    human_review_required: bool = True


class CandidateForm(BaseModel):
    full_name: str
    company: str
    position_applied: str
    email: str
    phone: str | None = None
    core_skills: list[str] = Field(default_factory=list)
    years_experience: float = 0
    notes: str | None = None


class FeedbackRequest(BaseModel):
    session_id: str
    request_id: str | None = None
    user_id: str | None = None
    rating: int = Field(ge=-1, le=1)
    comment: str | None = None


class PublicConfig(BaseModel):
    environment: str
    data_mode: str
    orchestrator_mode: str
    qdrant_mode: str
    guardrails_mode: str
    gemini_text_model: str
    gemini_embedding_model: str
    services: dict[str, Any]
