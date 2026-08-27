import json
from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen

from app.models import CandidateMatch, TalentMatchRequest


class TalentState(BaseModel):
    request: dict = {}
    position: dict = {}
    scored: list[dict] = []
    final: list[dict] = []


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
        position = self.data_gateway.get_position(req.position_id, req.position_title)
        keywords = [k.lower().strip() for k in req.skills_keywords if k.strip()]
        candidates = self.data_gateway.list_candidates(req.company)
        required = {s.lower(): s for s in position.required_skills}
        preferred = {s.lower(): s for s in position.preferred_skills}
        scored = []
        for c in candidates:
            cskills = {s.lower(): s for s in c.skills}
            matched = [label for key,label in required.items() if key in cskills]
            gaps = [label for key,label in required.items() if key not in cskills]
            pref_match = [label for key,label in preferred.items() if key in cskills]
            skill_score = (len(matched) / max(1, len(required))) * 75
            experience_score = min(15, (c.years_experience / max(1, position.min_years_experience)) * 15)
            preferred_score = min(10, len(pref_match) * 5)
            keyword_matches = [
                label for key, label in cskills.items()
                if any(keyword in key for keyword in keywords)
            ]
            keyword_score = min(10, len(keyword_matches) * 5) if keywords else 0
            score = round(min(100, skill_score + experience_score + preferred_score + keyword_score), 1)
            scored.append({"candidate": c.model_dump(), "match_score": score, "matched_skills": matched, "skill_gaps": gaps, "preferred_skills_matched": pref_match, "keyword_matches": keyword_matches, "reasoning": ""})
        scored.sort(key=lambda x: x["match_score"], reverse=True)
        self.state.position = position.model_dump()
        self.state.scored = scored[: req.top_n]
        self.observability.emit("tool", "candidate-scoring", {"candidate_count": len(candidates), "top_n": req.top_n})
        return self.state.scored

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
