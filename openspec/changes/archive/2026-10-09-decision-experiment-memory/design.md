## Foundation archive scope

**DELIVERED:** Slice A domain module + tests only (`app/modules/decision_experiment_memory/`).
**NOT DELIVERED:** slices B–F (see `openspec/evolution/decision-experiment-memory-future-boundaries.md`).
**OWNER_SCOPE:** Option A foundation-only; this change archives after merge.

## Context

WB Sky separates **settings facts**, **ChangeSet dry-run**, and **Apply Authority**
(PG-only V1 on `stage`). Decision-experiment memory is the **AI-readable semantic layer**:
WHY / EXPECT / OUTCOME / validity / causal design — never production write authority.

**Methodology addendum (planning repair):** experiments require a frozen
**ExperimentPlan**, orthogonal **execution_state** vs **outcome**, explicit
exposure anchoring, versioned metrics, data validity gates, factual vs interpretive
results, and structured retrieval (`experiment_memory_index`).

### Related architecture (not overridden)

| Authority | Role |
|-----------|------|
| `campaign-settings-history` | WHAT settings existed / changed (`state_token`, snapshots) |
| Apply Authority (`changeset-apply-authority`, archived) | Execution truth (`ApplyEvidenceV1`); memory holds `ApplyEvidenceRef` only |
| Dry-run receipt store (Apply Authority) | Validation truth (`DryRunReceiptV1`); memory holds `DryRunReceiptRef` only |
| `attribution-facts-contract` (in flight) | Authoritative attribution fact refs (see dependency section) |
| A/B Hold ADLs | Product hold experiment execution; memory may reference only |

### Repository evidence (updated)

- `ChangeSetMetadataV1`: optional `decision_id` / `experiment_id` (non-semantic).
- Dry-run: `DryRunResultV1` (control plane) + durable `DryRunReceiptV1` (Apply Authority PG).
- Apply execution: `ApplyEvidenceV1` / `ApplyEvidenceRef` in memory (no payload copy).
- **`attribution-facts-contract`**: separate module on `stage`; optional
  `AttributionFactSetRef` for later evaluator slices — not required for Slice A vocabulary.

## Goals / Non-Goals

**Goals:** first-class `ExperimentPlan`, dual state machines, exposure model,
design-type semantics, validity model, intervention signature, provenance,
post-hoc boundary, strengthened AI read model.

**Non-Goals:** switchback engine, sequential testing engine, PG migrations in
planning, ADL promotion, attribution-facts implementation, vector DB (optional
secondary retrieval only).

## Architecture Decision References

- `campaign-settings-contract-ownership`, `ai-package-v1-exporter-ownership`,
  `shop-data-source-strategy`
- `openspec/decisions/decision-experiment-memory-ownership/decision.md` (Accepted)

## Ownership & Placement

| Concern | Owner | Memory layer |
|---------|-------|----------------|
| Settings snapshots | `campaign_settings_history` | Ref only |
| ChangeSet body | `wb_sky_control_plane` | `changeset_id` + semantic digest |
| Apply truth | Apply Authority | `ApplyEvidenceRef` (id + optional digest; no payload) |
| Attribution facts | `attribution-facts-contract` (future) | `attribution_fact_set_ref` optional |
| Experiment plan & outcomes | **decision-experiment-memory** | ExperimentPlan + evaluations |

Checklist: context-first lookup done; proposed ADL cited; implementation deferred.

---

## Architecture locks (final contract repair)

### IDENTITY_MODEL

| Aggregate | Primary key | Parent |
|-----------|-------------|--------|
| **DecisionMemoryRecord** | `decision_id` | — |
| **ExperimentRecordV1** | `experiment_id` | `decision_id` (required FK) |

- `decision_id` and `experiment_id` are **independent** opaque ids.
- **`experiment_id = decision_id` MUST NOT** be a domain invariant, default, or
  encoding shortcut.
- `ChangeSetMetadataV1` may carry both ids; either may be present without implying
  equality.

Planning prose may say `DecisionRecord` / `ExperimentRecord`; canonical identity
names above are normative for contracts and persistence.

### DECISION_EXPERIMENT_CARDINALITY

- **Domain:** one `DecisionMemoryRecord` → **0..N** `ExperimentRecordV1`.
- Each experiment references exactly one decision; a decision MAY have zero experiments.

### V1_CARDINALITY_RESTRICTION

- **V1 product/API MAY restrict creation** to **0..1** experiment per decision for
  implementation simplicity.
- Domain types, event envelopes, reader shapes, and future PG schema MUST remain
  **1:N compatible** (no unique constraint implying 1:1 at the contract level).

