## Why

WB Sky needs a transport-independent semantic layer linking **why** a change was
considered, **what** was preregistered in an experiment protocol, and **how**
outcomes should be interpreted — without becoming settings, ChangeSet, dry-run,
Apply, metric, or attribution authority.

## What Changes

### Historical → delivered

**Planning era (2026-10-07):** this change introduced OpenSpec artifacts only.

**Delivered on `stage` (2026-10-09, PR #460):** **Slice A domain foundation**
in `app/modules/decision_experiment_memory/` — types, ports, projection vocabulary,
test-only in-memory fake, unit tests.

**Owner scope Option A:** archive closes this change at foundation; persistence,
ingest, evaluator, and AI export become **separate future changes** (see
`openspec/evolution/decision-experiment-memory-future-boundaries.md`).

## Scope

**Delivered:** domain foundation (Slice A) per `FOUNDATION_CERTIFICATION.md`.

**Not delivered:** PostgreSQL persistence, Apply/exposure ingest, deterministic
evaluator runtime, post-hoc persistence, AI Package `decision_memory_v1`, MCP/REST.

## Current Behavior (post-merge)

- Apply Authority PG-only V1 and `DryRunReceiptV1` / `ApplyEvidenceV1` exist on `stage`.
- Decision memory stores **refs only** (`ApplyEvidenceRef`, `DryRunReceiptRef`, …).
- Attribution-facts module exists separately; memory uses optional `AttributionFactSetRef` vocabulary.

## Desired Behavior (foundation)

- Canonical identities, plan immutability, exposure/apply projection invariants, validity
  vocabulary, factual vs interpretation boundary, post-hoc vocabulary, intervention signature.
- Production persistence and runtime evaluation deferred to future changes.
