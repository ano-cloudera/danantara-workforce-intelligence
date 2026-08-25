---
name: delivery-method-selector
description: Select direct implementation, lightweight spec-kit planning, or the full BMAD artifact chain before project changes. Use for feature, fix, refactor, configuration, documentation, architecture, or delivery-planning requests in this repository.
---

# Delivery Method Selector

Choose the least heavyweight method that preserves correctness and shared context. Do not route a
change through BMAD merely because this repository contains BMAD artifacts or an existing story.

## Direct implementation

Use direct implementation for bounded, low-risk work with an obvious solution and verification:

- bug fixes, tests, refactors, dependency maintenance, documentation, and local configuration;
- changes contained within an existing contract or locked architecture decision;
- reversible edits that do not introduce a new business capability or cross-system workflow.

Inspect the relevant code and docs, implement, test, and report. Do not create or update BMAD
planning artifacts unless the work reveals a material decision that changes their truth.

## Lightweight spec-kit

Use a lightweight spec for a medium-sized feature when acceptance criteria and a short technical
plan improve coordination, but business discovery and architecture redesign are unnecessary:

- a bounded user-facing capability spanning several files or one Application boundary;
- an API or data-contract extension compatible with the current architecture;
- work with meaningful edge cases, rollout steps, or test scenarios but a clear product intent.

Capture scope, non-goals, acceptance criteria, implementation plan, and verification in the
repository's available spec-kit mechanism. If no spec-kit scaffold exists, keep the spec concise in
the implementation plan or a task-specific `specs/<slug>.md`; do not invent a full framework.

## Full BMAD

Use BMAD when the request requires business and architecture alignment across substantial scope:

- a new business capability, persona, or end-to-end journey;
- reopening a locked decision, changing the four-Application topology, or replacing a core
  provider/orchestration/data-system role;
- cross-platform changes involving several of CAI, NiFi, CDE, CDW, governance, and Qdrant;
- material security, governance, system-of-record, or human-decision policy changes;
- ambiguous requirements that require BRD/PRD/architecture/epic/story decomposition.

Read and update only the BMAD artifacts affected by the decision. Preserve the artifact chain and
record material decisions in `PROJECT_STATE.md` and `_bmad/project-state.yaml`.

## Routing rules

1. Honor an explicit user request for BMAD or spec-kit unless it conflicts with repository safety.
2. When uncertain between adjacent levels, start with the lighter method and escalate only when a
   concrete scope, risk, contract, or decision boundary requires it.
3. Existing BMAD stories are context, not mandatory process gates. Read a story when using BMAD or
   when the task explicitly changes that story's acceptance criteria.
4. A direct or spec-kit change may update factual documentation without converting the task into
   BMAD. Update BMAD state only when its recorded architecture or delivery status would otherwise
   become inaccurate.
5. State the selected method briefly before implementation when the choice affects the workflow.
