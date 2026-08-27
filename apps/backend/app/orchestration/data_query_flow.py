import json
from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen


class DataQueryState(BaseModel):
    question: str = ""
    entity: str | None = None
    query_id: str = ""
    result: dict = {}
    answer: str = ""


# Whitelisted queries only. Gemini is never allowed to produce SQL or table
# names -- it only ever picks a query_id from this fixed list, plus an
# optional entity filter. Each handler receives (data_gateway, entity) and
# returns {"summary": {...}, "chart": {"title": str, "items": [(label, value), ...]} | None}.
QUERY_REGISTRY = {
    "candidate_count": "Total number of candidates, optionally filtered by entity",
    "candidates_over_time": "Candidate count grouped by month",
    "recruitment_stage_breakdown": "Candidate count grouped by recruitment pipeline stage",
    "open_positions_summary": "Count and openings of currently open positions, optionally filtered by entity",
}


def _run_candidate_count(data_gateway, entity: str | None) -> dict:
    candidates = data_gateway.list_candidates(entity)
    if entity:
        return {"summary": {"entity": entity, "count": len(candidates)}, "chart": None}
    by_entity: dict[str, int] = {}
    for c in candidates:
        key = c.company or "Unknown"
        by_entity[key] = by_entity.get(key, 0) + 1
    items = sorted(by_entity.items(), key=lambda x: x[1], reverse=True)
    return {
        "summary": {"total": len(candidates), "by_entity": items},
        "chart": {"title": "Candidates by entity", "items": items},
    }


def _run_candidates_over_time(data_gateway, entity: str | None) -> dict:
    items = data_gateway.candidates_by_month()
    return {
        "summary": {"months": items},
        "chart": {"title": "Candidates by month", "items": items} if items else None,
    }


def _run_recruitment_stage_breakdown(data_gateway, entity: str | None) -> dict:
    rows = data_gateway.recruitment_pipeline()
    if entity:
        rows = [r for r in rows if (r.get("entity") or "").lower() == entity.lower()]
    counts: dict[str, int] = {}
    for row in rows:
        stage = row.get("stage") or "Unknown"
        counts[stage] = counts.get(stage, 0) + 1
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return {
        "summary": {"entity": entity, "total": len(rows), "by_stage": items},
        "chart": {"title": "Candidates by recruitment stage", "items": items} if items else None,
    }


def _run_open_positions_summary(data_gateway, entity: str | None) -> dict:
    positions = data_gateway.list_positions()
    open_positions = [p for p in positions if p.status.lower() == "open"]
    if entity:
        open_positions = [p for p in open_positions if (p.entity or "").lower() == entity.lower()]
        total_openings = sum(p.openings for p in open_positions)
        return {
            "summary": {"entity": entity, "open_positions": len(open_positions), "total_openings": total_openings},
            "chart": None,
        }
    by_entity: dict[str, int] = {}
    for p in open_positions:
        key = p.entity or "Unknown"
        by_entity[key] = by_entity.get(key, 0) + p.openings
    items = sorted(by_entity.items(), key=lambda x: x[1], reverse=True)
    return {
        "summary": {
            "open_positions": len(open_positions),
            "total_openings": sum(p.openings for p in open_positions),
            "by_entity": items,
        },
        "chart": {"title": "Open positions by entity", "items": items} if items else None,
    }


QUERY_HANDLERS = {
    "candidate_count": _run_candidate_count,
    "candidates_over_time": _run_candidates_over_time,
    "recruitment_stage_breakdown": _run_recruitment_stage_breakdown,
    "open_positions_summary": _run_open_positions_summary,
}


class DataQueryFlow(Flow[DataQueryState]):
    def __init__(self, question: str, entity: str | None, data_gateway, gemini, observability):
        super().__init__()
        self.state.question = question
        self.state.entity = entity
        self.data_gateway = data_gateway
        self.gemini = gemini
        self.observability = observability

    @start()
    def classify_and_run(self):
        query_id = self._classify()
        self.state.query_id = query_id
        handler = QUERY_HANDLERS.get(query_id)
        if not handler:
            self.state.result = {}
            self.observability.emit("tool", "data-query", {"query_id": query_id or "none", "matched": False})
            return self.state.result
        result = handler(self.data_gateway, self.state.entity)
        self.state.result = result
        self.observability.emit(
            "tool",
            "data-query",
            {"query_id": query_id, "matched": True, "has_chart": bool(result.get("chart"))},
        )
        return result

    def _classify(self) -> str:
        options = "\n".join(f"- {qid}: {desc}" for qid, desc in QUERY_REGISTRY.items())
        prompt = f"""Classify the following workforce-data question into exactly one of these fixed query IDs, or null if none apply. Never invent a new query_id. Return JSON only: {{"query_id": "..." or null, "entity": "..." or null}}.

Available query IDs:
{options}

Question: {self.state.question}"""
        try:
            payload = self.gemini.generate_json(prompt, "data-query-classify")
            query_id = payload.get("query_id") if isinstance(payload, dict) else None
            entity = payload.get("entity") if isinstance(payload, dict) else None
            if entity and not self.state.entity:
                self.state.entity = str(entity)
        except Exception:
            query_id = None
        return query_id if query_id in QUERY_REGISTRY else ""

    @listen(classify_and_run)
    def narrate(self, result):
        if not result or not result.get("summary"):
            self.state.answer = ""
            return ""
        prompt = f"""You are a workforce-data assistant. In one or two short sentences, summarize this query result for an HR user. Do not invent numbers beyond what is given.\nQuestion: {self.state.question}\nResult: {json.dumps(result["summary"], default=str)}"""
        try:
            self.state.answer = self.gemini.generate_text(prompt, "data-query-narration").strip()
        except Exception:
            self.state.answer = f"Here is the data for your question: {json.dumps(result['summary'], default=str)}"
        return self.state.answer