### EXPERIMENT_DESIGN_MODEL (`experiment_design`)

Causal / statistical design only (unchanged):

`RANDOMIZED_AB` | `SWITCHBACK` | `CONTROLLED_BEFORE_AFTER` |
`BEFORE_AFTER_OBSERVATIONAL`

Drives `evidence_design` and `causal_evidence_level`. **Not** production apply mode.

### TREATMENT_MODE_MODEL (`treatment_mode`)

Separate axis on `ExperimentRecordV1` / plan:

| Value | Meaning |
|-------|---------|
| `LIVE` | Intended production treatment (requires apply + exposure evidence for confirmed exposure) |
| `SHADOW` | Counterfactual / dry-run / non-applied observation path; no production mutation claim |

SHADOW is **not** an `experiment_design` and does not change causal evidence level by itself.

### APPLY_EVIDENCE_ABSTRACTION

Apply Authority receipt payload **does not exist** in repo yet. Slice A defines only:

```text
ApplyEvidenceRef (alias ApplyReceiptRef)
  apply_evidence_id: str          # opaque id from future authority
  evidence_digest: str | None     # optional until authority publishes digest rules
  authority_kind: "APPLY_AUTHORITY"  # versioned literal for forward compat
```

No receipt body fields in decision-memory domain. Linkage events MAY carry `ApplyEvidenceRef`
when ingested later.

**Invariants**

- No `ApplyEvidenceRef` → decision MUST NOT claim `APPLY_CONFIRMED`; experiment MUST NOT
  treat production apply as proven.
- No authoritative effective-state evidence → MUST NOT confirm **LIVE** exposure /
  `OBSERVING` as valid production evidence.
- **`treatment_effective_from` MUST NOT be guessed** (inferred only from linked evidence
  or remain unset / validity `UNKNOWN`).

### SLICE_A_BLOCKED_BY_APPLY

**`SLICE_A_BLOCKED_BY_APPLY = NO`**

Slice A uses `ApplyEvidenceRef` / `DryRunReceiptRef` types and invariants only. Concrete Apply
integration is Slice C+; vocabulary and unit tests do not require Apply Authority.

### SLICE_A_BOUNDARY

Slice A is **domain-first**:

| In Slice A | Out of Slice A |
|------------|----------------|
| Pure domain vocabulary + invariants | PostgreSQL, migrations |
| Reader / repository **protocols** | Apply ingest integration |
| **Test-only** in-memory fake implementing protocols | Evaluator runtime |
| Unit tests against fake | AI Package / MCP |

### SLICE_A_IN_MEMORY_MEANING

“In-memory event store” in Slice A means a **testing fake** (e.g. `InMemoryDecisionMemoryRepository`)
for unit tests — not a production persistence tier, not durable across processes.

---

## Domain aggregates

### DecisionMemoryRecord (`DecisionRecord` in narrative)

Actor, scope, semantics (observation, rationale, intended action), evidence refs,
**decision-level** ChangeSet/dry-run/`ApplyEvidenceRef` linkage, `decision_fingerprint`
(coarse intent class — **not** experiment similarity).

A decision MAY exist without any experiment.

Decision status (proposal track, separate from experiment execution):

`RECORDED` | `VALIDATED` | `REJECTED` | `APPLY_CONFIRMED` | `APPLY_FAILED` |
`WITHDRAWN` | `SUPERSEDED`

### ExperimentRecordV1 (experiment shell)

Independent `experiment_id`; required `decision_id` parent. Holds:

- `treatment_mode`: `LIVE` | `SHADOW`
- `execution_state` (orthogonal machine)
- `outcome` (orthogonal machine)
- `active_plan_revision` + `frozen_plan_digest` (after freeze)
- `registration_kind`: `PREREGISTERED_CONFIRMATORY` | `POST_HOC_EXPLORATORY`
- `evidence_design` + `causal_evidence_level` (derived from plan design type)
- `intervention_signature` (deterministic; see below)
- `exposure` sub-model (assignment / apply / observation anchors)
- Latest `data_validity` projection
- Refs to `FactualResult` and optional `Interpretation` records (by id)

**Invariant:** `ExperimentRecord` MUST NOT exist without at least one registered
`ExperimentPlan` revision.

### ExperimentPlan (immutable first-class object)

Not embedded as a replaceable `evaluation_contract` blob. Each revision is an
immutable value object/event payload:

