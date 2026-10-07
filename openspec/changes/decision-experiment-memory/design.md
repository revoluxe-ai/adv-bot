## Context

Planning-only change. Reuse `ChangeSetV1` metadata hooks (`decision_id`,
`experiment_id` distinct). Memory module absent on `origin/stage`. Apply audit
tables planned in `changeset-apply-authority` (store + future change) — **not**
a dependency for Slice A domain vocabulary.

## Goals / Non-Goals

**Goals:**

- Canonical domain types: `DecisionMemoryRecord`, `ExperimentRecordV1`,
  `ExperimentPlanV1`, refs (`ApplyEvidenceRef`, settings/attribution/package refs).
- Plan registration/freeze, protocol deviations, execution_state vs outcome.
- Reader ports (transport-independent); revised implementation slices A–E.

**Non-Goals:**

- PostgreSQL in Slice A; WB/CH/PG writes; MCP; promoting ADR to accepted registry
  in this planning PR.

## Architecture Decision References

- `openspec/decisions/campaign-settings-contract-ownership/decision.md` — settings
  SoT; evidence via `state_hash` / registry.
- `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` — Slice E
  read-only export boundary.
- `openspec/changes/archive/2026-10-07-campaign-settings-changeset-contract/` —
  ChangeSetV1 + dry-run ownership.
- `openspec/changes/archive/2026-10-05-campaign-settings-history/` — history grain.
- **Proposed (not promoted):**
  `openspec/changes/decision-experiment-memory/decisions/decision-experiment-memory-ownership/decision.md`

## Ownership & Placement

| Layer | Owner |
|-------|--------|
| Decision/experiment domain, events vocabulary, reader port | `app/modules/decision_experiment_memory/` |
| PG event store + projections (Slice B) | same module `persistence/` |
| Ingest adapters ChangeSet/dry-run/apply/history (Slice C) | `decision_experiment_memory/ingest/` |
| Deterministic evaluator (Slice D) | `decision_experiment_memory/evaluation/` |
| AI Package datasets (Slice E) | `app/modules/ai_package_v1/decision_memory/` |

**Forbidden:** `campaign_settings_history` (link only), `wb_sky_control_plane` as
memory owner, `shop_runner`, any production writer.

Checklist:

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] new decision proposed (status Proposed, not promoted)
- [x] implementation layer matches proposed decision

---

## Identity model

| Entity | Primary key | Links |
|--------|-------------|--------|
| `DecisionMemoryRecord` | `decision_id` | optional many `experiment_id` via FK on experiment |
| `ExperimentRecordV1` | `experiment_id` | required `decision_id` (parent decision semantics) |

**DECISION_EXPERIMENT_CARDINALITY:** Decision 1 → 0..N Experiments.

**V1_CARDINALITY_RESTRICTION:** Creation API **MAY** reject a second experiment
for the same `decision_id` with `EXPERIMENT_LIMIT_V1` until multi-experiment UX
exists; storage schema and reader contracts **MUST** allow multiple rows per
`decision_id`.

**MUST NOT:** `experiment_id = decision_id` as domain invariant or default merge.

---

## EXPERIMENT_DESIGN_MODEL

How evidence is produced (causal / observational design):

| `experiment_design` | Meaning |
|---------------------|---------|
| `RANDOMIZED_AB` | Randomized assignment when platform supports it |
| `SWITCHBACK` | Alternating windows / legs |
| `CONTROLLED_BEFORE_AFTER` | Controlled pre/post with explicit control arm definition |
| `BEFORE_AFTER_OBSERVATIONAL` | Observational pre/post without randomized control |

---

## TREATMENT_MODE_MODEL

Whether production settings are mutated:

| `treatment_mode` | Meaning |
|------------------|---------|
| `LIVE` | Intended production intervention; `effective_from` requires `ApplyEvidenceRef` BOUND |
| `SHADOW` | Counterfactual / dry observation; no LIVE exposure claims |

**MUST NOT** encode `SHADOW` under `experiment_design`.

---

## EXPERIMENT_PLAN_MODEL (`ExperimentPlanV1`)

Embedded in `ExperimentRecordV1` but typed separately for freeze semantics:

- `registered_at`, hypothesis (non-identity text)
- `primary_metric_ids[]`, `secondary_metric_ids[]`, `guardrail_metric_ids[]`
- `baseline_window`, `observation_window`, `burn_in`, `burn_out`, `timezone`
- `minimum_effect_of_interest`, `success_criteria[]`, `failure_criteria[]`
- `stopping_rule`, `analysis_method` (+ version)

