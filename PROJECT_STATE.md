# Project State

**State:** Backend feature-complete and validated live in CAI for CV/policy ingestion, Talent
Intelligence, Policy Intelligence (RAG + whitelisted data-query tool), Dashboard, Settings, and
governed Data Sources upload. Frontend QA pass in progress; CDV and NiFi/CDE connection still open.
**Target readiness:** 95% PoC-ready
**Primary runtime:** Cloudera AI Workbench Applications
**Last architectural decision:** Use custom CrewAI Flow backend as the main runtime, with Agent Studio retained only as a capability showcase.
**Last updated:** 2026-08-28, from `origin/main` @ `4f2cc86` (~35 commits since the previous update below).

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
- The CAI CV Job supports a governed `datalake` storage mode through Hadoop/S3A so IDBroker and
  Ranger remain authoritative. Direct `boto3` access is retained only as a local or explicitly
  scoped workload-role fallback.
- CV ingestion normalizes the final entity once before any sink write. An explicit extracted entity
  is preserved; when absent, identifiers such as `CAND-BNS-*` and `CAND-ENP-*` provide the
  deterministic fallback used by both Impala and Qdrant.
- Backend Impala connectivity uses the same configurable HTTP transport and `cliservice` path as
  the CAI ingestion Job, allowing CDW port 443 without embedding customer endpoints.
- A separate one-shot CAI policy ingestion Job is implemented at
  `jobs/policy_ingestion/run_cai_job.py`. It accepts PDF/DOCX/XLSX, uses governed S3A prefixes,
  writes policy metadata/audit to Iceberg, applies pre/post-index guardrails, and replaces stable
  chunks only in `QDRANT_POLICY_COLLECTION`. It remains a PoC fallback for NiFi/CDE, not a fifth
  Application.
- Dynamic policy metadata is served from `danantara.v_policy_documents_api` in Impala mode.
  Citation downloads use governed Hadoop/S3A access and do not expose source S3 URIs publicly.
- The Data Sources upload form can write directly to the governed S3A CV/policy landing prefixes
  (`UPLOAD_ACCESS_MODE=datalake`, `S3_CV_LANDING_URI`, `S3_POLICY_LANDING_URI`) via `hadoop fs -put`,
  the same governed-access pattern as the ingestion Jobs, instead of writing to the backend's local
  filesystem and indexing straight to Qdrant. Local mode remains the default and is unaffected.
- Policy Intelligence chat routes every question through two lightweight Gemini classifiers before
  the RAG flow: one for small talk/greetings (answered directly, no retrieval, no citations, no
  guardrail-mandated sources) and one for a small set of whitelisted structured data-query tools
  (`candidate_count`, `candidates_over_time`, `recruitment_stage_breakdown`,
  `open_positions_summary`) that Gemini can only select by ID, never by writing SQL — the chosen
  query still runs a hardcoded Impala query. Both fall through to the normal PolicyRAGFlow path if
  classification is inconclusive, so ordinary policy questions are unaffected.
- Guardrails now also block chat requests for an individual's personal contact/compensation details
  (email, phone, salary of a named person) in English and Indonesian, deliberately scoped to leave
  public salary-band/policy questions ("salary range for grade G3") allowed. This is a second layer
  on top of DataGateway already never selecting PII columns (email/phone/source_cv_s3_uri) into any
  query result.
- AI-generated chat/reasoning text is rendered through a small dependency-free markdown renderer
  (bold/italic/bullet/numbered lists -> HTML) instead of being shown as escaped plain text with raw
  `**`/`*` characters. The PDF export strips the same markdown tokens instead, since that renderer
  has no font styling to express emphasis with.
- Policy Intelligence's entity Source filters are optional, not required: an empty selection means
  "search every entity," matching what `PolicyRAGFlow.retrieve()` already did server-side. Requiring
  at least one checked entity was stricter than necessary and caused newly ingested documents whose
  entity isn't pre-checked by default to silently disappear from answers.

