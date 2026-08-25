# Risk Register

| Risk | Impact | Treatment |
|---|---|---|
| Agent Studio provider mismatch | High | Custom CrewAI Flow backend is primary runtime |
| Qdrant binary download blocked | Medium | Allow pre-uploaded binary or external Qdrant URL |
| CDW credentials unavailable early | Medium | Keep `DATA_MODE=demo` fallback |
| NiFi integration not ready | Medium | Keep direct backend upload fallback for PoC |
| LLM hallucination | High | Grounded retrieval, citations, guardrails, human review |
| Candidate PII in logs | High | PII-safe observability defaults |
| SQLite scaling | Low for PoC | Replace with PostgreSQL before HA/scale |
| Langfuse unavailable | Low | Local observability gateway remains functional |
