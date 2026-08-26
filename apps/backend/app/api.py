import uuid

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.config import Settings
from app.models import (
    CandidateForm,
    FeedbackRequest,
    PolicyQueryRequest,
    PolicyQueryResponse,
    PolicySource,
    PublicConfig,
    TalentMatchRequest,
    TalentMatchResponse,
)
from app.orchestration.policy_flow import PolicyRAGFlow
from app.orchestration.talent_flow import TalentMatchingFlow


def build_router(services: dict, settings: Settings) -> APIRouter:
    router = APIRouter()

    def user_id(x_user_id: str | None):
        return x_user_id or settings.demo_user

    @router.get("/health")
    def health():
        return {
            "status": "ok",
            "gemini": services["gemini"].health(),
            "qdrant": services["qdrant"].healthy(),
            "data_mode": settings.data_mode,
            "orchestrator_mode": settings.orchestrator_mode,
        }

    @router.get("/health/qdrant")
    def qdrant_health():
        return services["qdrant"].diagnostics()

    @router.get("/config/public", response_model=PublicConfig)
    def public_config():
        return PublicConfig(
            environment=settings.environment,
            data_mode=settings.data_mode,
            orchestrator_mode=settings.orchestrator_mode,
            qdrant_mode=settings.qdrant_mode,
            guardrails_mode=settings.guardrails_mode,
            gemini_text_model=settings.gemini_text_model,
            gemini_embedding_model=settings.gemini_embedding_model,
            services={
                "qdrant_healthy": services["qdrant"].healthy(),
                "observability_configured": bool(settings.observability_base_url),
            },
        )

    @router.get("/candidates")
    def candidates(company: str | None = None):
        return [x.model_dump() for x in services["data"].list_candidates(company)]

    @router.get("/positions")
    def positions():
        return [x.model_dump() for x in services["data"].list_positions()]

    @router.post("/talent/match", response_model=TalentMatchResponse)
    def talent_match(payload: TalentMatchRequest, x_user_id: str | None = Header(default=None)):
        uid = user_id(x_user_id)
        sid = services["store"].ensure_session(payload.session_id, uid)
        request_id = str(uuid.uuid4())
        services["obs"].set_context(session_id=sid, user_id=uid, request_id=request_id)
        input_guard = services["guardrails"].validate_input(
            (payload.position_title or "") + " " + " ".join(payload.skills_keywords)
        )
        if not input_guard.allowed:
            raise HTTPException(
                400,
                detail={
                    "message": "Input blocked by guardrail",
                    "guardrail": input_guard.model_dump(),
                },
            )
        flow = TalentMatchingFlow(
            payload, services["data"], services["gemini"], services["guardrails"], services["obs"]
        )
        flow.kickoff()
        matches = flow.state.final
        output_guard = services["guardrails"].validate_talent_output(len(matches))
        return TalentMatchResponse(
            request_id=request_id,
            session_id=sid,
            position=flow.state.position,
            matches=matches,
            guardrail=output_guard,
            human_review_required=True,
        )

    @router.post("/policy/query", response_model=PolicyQueryResponse)
    def policy_query(payload: PolicyQueryRequest, x_user_id: str | None = Header(default=None)):
        uid = user_id(x_user_id)
        sid = services["store"].ensure_session(payload.session_id, uid)
        request_id = str(uuid.uuid4())
        services["obs"].set_context(session_id=sid, user_id=uid, request_id=request_id)
        input_guard = services["guardrails"].validate_input(payload.question)
        if not input_guard.allowed:
            raise HTTPException(
                400,
                detail={
                    "message": "Input blocked by guardrail",
                    "guardrail": input_guard.model_dump(),
                },
            )
        flow = PolicyRAGFlow(
            payload,
            services["qdrant"],
            services["policy_fallback"],
            services["gemini"],
            services["obs"],
        )
        flow.kickoff()
        sources = [PolicySource(**s) for s in flow.state.sources]
        output_guard = services["guardrails"].validate_policy_output(
            flow.state.answer, len(sources)
        )
        citations = [f"[{i}] {s.title}" for i, s in enumerate(sources, start=1)]
        return PolicyQueryResponse(
            request_id=request_id,
            session_id=sid,
            answer=flow.state.answer,
            sources=sources,
            citations=citations,
            guardrail=output_guard,
            human_review_required=True,
        )

    @router.post("/policy/compare", response_model=PolicyQueryResponse)
    def policy_compare(payload: PolicyQueryRequest, x_user_id: str | None = Header(default=None)):
        if not payload.question.lower().startswith("compare"):
            payload.question = f"Compare the following policy topic across the selected entities: {payload.topic or payload.question}. {payload.question}"
        return policy_query(payload, x_user_id)

    @router.post("/sources/candidate")
    def candidate_form(payload: CandidateForm):
        item_id = services["store"].add_candidate_submission(payload.model_dump())
        return {
            "status": "accepted",
            "submission_id": item_id,
            "routing": "nifi" if settings.ingest_mode == "nifi" else "backend_poc_fallback",
        }

    @router.post("/sources/upload")
    async def source_upload(
        file: UploadFile = File(...),
        entity: str | None = Form(default=None),
        doc_type: str | None = Form(default=None),
    ):
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(413, "File exceeds 50 MB PoC limit")
        return services["ingestion"].save_and_process(
            file.filename or "upload.pdf", content, entity, doc_type
        )

    @router.post("/feedback")
    def feedback(payload: FeedbackRequest):
        services["store"].add_feedback(payload.model_dump())
        services["obs"].emit(
            "feedback",
            "user-feedback",
            {"rating": payload.rating, "has_comment": bool(payload.comment)},
        )
        return {"status": "recorded"}

    @router.get("/dashboard/summary")
    def dashboard_summary():
        return services["data"].dashboard_summary()

    return router
