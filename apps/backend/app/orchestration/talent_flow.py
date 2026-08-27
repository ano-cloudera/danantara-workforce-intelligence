import json
from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen

from app.models import CandidateMatch, TalentMatchRequest


class TalentState(BaseModel):
    request: dict = {}
    position: dict = {}
    scored: list[dict] = []
    final: list[dict] = []


def score_candidate(candidate, position, keywords: list[str]) -> dict:
    required = {s.lower(): s for s in position.required_skills}
    preferred = {s.lower(): s for s in position.preferred_skills}
    cskills = {s.lower(): s for s in candidate.skills}
    matched = [label for key, label in required.items() if key in cskills]
    gaps = [label for key, label in required.items() if key not in cskills]
    pref_match = [label for key, label in preferred.items() if key in cskills]
    skill_score = (len(matched) / max(1, len(required))) * 75
    experience_score = min(15, (candidate.years_experience / max(1, position.min_years_experience)) * 15)
    preferred_score = min(10, len(pref_match) * 5)
    keyword_matches = [
        label for key, label in cskills.items()
        if any(keyword in key for keyword in keywords)
    ]
    keyword_score = min(10, len(keyword_matches) * 5) if keywords else 0
    score = round(min(100, skill_score + experience_score + preferred_score + keyword_score), 1)
    return {
        "candidate": candidate.model_dump(),
        "match_score": score,
        "matched_skills": matched,
        "skill_gaps": gaps,
        "preferred_skills_matched": pref_match,
        "keyword_matches": keyword_matches,
        "reasoning": "",
        "position_id": position.position_id,
    }


class TalentMatchingFlow(Flow[TalentState]):
    def __init__(self, request: TalentMatchRequest, data_gateway, gemini, guardrails, observability):
        super().__init__()
        self.state.request = request.model_dump()
        self.data_gateway = data_gateway
        self.gemini = gemini
        self.guardrails = guardrails
        self.observability = observability

    @start()
    def load_and_score(self):
        req = TalentMatchRequest(**self.state.request)
        keywords = [k.lower().strip() for k in req.skills_keywords if k.strip()]

        positions = self._resolve_positions(req)
        candidates = self.data_gateway.list_candidates(req.company)

        scored = []
        if len(positions) == 1:
            position = positions[0]
            for c in candidates:
                scored.append(score_candidate(c, position, keywords))
        else:
            positions_by_entity = {(p.entity or "").lower(): p for p in positions}
            for c in candidates:
                position = positions_by_entity.get((c.company or "").lower())
                if not position:
                    continue
                scored.append(score_candidate(c, position, keywords))

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        self.state.position = (
            positions[0].model_dump()
            if len(positions) == 1
            else {
                "title": positions[0].title,
                "matched_entities": sorted({p.entity for p in positions if p.entity}),
            }
        )
        self.state.scored = scored[: req.top_n]
        self.observability.emit(
            "tool",
            "candidate-scoring",
            {"candidate_count": len(candidates), "position_count": len(positions), "top_n": req.top_n},
        )
        return self.state.scored

    def _resolve_positions(self, req: TalentMatchRequest) -> list:
        if req.position_id or req.company:
            return [self.data_gateway.get_position(req.position_id, req.position_title, req.company)]
        if req.position_title:
            positions = self.data_gateway.get_positions_by_title(req.position_title)
            if positions:
                return positions
        return [self.data_gateway.get_position(req.position_id, req.position_title, req.company)]

    @listen(load_and_score)
    def add_reasoning(self, scored):
        if not scored:
            self.state.final = []
            return []
        prompt = f"""You are an HR talent analyst. Explain the following deterministic candidate ranking without changing any scores. Be concise, evidence-based and explicitly mention important skill gaps. Return JSON array with candidate_id and reasoning only.\nPosition: {json.dumps(self.state.position)}\nCandidates: {json.dumps(scored)}\n"""
        try:
            rows = self.gemini.generate_json(prompt, "talent-reasoning")
            reason_map = {str(x.get("candidate_id")): str(x.get("reasoning", "")) for x in rows if isinstance(x, dict)} if isinstance(rows, list) else {}
        except Exception:
            reason_map = {}
        for item in scored:
            cid = item["candidate"]["candidate_id"]
            item["reasoning"] = reason_map.get(cid) or f"Match score is based on required skills, preferred skills and experience. Review gaps: {', '.join(item['skill_gaps']) or 'none identified'}."
        self.state.final = scored
        return scored
