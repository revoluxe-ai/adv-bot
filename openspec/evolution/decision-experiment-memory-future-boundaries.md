# Future boundaries — decision-experiment-memory (non-normative)

Owner scope **Option A** closed `decision-experiment-memory` at **domain foundation
(Slice A only)** on `stage` (PR #460). The following are **separate future OpenSpec
changes** — not delivered by the archived foundation implementation.

## A. decision-memory-persistence (concept)

- PostgreSQL append-only event log + projections
- Alembic migration; immutable plan revision rows
- Idempotency indexes (`apply_evidence_id`, `evaluation_run_digest`, `event_id`)
- **No** `UNIQUE(decision_id)` enforcing 1:1 experiments
- Projection rebuild from events (if event-sourced model retained)
- EVIDENCE_GAP: retention, concurrency, correction-event PG shape

## B. decision-memory-exposure-ingest (concept)

- `TREATMENT_INTENDED` / `CHANGESET_LINKED` / `APPLY_LINKED` / `EXPOSURE_CONFIRMED` ingest
- `ApplyEvidenceRef` + settings-state confirmation → `effective_from`, `observation_start`
- No authoritative payload duplication

## C. decision-memory-evaluator (concept)

- Deterministic evaluator runtime; `FactualResult` persistence
- Validity gates; source completeness; attribution refs; confounder ingest integration
- Scenarios **S12–S13**, **S20–S22** (evaluator-owned)

## D. decision-memory-posthoc (concept)

- Post-hoc / interpretation persistence runtime beyond vocabulary types

## E. decision-memory-ai-package (concept)

- `decision_memory_v1` export block (`recent_decisions`, `active_experiments`, …)
- Read-only via `DecisionMemoryReader`; no mutation authority

## PG design constraints (read-only, non-binding)

- PK: `decision_id`, `experiment_id`; `experiment.decision_id` FK, not unique parent
- Plan revisions: `(experiment_id, plan_revision)` immutable
- Interpretation append-only; factual results not overwritten by interpretation