## Environment-specific tasks still required

- [x] Set `GEMINI_API_KEY` (confirmed live via successful embeddings/generation in CAI runs).
- [x] Create the four CAI Applications and capture their URLs (`danantara-qdrant`,
  `danantara-backend`, `danantara-frontend`, `danantara-observability` all running).
- [x] Set `BACKEND_BASE_URL` in frontend application variables (frontend successfully calls backend).
- [x] Set `QDRANT_BASE_URL`, shared Qdrant API key and the three collection variables (Qdrant
  health OK, policy/candidate collections indexed and queried live).
- [x] Set `OBSERVABILITY_BASE_URL` in backend Application variables (pipeline/guardrail events
  confirmed flowing in job/backend logs throughout this session).
- [x] Confirm each CAI Application receives `CDSW_APP_PORT`.
- [ ] Run `apps/backend/scripts/init_qdrant_collections.py` and verify all three collections
  (candidate/policy collections confirmed working via job runs; NiFi collection not yet exercised).
- [ ] Validate Qdrant binary download from the target CAI runtime, or upload binary manually.
- [x] Configure CDW Impala connection and change `DATA_MODE=impala` (confirmed live: dashboard,
  candidates, positions, recruitment pipeline all reading real Impala data).
- [x] Validate non-interactive CDW authentication and execute the CAI CV ingestion Job dry-run
  (CV job validated end-to-end previously; policy job re-validated again this session).
- [ ] Configure NiFi webhook/landing integration and change `INGEST_MODE=nifi` if required.
- [ ] Configure optional Langfuse credentials if enterprise LLM tracing is required.
- [ ] Replace demo candidate/policy data with customer-provided PoC data.
- [x] Create and synchronize the scoped Ranger/IDBroker mapping for CAI CV prefixes.
- [x] Validate the CAI CV dry-run through the governed S3A adapter.
- [x] Create/synchronize Ranger access for the four policy prefixes and validate policy Job schema
  init, single-file dry-run, real run, and Qdrant/Impala writes end-to-end in CAI.
- [x] Validate policy citation query (`/api/v1/policy/query`) and governed download against a real
  ingested document, including the backend's own Ranger/IDBroker read access.
- [x] Wire the Data Sources upload form to governed S3A landing prefixes
  (`UPLOAD_ACCESS_MODE=datalake`) so upload -> CAI Job -> Impala/Qdrant is one real, demoable loop.
  Validated live in CAI: uploaded PDF landed in `cv-collect/`/`policy-collect/`, CV ingestion Job
  picked it up, chunked/embedded/indexed it, and it was retrievable via Policy Intelligence chat.
- [x] Validate Talent Match end-to-end in CAI, including the ambiguous-title/multi-entity merge path
  and the keyword-boost scoring fix.
- [x] Validate the whitelisted Policy Intelligence data-query tool (candidate count, candidates by
  month, recruitment stage breakdown, open positions) live in CAI, including the inline chart.

- The Gemini policy embedding call (`GeminiEmbedder.embed`) sends chunks to `embed_content`
  individually instead of batching them in one `batchEmbedContents` call. Batching could return
  fewer embeddings than input chunks for multi-chunk documents, tripping the pipeline's
  `embedding_count_mismatch` guardrail and failing real ingestion runs. Per-chunk calls guarantee a
  1:1 vector-to-chunk mapping by construction (commit `f3574ae`).