**intervention_signature:** stable hash of `intervention_class` + normalized intent
(op kinds/target fields/direction) — not hypothesis text.

---

## PLAN_FREEZE_MODEL

- Event `PLAN_REGISTERED` binds `(experiment_id, plan_revision, plan_digest)`.
- `plan_digest = hash(canonical_json(ExperimentPlanV1 without revision fields))`.
- After register: plan fields for that revision are immutable; change →
  `PLAN_AMENDED` → `plan_revision++` → new digest.
- `protocol_deviations[]` append-only coded events (`ProtocolDeviationV1`).

---

## EXECUTION_STATE_MODEL (experiment)

Orthogonal to **outcome**. Suggested enum:

`PLANNED` → `PREREGISTERED` → `INTERVENTION_BOUND` → `EXPOSURE_PENDING` →
`OBSERVING` → `EVALUATION_DUE` → `EVALUATED` | `TERMINATED`

**Decision execution_state** (lighter): `DRAFT` → `READY` → `CHANGESET_LINKED` →
`DRY_RUN_RECORDED` → `APPLY_CONFIRMED` (only with BOUND Apply ref) → `CLOSED`.

**Invariants (examples MUST hold):**

- `(execution_state=EVALUATED, outcome=INVALID)` — valid (evaluated but invalid protocol/data).
- `(execution_state=EVALUATED, outcome=INCONCLUSIVE)` — valid.
- `(execution_state=OBSERVING, outcome=SUCCEEDED)` — **invalid** (premature outcome).
- `treatment_mode=LIVE` + `EXPOSURE_PENDING` without BOUND Apply → cannot enter
  `OBSERVING` with LIVE exposure claim.

---

## OUTCOME_MODEL

`SUCCEEDED` | `FAILED` | `INCONCLUSIVE` | `INVALID` | `ABORTED` | (`NOT_APPLICABLE`
for decision-only).

Derived deterministically from criteria + validity; AI narrative non-authoritative.

---

## VALIDITY_MODEL

`validity_status`: `VALID` | `DEGRADED` | `INVALID` + `validity_reason_codes[]`.
`INVALID` validity forces experiment `outcome=INVALID` (not FAILED).

---

## APPLY_EVIDENCE_ABSTRACTION

```text
ApplyEvidenceRefV1:
  authority: "changeset_apply_audit"   # extensible string, no payload here
  apply_receipt_id: str | null        # opaque when bound
  evidence_digest: str | null         # optional stable digest when known
  binding_status: UNBOUND | BOUND | STALE
```

**Without BOUND authoritative Apply evidence:**

- Decision **MUST NOT** reach `APPLY_CONFIRMED`.
- Experiment **MUST NOT** set factual LIVE `effective_from` from Apply.
- Experiment **MUST NOT** claim valid LIVE exposure.

Slice C binds concrete receipt type when Apply Authority lands; Slice A defines
ref + invariants only.

**SLICE_A_BLOCKED_BY_APPLY:** **NO**

---

## OWNERSHIP_BOUNDARY (ADR summary)

**OWNS:** decision semantics; preregistered experiment plan; experiment lifecycle
semantics; validity/evaluation semantics; result history; interpretation/provenance
linkage (refs only).

**DOES NOT OWN:** campaign settings truth; catalog truth; Apply execution truth;
metric source truth; attribution truth — immutable refs/digests only.

---

## REVISED_IMPLEMENTATION_SLICES

| Slice | Scope |
|-------|--------|
| **A** | Pure domain + `ExperimentPlanV1` + ports + invariants + unit tests (**no PG**) |
| **B** | PostgreSQL append event store + projections + repository |
| **C** | ChangeSet / dry-run / Apply / settings-history linkage ingest |
| **D** | Deterministic evaluator + validity + outcomes + late metrics + corrections |
| **E** | AI Package / MCP read exposure (transport adapter out of scope) |

---

## Derived lifecycle (scenario coverage)

- L1 Decision record created (semantics, evidence refs)
- L2 Experiment plan registered / frozen
- L3 Intervention bound (ChangeSet digest) without Apply
- L4 Apply evidence bound (LIVE) or SHADOW observe path
- L5 Evaluation window complete → EVALUATED + outcome
- L6 Correction / supersede / follow-up experiment (new `experiment_id`)
