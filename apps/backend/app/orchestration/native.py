"""Native fallback orchestrator intentionally kept small for troubleshooting when CrewAI import/runtime is unavailable."""


def run_talent_native(request, data_gateway, gemini):
    from app.orchestration.talent_flow import TalentMatchingFlow
    flow = TalentMatchingFlow(request, data_gateway, gemini, guardrails=None, observability=_NoopObs())
    return flow.kickoff()


class _NoopObs:
    def emit(self, *args, **kwargs):
        pass
