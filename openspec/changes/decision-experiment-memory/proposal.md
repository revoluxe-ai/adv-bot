## Why

WB Sky must remember **why** a control decision was made and **what happened**
afterward, separate from settings history, Apply execution audit, and attribution
facts. AI-first clients (ChatGPT, API, MCP) need transport-independent memory of
decision semantics, preregistered experiments, validity, and factual outcomes.

`ChangeSetMetadataV1` already carries distinct `decision_id` and `experiment_id`
(`app/modules/wb_sky_control_plane/models/changeset.py`). There is no durable
decision/experiment memory module yet.

## What Changes

- Introduce canonical **DecisionMemoryRecord** and **ExperimentRecordV1** with
  independent identities (`decision_id` ≠ `experiment_id` invariant forbidden).
- **ExperimentPlanV1** with `plan_revision`, `plan_digest`, registration/freeze,
  protocol deviations — domain Slice A (pure types + invariants + tests, no PG).
- Separate **experiment_design** (how evidence is produced) from **treatment_mode**
  (whether production is mutated: LIVE vs SHADOW).
- Optional **ApplyEvidenceRef** abstraction — Slice A MUST NOT depend on Apply
  Authority implementation landing.
- Two-axis model: **execution_state** orthogonal to **outcome**.
- PostgreSQL event store deferred to Slice B; linkage to ChangeSet/Apply/history in
  Slice C; evaluator in Slice D; AI Package read exposure in Slice E.

## Capabilities

### New Capabilities

- `decision-experiment-memory` — decision semantics, experiment plan freeze,
  validity/evaluation vocabulary, result history, read port (planning + phased impl).

### Modified Capabilities

- None on `origin/stage` baseline (planning change only).

## Impact

- New module `app/modules/decision_experiment_memory/` (after ADR acceptance).
- AI Package optional datasets in Slice E (`READ_ONLY_NO_MUTATION`).
- Does not change Apply Authority, campaign settings SoT, or shop-runner writes.

## Out of Scope (this change planning)

- Production writes, migrations, MCP transport, durable Apply/dry-run tables (Slice C
  consumes them when `changeset-apply-authority` lands).
- Promoting ownership ADR to `openspec/decisions/` before Owner Contract Review GO.
