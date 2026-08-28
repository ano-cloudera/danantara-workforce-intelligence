import re
from app.config import Settings
from app.models import GuardrailResult


class GuardrailsService:
    """Deterministic baseline guardrails. Extend with Guardrails AI validators if required."""

    INJECTION_PATTERNS = [
        r"ignore (all|any|the) previous instructions",
        r"reveal (the )?(system|developer) prompt",
        r"bypass (security|policy|guardrail)",
    ]

    # Requests for an individual's private contact details or personal
    # compensation, as opposed to public salary-band/policy information
    # (e.g. "salary band for grade G3" stays allowed).
    PII_REQUEST_PATTERNS = [
        r"\b(email|phone|contact)\s*(address|number)?\s*(of|for)\s+[a-z]",
        r"\b[a-z']+'s (email|phone|salary|contact)\b",
        r"\bwhat('?s| is) (his|her|their) (email|phone|salary|contact)\b",
        r"\bhow much does [a-z]+ (get paid|earn|make)\b",
        r"\bsalary (of|for) [a-z]+\b",
        r"\bgaji\s+si\s+[a-z]+\b",
        r"\bgaji(nya)?\s+[a-z]+\s+berapa\b",
        r"\b(nomor telepon|no telepon|nomor hp|no hp|email|kontak)\s+(dari|untuk)\s+[a-z]+\b",
    ]

    def __init__(self, settings: Settings, observability=None):
        self.settings = settings
        self.observability = observability

    def validate_input(self, text: str) -> GuardrailResult:
        if self.settings.guardrails_mode == "off":
            return GuardrailResult()
        reasons = []
        if len(text) > self.settings.guardrails_max_input_chars:
            reasons.append("input_too_long")
        lowered = text.lower()
        if any(re.search(p, lowered) for p in self.INJECTION_PATTERNS):
            reasons.append("prompt_injection_pattern")
        if any(re.search(p, lowered) for p in self.PII_REQUEST_PATTERNS):
            reasons.append("personal_data_request")
        result = GuardrailResult(allowed=not reasons, reasons=reasons, human_review_required=bool(reasons))
        if self.observability:
            self.observability.emit("guardrail", "input-guardrail", result.model_dump())
        return result

    def validate_policy_output(self, answer: str, source_count: int) -> GuardrailResult:
        reasons = []
        if self.settings.guardrails_require_policy_citations and source_count == 0:
            reasons.append("missing_sources")
        if not answer.strip():
            reasons.append("empty_answer")
        result = GuardrailResult(allowed=not reasons, reasons=reasons, human_review_required=True)
        if self.observability:
            self.observability.emit("guardrail", "policy-output-guardrail", result.model_dump())
        return result

    def validate_talent_output(self, match_count: int) -> GuardrailResult:
        reasons = [] if match_count else ["no_candidates"]
        result = GuardrailResult(allowed=not reasons, reasons=reasons, human_review_required=True)
        if self.observability:
            self.observability.emit("guardrail", "talent-output-guardrail", result.model_dump())
        return result