| Field | Notes |
|-------|--------|
| `experiment_id` | Parent |
| `plan_revision` | Monotonic int, starts at 1 |
| `plan_digest` | `sha256(canonical_json(plan_body))` |
| `registered_at` | Timestamp |
| `registration_kind` | PREREGISTERED_CONFIRMATORY / POST_HOC_EXPLORATORY |
| `hypothesis` | Structured + optional narrative |
| `treatment_definition` | Normalized intended change semantics |
| `control_definition` | Explicit counterfactual (see below) |
| `experiment_design` | Enum (see EXPERIMENT_DESIGN_MODEL) |
| `treatment_mode` | `LIVE` \| `SHADOW` (orthogonal to design) |
| `primary_metrics[]` | Versioned metric defs |
| `secondary_metrics[]` | Optional |
| `guardrail_metrics[]` | Optional |
| `window_model` | Baseline, observation, burn-in/out, cutoff, timezone |
| `minimum_meaningful_effect` | Optional structured threshold |
| `success_criteria` | Deterministic predicate tree |
| `failure_criteria` | Optional |
| `analysis_method` | e.g. `FIXED_HORIZON_DIFF`, `RATIO_VS_BASELINE` |
| `analysis_config_version` | Version id for evaluator config |
| `stopping_rule` | `FIXED_HORIZON` \| `FIXED_SAMPLE` \| `SEQUENTIAL_RESERVED` |
| `required_data_validity_conditions` | Gates before SUCCEEDED/FAILED |
| `switchback_schedule` | Optional reserved struct (no engine in V1) |

**Plan freeze model**

- Event `PLAN_REGISTERED` appends a revision.
- Event `PLAN_FROZEN` MUST occur before any `OUTCOME_INSPECTED` / factual evaluation
  that feeds preregistered outcome. `frozen_plan_digest` = that revision's digest.
- Later changes: new `plan_revision` **or** `PROTOCOL_DEVIATION` event (explicit;
  does not rewrite prior revision bytes).
- **Forbidden:** in-place edit of a registered plan revision.

**Plan revision model**

- Revisions are append-only; readers select by `plan_revision` or `frozen_plan_digest`.
- POST_HOC plans use `POST_HOC_EXPLORATORY`; they cannot retroactively become
  preregistered for the same evaluation run.

---

## Orthogonal state machines

### execution_state (experiment)

```
PLANNED → REGISTERED → APPLY_PENDING → APPLIED → OBSERVING → EVALUATABLE → EVALUATED
                                                              ↘ ABORTED (from several states)
```

| State | Meaning |
|-------|---------|
| `PLANNED` | Experiment shell created; plan may still be drafted |
| `REGISTERED` | Plan revision registered (and frozen if confirmatory) |
| `APPLY_PENDING` | ChangeSet linked; apply not confirmed |
| `APPLIED` | Apply receipt proves mutation (future authority) |
| `OBSERVING` | Exposure established; observation window active |
| `EVALUATABLE` | Window + validity pre-checks allow evaluation run |
| `EVALUATED` | At least one deterministic evaluation run completed |
| `ABORTED` | Stopped before normal completion |

**Invariant:** `EVALUATED` means "evaluation executed", **not** success.

### outcome (experiment)

`PENDING` | `SUCCEEDED` | `FAILED` | `INCONCLUSIVE` | `INVALID`

| outcome | When |
|---------|------|
| `PENDING` | Before first terminal evaluation |
| `SUCCEEDED` / `FAILED` | Validity gates pass + criteria met / failed |
| `INCONCLUSIVE` | Insufficient coverage/window/data |
| `INVALID` | Validity hard-fail (e.g. exposure integrity, metric mismatch) |

**Invariant:** `execution_state=EVALUATED` AND `outcome=INCONCLUSIVE` is valid.

**Abort projection (V1):** `execution_state=ABORTED` before terminal evaluation →
`outcome=PENDING` (no `outcome=ABORTED` enum).

**Rule:** If required validity gates fail → MUST NOT emit `SUCCEEDED` or `FAILED`;
use `INCONCLUSIVE` or `INVALID` per `OUTCOME_MAPPING_VERSION` in spec
(`demem_outcome_v1`).

---

## Assignment / apply / exposure model

Separate concepts (decision ≠ assignment ≠ apply ≠ exposure):

| Concept | Fields |
|---------|--------|
| **Intended treatment** | Normalized ops from plan `treatment_definition` |
| **ChangeSet ref** | `changeset_id`, `changeset_semantic_digest` |
| **Apply evidence ref** | `ApplyEvidenceRef` (typed id + optional digest; no payload) |
| **Authoritative post-state** | `resulting_state_token` / snapshot ref |
| **effective_from** | When treatment state authoritative |
| **observation_start** | `max(effective_from, burn_in_end)` in plan timezone |

