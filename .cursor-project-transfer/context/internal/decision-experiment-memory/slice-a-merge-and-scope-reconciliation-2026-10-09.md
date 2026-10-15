---
cursor:
  subagentId: "bc-929904d1-8a63-559a-8bd2-0d59b664eb40"
---

# decision-experiment-memory — Slice A merge + scope reconciliation

## Merge

- PR: #460 (MERGED)
- Branch HEAD pre-merge: `20248943cee6e785e4554ddad23ba6c0cd224144`
- Merge commit on `stage`: `5c2e15a5805d2a048fd339b173f19c249d3a3353`
- Post-merge `origin/stage`: `5c2e15a5805d2a048fd339b173f19c249d3a3353`
- Post-merge verify: 50/50 `tests/unit/decision_experiment_memory/` on `stage`

## Vocabulary repairs (pre-merge)

- `DryRunReceiptRef` ≠ `ApplyEvidenceRef` (`EvaluationProvenance`, `DecisionMemoryRecord`)
- `PostHocAnalysisRecord`: `analysis_kind`, `exploratory_metrics`
- Apply Authority V1 prose updated (no “future gap” for PG ledger)

## Slice B read-only inventory (no migration)

| Area | Notes |
|------|--------|
| Event tables | Append-only `MemoryEvent` persistence; type + payload JSON/refs |
| Plan revisions | Immutable rows keyed `(experiment_id, plan_revision)` + `plan_digest` |
| Projections | `DecisionMemoryRecord`, `ExperimentRecordV1`, factual results, index |
| Idempotency | Unique on `apply_evidence_id`, `evaluation_run_digest`, event `event_id` |
| Cardinality | **No** `UNIQUE(decision_id)` on experiments — 1:N |
| Alembic head | `f9c0a1b2d3e4` (apply authority ledger); demem tables **not** present |
| EVIDENCE_GAP | Retention policy, projection rebuild cadence, correction event PG shape |

## Scope options (Owner gate)

**OPTION A — foundation change ends at Slice A**

- Pros: Clear archive boundary; Slice B = new change + migration Owner GO
- Cons: Active change `decision-experiment-memory` still lists B–F tasks

**OPTION B — continue same change**

- Pros: Single lifecycle for spec/tasks; slices already numbered
- Cons: Mixes merged Slice A with unimplemented persistence; archive only after F

**Recommendation:** **OPTION B** for task/spec continuity, but **separate Owner GO** (and likely OPSX hop) before any Slice B Alembic revision — same pattern as apply-authority / attribution-facts.

## Change status

- `decision-experiment-memory` remains **ACTIVE** (not archived)
- Tasks 3–7 open; 2.x complete; 1.6 planning-review receipt still not materialized