- `POLICY_SOURCE_ACCESS_MODE=datalake` must be set on the `danantara-backend` Application itself
  (separate from the policy Job's `S3_ACCESS_MODE`), and the backend's own workload identity needs
  Ranger read access to `policy-processed/`/`policy-review/`, or citation downloads 404 with
  "Document source is unavailable" even though ingestion succeeded.
- `policy_query` previously returned a bare 500 with no detail on any internal failure. It now logs
  the traceback server-side and returns a 502 with `request_id` and the error message
  (commit `4e2a0b1`).
- `GET /dashboard/summary` now branches on `DATA_MODE`: in `impala` mode it reads recruitment-pipeline
  stage/status/match-score/salary-compliance rows from `danantara.v_recruitment_pipeline_api`
  (`IMPALA_RECRUITMENT_TABLE`), falling back to the demo `recruitment_status.json` fixture if the
  table is empty or unreachable. Schema is created by
  `apps/backend/scripts/init_dashboard_schema.py` (DDL in `dashboard_schema.sql`); no ingestion Job
  populates it yet — see `config/data-contracts.md`.

- `danantara.recruitment_pipeline` and `danantara.v_recruitment_pipeline_api` have been created in the
  target CDW/Impala database and seeded with 3 PoC rows (2026-08-27). `GET /dashboard/summary` has
  been validated live against real Impala data in CAI: correct stage/salary-compliance/match-score
  aggregation, 24 real candidates from `v_candidates_api`, no fallback to the demo fixture.
- Stray non-CV rows (filenames like `README.md`/`manifest.csv` with all other fields NULL) were found
  in `danantara.candidate_master` and manually deleted; not caused by the CV ingestion job, which has
  always filtered to `.pdf` only. `_impala_candidates`/`_impala_positions` now skip (and log) any row
  with a missing required field instead of crashing the whole dashboard endpoint (commit `9b26d26`).
- Cloudera Data Visualization is intended to read the same governed views (`v_recruitment_pipeline_api`,
  `v_candidates_api`, `curated_job_positions`) as the in-app dashboard — one shared source of truth,
  no separate CDV-only schema. Deferred until frontend QA below is complete.
- Talent Intelligence QA in CAI found two issues, both fixed and later re-validated live: (1) the
  free-text "Skills / Keywords" box was merged verbatim into `position.required_skills`, so any
  keyword phrase always showed as a false "Skill Gap" and inflated the scoring denominator,
  mechanically lowering every match score — keywords are now a separate substring-matched boost (up
  to 10 pts) that never touches required/matched/gap skills. (2) Two distinct positions sharing a
  title (e.g. "Senior Data Engineer" for both BNS and ENP) looked like a duplicate in the position
  dropdown — the dropdown now dedups by title, and picking an ambiguous title with no entity filter
  merges results by scoring each candidate against their own entity's position variant, rather than
  blocking the request or picking one arbitrarily (commit `b6738a5`; a follow-up fix in `ca4392c`
  resolved a bare-500 response-shape bug this merge path introduced).
- Settings page was simplified to three live/actionable cards (Runtime Configuration, Security &
  Monitoring, Data Pipeline); removed three pieces of dead UI (category tabs, "Access & Roles",
  "PoC Display Preferences") that didn't actually filter or persist anything.
- Dashboard page's "PoC Sample Data" badge and "Open in Cloudera Data Visualization" button were
  removed (CDV isn't configured yet, so the button always errored); will return once CDV is wired up.

## Next implementation sequence

1. Finish the frontend QA pass: Overview and Sources pages haven't had a dedicated live-data pass
   yet this session (Talent, Policy, Dashboard, Data Sources, and Settings all have).
2. Connect NiFi/CDE pipeline and hand off the policy ingestion Job's data contract to that team.
3. Connect Cloudera Data Visualization: build a CDV dashboard against the shared governed views
   (`v_recruitment_pipeline_api`, `v_candidates_api`, `curated_job_positions` — spec already drafted
   this session), then set `CDV_DASHBOARD_URL` on the frontend Application and restore the Dashboard
   page's "Open in CDV" entry point.
4. Turn on optional Langfuse forwarding.
5. Consider populating `candidate_master.proficiency_score` from CV extraction (currently always
   NULL in real data, so the candidate detail modal always shows "Proficiency not assessed" — not a
   bug, just unimplemented in the CV ingestion Job's extraction prompt).
6. Execute full regression rehearsal and freeze configuration.
