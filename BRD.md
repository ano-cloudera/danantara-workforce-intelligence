# Business Requirements Document (BRD)

## 1. Business context

Danantara requires a Unified Data Platform PoC that can ingest structured and unstructured workforce data, organize it into a governed lakehouse, provide analytics/reporting, and enable AI-driven use cases such as talent matching, policy comparison, summarization and RAG-based question answering.

## 2. Business objective

Show that one governed enterprise data foundation can serve both conventional management analytics and AI-driven workforce intelligence without creating disconnected data silos.

## 3. Business capabilities

### BR-01 Candidate intake
The solution shall accept candidate registration information and CV documents and make the processed data available for downstream analysis.

### BR-02 Workforce data foundation
The solution shall maintain raw and curated workforce data in open lakehouse tables and expose business-ready data through governed SQL.

### BR-03 Talent intelligence
An HR analyst shall be able to select a position and receive ranked candidate recommendations, match scores, matched skills, skill gaps and explainable reasoning.

### BR-04 Policy intelligence
An HR user shall be able to ask questions and compare policies across entities, receiving grounded answers with source references.

### BR-05 Management monitoring
Management shall be able to monitor candidate counts, recruitment activity, skill distribution and related KPIs using Cloudera Data Visualization.

### BR-06 Governance
All enterprise data access shall remain subject to Cloudera governance and authorization policies. AI responses shall expose source context where available and identify AI-generated recommendations as requiring human review.

### BR-07 Safety and monitoring
The custom AI application shall validate input/output, capture workflow telemetry and provide a mechanism for user feedback and human review.

## 4. Out of scope for this PoC

- Full enterprise MDM implementation.
- Production-grade identity lifecycle inside the custom app; CAI/enterprise SSO is preferred.
- Production HR decision automation without human review.
- Full privacy-preserving clean room.
- Production multi-region HA for Qdrant or SQLite.

## 5. Success criteria

- Demonstrate candidate matching from governed candidate data.
- Demonstrate policy RAG with citations.
- Demonstrate management analytics from curated data.
- Demonstrate configurable Gemini model and embedding calls from Cloudera AI.
- Demonstrate application tracing and guardrail results.
- Demonstrate that enterprise data remains in Iceberg/CDW rather than SQLite.
