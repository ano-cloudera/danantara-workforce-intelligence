# Project State

**State:** Scaffold complete, environment validation pending  
**Target readiness:** 95% PoC-ready  
**Primary runtime:** Cloudera AI Workbench Applications  
**Last architectural decision:** Use custom CrewAI Flow backend as the main runtime, with Agent Studio retained only as a capability showcase.

## Locked decisions

- Four logical applications: frontend, backend, qdrant, observability.
- Gemini is the default LLM and embedding provider.
- `from google import genai` is the required Gemini SDK path.
- CrewAI Flows are the default orchestration engine.
- No LangChain dependency in the baseline.
- Qdrant is the vector store.
- One Qdrant deployment is shared safely: NiFi, Workforce candidates and Workforce policies use
  distinct collections configured by `QDRANT_NIFI_COLLECTION`, `QDRANT_CANDIDATE_COLLECTION` and
  `QDRANT_POLICY_COLLECTION`.
- Local workload data is separated under `data/nifi-demo/` and `data/workforce-app/`; folders are
  not used as a substitute for Qdrant collection isolation.
- SQLite is application state only and stays with the backend.
- Cloudera Data Engineering owns raw-to-curated Spark transformation.
- Cloudera Data Warehouse / Impala is the structured serving layer.
- Cloudera Data Visualization is the management analytics experience.
- Guardrails run before orchestration and before returning final output.
- Observability captures request, retrieval, tool, generation and guardrail events.

## Environment-specific tasks still required

- [ ] Set `GEMINI_API_KEY` or Vertex AI settings.
- [ ] Create the four CAI Applications and capture their URLs.
- [ ] Set `BACKEND_BASE_URL` in frontend application variables.
- [ ] Set `QDRANT_URL`, shared Qdrant API key and the three collection variables in backend/NiFi.
- [ ] Run `apps/backend/scripts/init_qdrant_collections.py` and verify all three collections.
- [ ] Validate Qdrant binary download from the target CAI runtime, or upload binary manually.
- [ ] Configure CDW Impala connection and change `DATA_MODE=impala`.
- [ ] Configure NiFi webhook/landing integration and change `INGEST_MODE=nifi` if required.
- [ ] Configure optional Langfuse credentials if enterprise LLM tracing is required.
- [ ] Replace demo candidate/policy data with customer-provided PoC data.
- [ ] Validate Ranger permissions for the service/user identities used by the PoC.

## Next implementation sequence

1. Validate backend Gemini health.
2. Validate frontend to backend proxy.
3. Validate Qdrant and index policy sample.
4. Validate Policy Intelligence end-to-end.
5. Configure CDW and validate candidate query.
6. Validate Talent Intelligence end-to-end.
7. Connect NiFi/CDE pipeline.
8. Connect Cloudera Data Visualization dashboard URL.
9. Turn on optional Langfuse forwarding.
10. Execute demo rehearsal and freeze configuration.
