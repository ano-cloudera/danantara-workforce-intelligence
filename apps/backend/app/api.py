import logging
import uuid
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.config import Settings
from app.models import (
    CandidateForm,
    FeedbackRequest,
    PolicyChatRequest,
    PolicyExportRequest,
    PolicyQueryRequest,
    PolicyQueryResponse,
    PolicySource,
    PublicConfig,
    TalentMatchRequest,
    TalentMatchResponse,
)
from app.orchestration.policy_flow import PolicyRAGFlow
from app.orchestration.talent_flow import TalentMatchingFlow
from app.services.pdf_export import build_policy_pdf


logger = logging.getLogger(__name__)


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

    @router.get("/candidates/{candidate_id}")
    def candidate_detail(candidate_id: str):
        try:
            return services["data"].get_candidate(candidate_id).model_dump()
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc

    @router.get("/positions")
    def positions():
        return [x.model_dump() for x in services["data"].list_positions()]

    @router.get("/search")
    def global_search(
        q: str = Query(min_length=2, max_length=200),
        types: str | None = None,
        limit: int = Query(default=5, ge=1, le=20),
    ):
        selected = {value.strip().lower() for value in (types or "").split(",") if value.strip()}
        return services["data"].search(q, selected or None, limit)

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
        try:
            flow.kickoff()
        except ValueError as exc:
            raise HTTPException(404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("talent_match flow failed request_id=%s", request_id)
            raise HTTPException(
                502,
                detail={
                    "message": "Talent match failed",
                    "request_id": request_id,
                    "error": str(exc),
                },
            ) from exc
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

    def execute_policy_query(payload: PolicyQueryRequest, uid: str) -> PolicyQueryResponse:
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
        history = services["store"].list_policy_messages(sid)[-8:]
        services["store"].add_policy_message(sid, "user", payload.question, request_id=request_id)
        flow = PolicyRAGFlow(
            payload,
            services["qdrant"],
            services["policy_fallback"],
            services["gemini"],
            services["obs"],
            history=history,
        )
        try:
            flow.kickoff()
        except Exception as exc:
            logger.exception("policy_query flow failed request_id=%s", request_id)
            raise HTTPException(
                502,
                detail={
                    "message": "Policy retrieval or generation failed",
                    "request_id": request_id,
                    "error": str(exc),
                },
            ) from exc
        sources = [PolicySource(**s) for s in flow.state.sources]
        output_guard = services["guardrails"].validate_policy_output(
            flow.state.answer, len(sources)
        )
        citations = [f"[{i}] {s.title}" for i, s in enumerate(sources, start=1)]
        source_payloads = [source.model_dump() for source in sources]
        message_id = services["store"].add_policy_message(
            sid,
            "assistant",
            flow.state.answer,
            request_id=request_id,
            sources=source_payloads,
        )
        selected_entities = ", ".join(payload.entities) if payload.entities else "the selected entities"
        suggestions = [
            f"What exceptions apply for {selected_entities}?",
            f"Summarize the approval and escalation requirements for {selected_entities}.",
            "Which source sections should HR review before making a decision?",
        ]
        return PolicyQueryResponse(
            request_id=request_id,
            session_id=sid,
            answer=flow.state.answer,
            sources=sources,
            citations=citations,
            guardrail=output_guard,
            human_review_required=True,
            message_id=message_id,
            suggested_questions=suggestions,
        )

    @router.post("/policy/query", response_model=PolicyQueryResponse)
    def policy_query(payload: PolicyQueryRequest, x_user_id: str | None = Header(default=None)):
        return execute_policy_query(payload, user_id(x_user_id))

    @router.post("/policy/compare", response_model=PolicyQueryResponse)
    def policy_compare(payload: PolicyQueryRequest, x_user_id: str | None = Header(default=None)):
        if not payload.question.lower().startswith("compare"):
            payload.question = f"Compare the following policy topic across the selected entities: {payload.topic or payload.question}. {payload.question}"
        return policy_query(payload, x_user_id)

    @router.post("/policy/chat", response_model=PolicyQueryResponse)
    def policy_chat(payload: PolicyChatRequest, x_user_id: str | None = Header(default=None)):
        query = PolicyQueryRequest(
            question=payload.message,
            entities=payload.filters.entities,
            topic=payload.filters.topics[0] if payload.filters.topics else None,
            document_types=payload.filters.document_types,
            top_k=payload.retrieval.top_k,
            session_id=payload.session_id,
        )
        return execute_policy_query(query, user_id(x_user_id))

    @router.get("/policy/sessions/{session_id}")
    def policy_session(session_id: str):
        return {
            "session_id": session_id,
            "messages": services["store"].list_policy_messages(session_id),
        }

    @router.post("/policy/export")
    def policy_export(payload: PolicyExportRequest):
        answer = services["store"].get_policy_answer(payload.request_id)
        if not answer:
            raise HTTPException(404, "Policy answer not found")
        messages = services["store"].list_policy_messages(answer["session_id"])
        title = payload.title or "Danantara Workforce Intelligence - Policy Conversation"
        pdf = build_policy_pdf(title, messages)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="policy-conversation.pdf"'},
        )

    @router.get("/documents/{document_id}")
    def document_detail(document_id: str):
        try:
            document = services["data"].get_document(document_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        private_fields = {"relative_path", "source_s3_uri"}
        return {key: value for key, value in document.items() if key not in private_fields}

    @router.get("/documents/{document_id}/download")
    def document_download(document_id: str):
        try:
            filename, content = services["data"].read_document(document_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        media_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return Response(
            content=content,
            media_type=media_types.get(suffix, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )

    @router.post("/sources/candidate")
    def candidate_form(payload: CandidateForm):
        item_id = services["store"].add_candidate_submission(payload.model_dump())
        return {
            "status": "accepted",
            "submission_id": item_id,
            "routing": "nifi" if settings.ingest_mode == "nifi" else "backend_poc_fallback",
        }

    @router.get("/sources")
    def source_inventory():
        documents = []
        for item in services["data"].list_documents():
            private_fields = {"relative_path", "source_s3_uri"}
            documents.append({key: value for key, value in item.items() if key not in private_fields})
        return {"documents": documents, "uploads": services["store"].list_uploads()}

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
        try:
            return services["data"].dashboard_summary()
        except Exception as exc:
            logger.exception("dashboard_summary failed")
            raise HTTPException(
                502,
                detail={"message": "Dashboard summary failed", "error": str(exc)},
            ) from exc

    return router
