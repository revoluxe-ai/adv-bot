# decision-experiment-memory — planning

**Status:** `READY_FOR_OWNER_CONTRACT_REVIEW` · **IMPLEMENTATION_READY:** false  
**FINAL_STATUS:** `ARCHITECTURE_DECISION_REQUIRED` until Owner accepts proposed ADR (not promoted yet)

Planning only — no migrations, production writes, or deploy.

## Purpose

Canonical WB Sky memory of **decision semantics** (why / hypothesis / expected effect) and **factual experiment outcomes**, transport-independent. Separate from:

| System | Authority |
|--------|-----------|
| `campaign-settings-history` | **Settings** timeline (`snapshot_id`, `state_hash`) |
| ChangeSet Apply audit | **Execution** (`changeset_apply_*`, dry-run receipts) |
| `attribution-facts-contract` | **Economics facts** (read-only evidence) |
| AI Package DRR / analysis metrics | **Derived analytics** — not decision SoT |

A decision record **never** grants production write permission; Apply Authority remains sole write gate.

## Domain (V1)

- **`DecisionMemoryRecord`** (`decision_id`) + **`ExperimentRecordV1`** (`experiment_id`, `decision_id`) — **independent ids**, Decision 1→0..N Experiments; V1 API may cap at one create per decision.
- **`experiment_design`** ⊥ **`treatment_mode`** (`LIVE` | `SHADOW`); **`ApplyEvidenceRef`** in Slice A without Apply payload.
- Slices **A–E** (domain first, no PG in A). OpenSpec: `openspec/changes/decision-experiment-memory/`.
- Settings before/after: **`SettingsSnapshotRef`** only (`snapshot_id`, `state_hash`) — not full payloads.
- Append-only events (`PLAN_REGISTERED`, `VALIDITY_ASSESSED`, …) + projections; no silent overwrite of frozen plan or outcomes.

## Dependencies

| Blocker | Why |
|---------|-----|
| ADR `decision-experiment-memory-ownership` | Module placement under `app/modules/decision_experiment_memory/` |
| `changeset-apply-authority` + durable dry-run receipts | `APPLY_RECORDED` / `dry_run_receipt_digest` evidence |
| OpenSpec scaffold in repo | `proposal` / `design` / `spec` / `tasks` (not yet created) |

## Slices

| Slice | Scope |
|-------|--------|
| **A** | Domain, PG event store, projection, reader port, unit tests |
| **B** | ChangeSet / dry-run / Apply audit ingest + idempotency |
| **C** | Evaluation windows, deterministic outcomes, late metrics, corrections |
| **D** | AI Package datasets (`recent_decisions`, `active_experiments`, `experiment_results`) |

## Normative detail

Full inventory, lifecycle, idempotency, reader port, and risk register:

[internal/decision-experiment-memory/planning-report-bc-0395eb9d.md](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/decision-experiment-memory/planning-report-bc-0395eb9d.md) (latest verification); prior: [planning-report-bc-2bbf6418.md](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/internal/decision-experiment-memory/planning-report-bc-2bbf6418.md)

Related: [changeset-apply-authority planning](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-apply-authority-planning.md).
