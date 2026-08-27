# Project State

**State:** Scaffold complete, environment validation pending  
**Target readiness:** 95% PoC-ready  
**Primary runtime:** Cloudera AI Workbench Applications  
**Last architectural decision:** Use custom CrewAI Flow backend as the main runtime, with Agent Studio retained only as a capability showcase.

## Locked decisions

- Four logical applications: frontend, backend, qdrant, observability.
- All four CAI launchers bind to `127.0.0.1` in Workbench and resolve their port using
  `CDSW_APP_PORT -> PORT -> local development default`; CAI exposed ports are never fixed in code.
- Inter-Application calls use CAI-assigned URLs configured through `BACKEND_BASE_URL`,
  `QDRANT_BASE_URL`, and `OBSERVABILITY_BASE_URL`.
- Gemini is the default LLM and embedding provider.
- `from google import genai` is the required Gemini SDK path.
- CrewAI Flows are the default orchestration engine.
- No LangChain dependency in the baseline.
- Qdrant is the vector store.
- The backend uses Qdrant's REST API through `httpx` for CAI health, collection management, upsert,
  and query operations; this is the stable transport across the platform Istio/Envoy proxy.
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
- Delivery method is proportional: direct implementation for bounded changes, lightweight
  spec-kit planning for medium well-defined features, and BMAD for material business/architecture
  work. BMAD is not the default for every change.
- The frontend uses one responsive six-page enterprise shell, same-origin API proxying, the
  official `assets/logo.webp` brand mark (including favicon), and named `lucide-react` icons.
  Functional enterprise icons replace decorative AI/sparkle motifs; primary-action icons are white.
- Supplied CV, registration, job-opening, salary, Group-policy, PKB, and curated CSV samples are
  normalized into safe local demo fixtures; public candidate APIs exclude direct identifiers and
  protected HR attributes.
- Policy Intelligence is a citation-first multi-turn workspace. SQLite stores Policy conversation
  state and feedback, while sources remain in governed documents/Qdrant and structured data remains
  in CDW.
- Global search groups candidates, positions, skills, and policy documents and remains accessible
  through a responsive overlay on compact layouts.
- A one-shot scheduled CAI CV ingestion Job is available as a PoC fallback while the NiFi/CDE flow
  is completed. It uses S3 URI plus ETag idempotency, writes Iceberg through Impala, indexes only a
  sanitized professional projection in `QDRANT_CANDIDATE_COLLECTION`, and emits PII-free pipeline
  events. It is not a fifth Application and does not replace NiFi/CDE as the target architecture.

## Environment-specific tasks still required

- [ ] Set `GEMINI_API_KEY` or Vertex AI settings.
- [ ] Create the four CAI Applications and capture their URLs.
- [ ] Set `BACKEND_BASE_URL` in frontend application variables.
- [ ] Set `QDRANT_BASE_URL`, shared Qdrant API key and the three collection variables in backend/NiFi.
- [ ] Set `OBSERVABILITY_BASE_URL` in backend Application variables.
- [ ] Confirm each CAI Application receives `CDSW_APP_PORT`; do not set a fixed exposed port.
- [ ] Run `apps/backend/scripts/init_qdrant_collections.py` and verify all three collections.
- [ ] Validate Qdrant binary download from the target CAI runtime, or upload binary manually.
- [ ] Configure CDW Impala connection and change `DATA_MODE=impala`.
- [ ] Validate non-interactive CDW authentication and execute the CAI CV ingestion Job dry-run.
- [ ] Configure NiFi webhook/landing integration and change `INGEST_MODE=nifi` if required.
- [ ] Configure optional Langfuse credentials if enterprise LLM tracing is required.
- [ ] Replace demo candidate/policy data with customer-provided PoC data.
- [ ] Validate Ranger permissions for the service/user identities used by the PoC.

## Next implementation sequence

1. Validate backend Gemini health.
2. Validate frontend to backend proxy.
3. Run the sample importer, validate Qdrant, and index supplied policy chunks.
4. Validate Policy chat, citations, source download, feedback, and PDF export end-to-end.
5. Configure CDW and validate candidate query.
6. Validate Talent Intelligence end-to-end.
7. Connect NiFi/CDE pipeline.
8. Connect Cloudera Data Visualization dashboard URL.
9. Turn on optional Langfuse forwarding.
10. Execute demo rehearsal and freeze configuration.
