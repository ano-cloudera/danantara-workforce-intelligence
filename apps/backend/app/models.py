from typing import Any, Literal
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    allowed: bool = True
    reasons: list[str] = Field(default_factory=list)
    human_review_required: bool = False


class Candidate(BaseModel):
    candidate_id: str
    name: str
    company: str | None = None
    current_title: str | None = None
    years_experience: float = 0
    skills: list[str] = Field(default_factory=list)
    skill_proficiency: dict[str, int] = Field(default_factory=dict)
    summary: str = ""
    education_level: str | None = None
    education_institution: str | None = None
    city: str | None = None
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    application_id: str | None = None
    position_id: str | None = None
    application_stage: str | None = None
    application_status: str | None = None
    salary_compliance: str | None = None
    source_documents: list[str] = Field(default_factory=list)


class Position(BaseModel):
    position_id: str
    title: str
    entity: str | None = None
    grade: str | None = None
    level: str | None = None
    department: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: float = 0
    competency_ids: list[str] = Field(default_factory=list)
    openings: int = 1
    status: str = "Open"
    open_date: str | None = None
    matched_entities: list[str] = Field(default_factory=list)


class CandidateMatch(BaseModel):
    candidate: Candidate
    match_score: float
    matched_skills: list[str]
    skill_gaps: list[str]
    preferred_skills_matched: list[str] = Field(default_factory=list)
    keyword_matches: list[str] = Field(default_factory=list)
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
    document_types: list[str] = Field(default_factory=list)
    top_k: int | None = None
    session_id: str | None = None


class PolicyChatFilters(BaseModel):
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)


class PolicyRetrievalOptions(BaseModel):
    top_k: int = Field(default=6, ge=1, le=20)


class PolicyChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None
    filters: PolicyChatFilters = Field(default_factory=PolicyChatFilters)
    retrieval: PolicyRetrievalOptions = Field(default_factory=PolicyRetrievalOptions)


class PolicySource(BaseModel):
    source_id: str
    document_id: str | None = None
    entity: str | None = None
    title: str
    document_type: str | None = None
    page: int | None = None
    section: str | None = None
    score: float | None = None
    text_excerpt: str = ""
    view_url: str | None = None
    download_url: str | None = None


class ChartData(BaseModel):
    title: str
    items: list[tuple[str, float]] = Field(default_factory=list)
    kind: Literal["bar"] = "bar"


class PolicyQueryResponse(BaseModel):
    request_id: str
    session_id: str
    answer: str
    sources: list[PolicySource]
    citations: list[str] = Field(default_factory=list)
    guardrail: GuardrailResult
    human_review_required: bool = True
    message_id: str | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    chart: ChartData | None = None
    response_kind: Literal["grounded", "data", "conversational"] = "grounded"


class PolicyExportRequest(BaseModel):
    request_id: str
    title: str | None = None


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