**effective_from model**

- Derived from Apply receipt + settings history confirmation when available.
- If exposure cannot be established authoritatively → MUST NOT enter `OBSERVING`
  as valid evidence (remain `APPLIED` or `APPLY_PENDING` with validity `UNKNOWN`).

Event types: `TREATMENT_INTENDED`, `CHANGESET_LINKED`, `APPLY_LINKED`,
`EXPOSURE_CONFIRMED` (carries `effective_from`, `observation_start`).

---

## Experiment design types & causal evidence

| experiment_design | causal_evidence_level (ordered) | Notes |
|-------------------|-----------------------------------|--------|
| `RANDOMIZED_AB` | `HIGH_RANDOMIZED` | Strongest in catalog |
| `SWITCHBACK` | `MEDIUM_SWITCHBACK` | Schedule/bucket fields reserved |
| `CONTROLLED_BEFORE_AFTER` | `MEDIUM_CONTROLLED` | Explicit control arm |
| `BEFORE_AFTER_OBSERVATIONAL` | `LOW_OBSERVATIONAL` | **Must not** be narrated as proof of causation |

`evidence_design` equals `experiment_design` for AI manifest stability.

Switchback reserved (no engine): `schedule`, `assignment_time_bucket`, `timezone`,
`burn_in`, `burn_out`, `carryover_policy`.

---

## Control / counterfactual model

`control_definition` MUST be explicit in every `ExperimentPlan`:

- `RANDOMIZED_CONTROL_ARM`
- `PRIOR_CONFIGURATION` (ref `state_token` / snapshot)
- `MATCHED_ENTITY` (cmp/id set + match rule id)
- `HISTORICAL_BASELINE` (baseline window only)
- `SWITCHBACK_CONTROL_WINDOW` (reserved)

Comparison semantics MUST NOT be implicit in prose.

---

## Data validity model

`data_validity_status`: `VALID` | `PARTIAL` | `INVALID` | `UNKNOWN`

**Reason codes** (multi-valued): `SOURCE_INCOMPLETE`, `SOURCE_COMPLETE_THROUGH_GAP`,
`ATTRIBUTION_COVERAGE_LOW`, `RECONCILIATION_FAILED`, `METRIC_DEFINITION_MISMATCH`,
`EXPOSURE_INTEGRITY_FAIL`, `MISSING_REQUIRED_INPUT`, `OBSERVATION_WINDOW_INCOMPLETE`,
`CONCURRENT_INTERVENTION`, `STALE_OR_REVISED_SOURCE`.

Evaluator MUST record validity snapshot on each evaluation run.

---

## Metric definition versioning

Metrics in plans and results reference **MetricSpecRef**:

- `metric_id`, `metric_definition_version`
- `source_family` (CH / PG / export leg / future attribution-facts)
- `grain`, `scope`
- `numerator_semantics`, `denominator_semantics`
- `coverage_requirements`
- `analysis_window` (may point into `window_model`)
- `evaluation_cutoff`, `source_complete_through`

**FactualResult** stores metric values keyed by `(metric_id, metric_definition_version)`.

Comparability rule: two values comparable only if same id+version+grain+scope.

---

## Window model

Structured `ExperimentWindowModel` (timezone-aware):

- `baseline_start`, `baseline_end`
- `treatment_effective_from` (mirrors exposure)
- `burn_in_end`, `burn_out_start` (optional)
- `observation_start`, `observation_end`
- `evaluation_cutoff`
- `source_complete_through`
- `evaluated_at` (set on run)
- `timezone` (IANA)

**Forbidden:** deriving observation windows from `DecisionRecord.created_at` alone.

---

## Concurrent interventions / confounders

Append-only `CONFOUNDER_DETECTED` events with structured refs:

- `PRICE_CHANGE`, `STOCK_AVAILABILITY`, `BUDGET_CHANGE`, `DRR_CPO_CHANGE`,
  `CAMPAIGN_ACTIVATION`, `ASSORTMENT_CHANGE`, `OVERLAPPING_EXPERIMENT`, etc.

Refs: `settings_state_token`, `decision_id`, `experiment_id`, or external fact id.

Confounders do not auto-invalidate; they feed validity (`CONCURRENT_INTERVENTION`)
and AI index `confounder_flags[]`.

---

## Intervention signature & similar experiment retrieval

**intervention_signature** (deterministic canonical JSON hashed):

- normalized `setting_keys[]`
- `old_values` / `new_values` or deltas (typed)
- `scope` (shop, cmp ids, nm ids)
- `control_mode` if applicable
- `changeset_semantic_digest` when available

Free text MUST NOT be signature input.

**Similar retrieval**

1. Primary: exact or prefix match on `intervention_signature` / digest.
2. Secondary (optional): vector similarity — **non-authoritative**, labeled `RETRIEVAL_HINT`.

`decision_fingerprint` remains coarse decision-class similarity only.

---

## Analysis method & stopping rule

Captured in `ExperimentPlan` (frozen):

- `analysis_method`, `analysis_config_version`
- `stopping_rule`: `FIXED_HORIZON` (V1 default), `FIXED_SAMPLE`, `SEQUENTIAL_RESERVED`
- `target_duration` / `min_sample` when applicable
- `minimum_meaningful_effect`

AI MUST NOT alter stopping criteria after results exist; changes require new plan
revision or `PROTOCOL_DEVIATION`.

---

## Factual result vs interpretation

| Aggregate | Authority | Writable by |
|-----------|-----------|-------------|
| **FactualResult** | Deterministic evaluator + metric readers | System evaluator only |
| **Interpretation** | Narrative, hypothesis refinement, follow-ups | AI/human append events |

**Boundary:** Interpretation events MUST NOT overwrite factual metric values,
validity status, deterministic outcome, or provenance refs. Separate ids:
`factual_result_id`, `interpretation_id`.

---

## Provenance / reproducibility

Each evaluation run carries `EvaluationProvenance`:

- memory `schema_version`
- `frozen_plan_digest`
- `ai_package_id` / digest
- source snapshot refs, `settings_state_token`
- `changeset_semantic_digest`, dry-run / apply receipt refs
- metric definition versions used
- `analysis_config_version`
- `evaluation_input_refs[]` (dataset slice ids)
- `producer` + `producer_version`
- `evaluation_run_digest`

Prefer refs/digests over payload duplication.

---

## Post-hoc analysis model

`PostHocAnalysisRecord`:

- `analysis_kind`: `EXPLORATORY` | `POST_HOC`
- links `experiment_id`, optional new metrics **not** in frozen plan
- **Cannot** modify frozen `ExperimentPlan` bytes or preregistered outcome
- conclusions stored as `Interpretation` with `is_post_hoc=true`

---

## Attribution-facts dependency

| State | Planning stance |
|-------|-----------------|
| Change `attribution-facts-contract` | Known project artifact |
| Slice A branch | `cursor/attribution-facts-contract-slice-a` |
| PR #456 | May be open / not on `stage` |
| Decision memory Slice A | **No hard dependency** on runtime attribution availability |
| Evaluation Slice | MAY reference `attribution_fact_set_ref` when deployed version supports it; validity `UNKNOWN` if missing |

---

## Reader port (extended)

`DecisionMemoryReader` adds:

- `get_experiment_plan(experiment_id, plan_revision?)`
- `get_factual_result(factual_result_id)`
- `find_similar_experiments(intervention_signature_digest, shop_id, ...)`
- `get_experiment_memory_index(scope)` → compact index entries

---

## AI Package future contract (`decision_memory_v1`)

```json
{
  "schema_version": "decision_memory_v1",
  "recent_decisions": [],
  "active_experiments": [],
  "recent_experiment_results": [],
  "experiment_memory_index": []
}
```

**experiment_memory_index** entry (compact, structured — not prose-primary):

- `experiment_id`, `decision_id`, `intervention_signature_digest`
- `experiment_design`, `causal_evidence_level`, `registration_kind`
- `execution_state`, `outcome`, `data_validity_status`
- `similar_prior_experiment_ids[]` (signature match)
- `immutable_refs`: plan digest, apply receipt, evaluation_run_digest

---

## Revised implementation slices

| Slice | Content | Notes |
|-------|---------|-------|
| **A** | Domain vocabulary, invariants, protocols, **test-only in-memory fake** + unit tests | **No PG**; `SLICE_A_BLOCKED_BY_APPLY=NO` |
| **B** | PostgreSQL append-only persistence + projections | After A accepted |
| **C** | Exposure / assignment / apply receipt ingest | Apply Authority + exposure rules |
| **D** | Deterministic evaluator, validity, factual result, provenance | Metric catalog; soft attribution refs |
| **E** | Post-hoc analysis records + interpretation append | |
| **F** | AI Package `decision_memory_v1` + index | `ai_package_v1` read-only |

Do not freeze physical schema before Slice A vocabulary sign-off.

## Risks

- Premature PG schema before plan freeze semantics → mitigated by Slice A-first.
- Observational designs misread as causal → `causal_evidence_level` + AI index fields.
- Attribution not on stage → validity UNKNOWN, not blocking vocabulary work.
