# Scenario Coverage Plan

CHANGE_ID: decision-experiment-memory
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-a48d03971a706909
LIFECYCLE_STATUS: DERIVED

Required-evidence planning only. Does not claim tests exist, were executed, or
passed. Architecture is **accepted**; implementation is gated by Slice A–F.

## Derived lifecycle (domain memory)

From accepted `design.md` / `owner-contract.md`:

- L1 Decision semantics recorded (`DecisionMemoryRecord`)
- L2 Optional experiment shell + `ExperimentPlan` registration/freeze
- L3 Treatment mode (`LIVE` | `SHADOW`) vs `experiment_design`
- L4 Assignment / ChangeSet / `ApplyEvidenceRef` / exposure anchoring
- L5 Observation windows (not decision timestamp)
- L6 Deterministic evaluation + validity → factual outcome
- L7 Interpretation / post-hoc (non-mutating)
- L8 Reader / AI index (deferred)

LIFECYCLE_COVERAGE:

- L1 → S01, S02, S03 — covered
- L2 → S04, S05, S06 — covered
- L3 → S07, S19 — covered
- L4 → S08, S09, S10 — covered
- L5 → S11, S21 — covered
- L6 → S12–S18, S20, S22 — covered (Slice A: projection rules; Slice D: evaluator)
- L7 → S23, S24 — covered (Slice A boundary; Slice E append)
- L8 → deferred (Slice F; no S-row for ZIP/MCP in this plan)

## Architecture and evidence constraints

- Decision Experiment Memory **owns** semantics, plans, lifecycle projections,
  validity/outcome mapping, factual result **history**, interpretation linkage.
- **Does not own** settings, catalog, Apply execution, source metrics, attribution
  (refs/digests only). `ApplyEvidenceRef` — no receipt payload in this change.
- Slice A: `InMemoryDecisionMemoryRepository` is **test-only fake**; no production
  persistence.
- Slice B+: PG; Slice C: exposure ingest; Slice D: evaluator; Slice E: post-hoc;
  Slice F: AI Package / `experiment_memory_index`.

Shared evidence (when implemented):

- Slice A: `unit_component` + domain `scenario_seam` via in-memory fake and
  projection functions (no PG/CH/WB).
- Later slices: boundary integration per store/Apply as required.

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: decision-experiment-memory
SOURCE_SPEC_SHA: bb30f71770d61bd72c484c87b47d1fc475ba7a36d348c4fc71ebd32e3b357932
PLAN_STATUS: ready

### S01 — Decision without experiment

SCENARIO_ID: `openspec/changes/decision-experiment-memory/specs/decision-experiment-memory/spec.md::#### Scenario: Policy decision without measurable experiment` (normative via Requirement: Decision without experiment)
LIFECYCLE_STEPS: L1
IMPLEMENTATION_SLICE: A
GIVEN_WHEN_THEN: Decision recorded with semantics only; no `ExperimentRecordV1`.
PRODUCTION_ENTRYPOINT: `decision_experiment_memory` domain writer + projection (Slice A fake).
REQUIRED_EVIDENCE: `unit_component` / `scenario_seam` on in-memory fake; assert one `decision_id`, zero experiments.

### S02 — One decision, many experiments (contract)

SCENARIO_ID: plan-native `S02`
LIFECYCLE_STEPS: L1, L2
IMPLEMENTATION_SLICE: A (contract); B+ (persistence enforces V1 0..1 writer optional)
GIVEN_WHEN_THEN: Domain model allows two `experiment_id` values for same `decision_id`; V1 API may reject second create without 1:1 schema.
REQUIRED_EVIDENCE: Slice A type/model tests; no unique (decision_id) on experiment aggregate.

### S03 — Independent experiment_id and decision_id

SCENARIO_ID: `spec.md::#### Scenario: Distinct ids for one decision-experiment pair`
LIFECYCLE_STEPS: L1, L2
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: Persist E1≠D1; forbid invariant `experiment_id == decision_id` in factory/projection tests.

### S04 — Plan immutable after PLAN_FROZEN

SCENARIO_ID: `spec.md::#### Scenario: Plan registration creates immutable revision` + freeze requirement
LIFECYCLE_STEPS: L2
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: After `PLAN_FROZEN`, append-only events cannot alter frozen revision bytes; confirmatory evaluation rejected without freeze.

### S05 — Amendment = new revision/digest

SCENARIO_ID: `spec.md::#### Scenario: New revision preserves old digest`
LIFECYCLE_STEPS: L2
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: `plan_revision=2` new digest; revision 1 readable unchanged.

### S06 — PROTOCOL_DEVIATION append-only

SCENARIO_ID: plan-native `S06`
LIFECYCLE_STEPS: L2
IMPLEMENTATION_SLICE: A
GIVEN_WHEN_THEN: Deviation event recorded; preregistered plan bytes unchanged; preregistered outcome path unchanged without new evaluation contract.
REQUIRED_EVIDENCE: Event log contains deviation; frozen digest stable.

### S07 — treatment_mode orthogonal to experiment_design

SCENARIO_ID: `spec.md::#### Scenario: Shadow observational study`
LIFECYCLE_STEPS: L3
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: `treatment_mode=SHADOW` + `experiment_design=BEFORE_AFTER_OBSERVATIONAL`; SHADOW not an `experiment_design` enum value.

### S08 — Decision / ChangeSet / Apply / exposure distinct

SCENARIO_ID: `spec.md` assignment apply exposure requirements
LIFECYCLE_STEPS: L4
IMPLEMENTATION_SLICE: A (event taxonomy); C (ingest)
GIVEN_WHEN_THEN: Decision recorded without ChangeSet; ChangeSet linked without ApplyEvidenceRef; apply without EXPOSURE_CONFIRMED.
REQUIRED_EVIDENCE: Slice A projection tests per event type; Slice C integration deferred.

### S09 — No ApplyEvidenceRef → no APPLY_CONFIRMED

SCENARIO_ID: `spec.md::#### Scenario: No apply evidence no apply confirmed`
LIFECYCLE_STEPS: L4
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: Decision status projection without `ApplyEvidenceRef`.

### S10 — No effective-state → no confirmed LIVE exposure

SCENARIO_ID: `spec.md::#### Scenario: No effective state evidence no confirmed live exposure`
LIFECYCLE_STEPS: L4
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: `treatment_mode=LIVE` without exposure evidence → no confirmed OBSERVING; `treatment_effective_from` unset.

### S11 — Observation from exposure + burn-in

SCENARIO_ID: `spec.md::#### Scenario: Observation anchors to exposure not decision time`
LIFECYCLE_STEPS: L5
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: `WindowModel` computes `observation_start` from `effective_from`/burn-in, not `decision.created_at`.

### S12 — EVALUATED + SUCCEEDED when validity permits

SCENARIO_ID: plan-native `S12`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: D (evaluator); A (outcome projection rules with fixtures)
REQUIRED_EVIDENCE: Validity VALID + criteria met → SUCCEEDED; Slice A may test projection table only with injected factual inputs.

### S13 — EVALUATED + FAILED when validity permits

SCENARIO_ID: plan-native `S13`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: D; A (projection)
REQUIRED_EVIDENCE: Validity VALID + failure criteria met → FAILED (business underperformance, not integrity).

### S14 — EVALUATED + INCONCLUSIVE

SCENARIO_ID: `spec.md::#### Scenario: Evaluated with inconclusive outcome`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: A, D
REQUIRED_EVIDENCE: `execution_state=EVALUATED`, `outcome=INCONCLUSIVE` (e.g. neutral effect region).

### S15 — EVALUATED + INVALID

SCENARIO_ID: plan-native `S15`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: A, D
REQUIRED_EVIDENCE: Integrity mapping → `outcome=INVALID` per normative table (spec).

### S16 — ABORTED execution → outcome PENDING

SCENARIO_ID: plan-native `S16`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: A
GIVEN_WHEN_THEN: `execution_state=ABORTED` before terminal evaluation → `outcome=PENDING` (V1; no `outcome=ABORTED`).
REQUIRED_EVIDENCE: Projection unit test; documented in spec.

### S17 — Integrity failure → INVALID not FAILED

SCENARIO_ID: plan-native `S17`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: A, D
REQUIRED_EVIDENCE: Reason codes mapped to INVALID (e.g. `EXPOSURE_INTEGRITY_FAIL`); never FAILED.

### S18 — Insufficient effect evidence → INCONCLUSIVE not INVALID

SCENARIO_ID: plan-native `S18`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: A, D
REQUIRED_EVIDENCE: Valid run, threshold not met → INCONCLUSIVE.

### S19 — Observational design causal cap

SCENARIO_ID: `spec.md::#### Scenario: Observational design capped evidence level`
LIFECYCLE_STEPS: L3
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: `causal_evidence_level=LOW_OBSERVATIONAL` for `BEFORE_AFTER_OBSERVATIONAL`.

### S20 — Metric definition version mismatch

SCENARIO_ID: `spec.md::#### Scenario: Incomparable metrics flagged`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: D
REQUIRED_EVIDENCE: Evaluation gated INVALID or blocked via `METRIC_DEFINITION_MISMATCH`.

### S21 — source_complete_through lag

SCENARIO_ID: plan-native `S21`
LIFECYCLE_STEPS: L5, L6
IMPLEMENTATION_SLICE: D
REQUIRED_EVIDENCE: Evaluation before `source_complete_through` → INCONCLUSIVE or INVALID per mapping (`SOURCE_COMPLETE_THROUGH_GAP`).

### S22 — Concurrent intervention evidence

SCENARIO_ID: plan-native `S22`
LIFECYCLE_STEPS: L6
IMPLEMENTATION_SLICE: D (C confounder ingest optional)
REQUIRED_EVIDENCE: `CONFOUNDER_DETECTED` + validity reason `CONCURRENT_INTERVENTION`; does not auto-invalidate without policy.

### S23 — Interpretation cannot overwrite facts

SCENARIO_ID: `spec.md` factual vs interpretation requirement
LIFECYCLE_STEPS: L7
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: Append interpretation event; factual result bytes unchanged.

### S24 — Post-hoc cannot mutate preregistered outcome

SCENARIO_ID: `spec.md` post-hoc requirement
LIFECYCLE_STEPS: L7
IMPLEMENTATION_SLICE: E (append); A (invariant)
REQUIRED_EVIDENCE: POST_HOC interpretation separate; frozen plan + preregistered outcome unchanged.

### S25 — Intervention signature authoritative

SCENARIO_ID: `spec.md` intervention signature requirement
LIFECYCLE_STEPS: L1, L2
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: Deterministic digest from structured fields; vector hint labeled non-authoritative.

### S26 — In-memory repository test-only

SCENARIO_ID: plan-native `S26`
LIFECYCLE_STEPS: L1
IMPLEMENTATION_SLICE: A
REQUIRED_EVIDENCE: Module doc/tests state fake not production store; no PG adapter in Slice A.

## Slice summary

| Slice | Scenario IDs |
|-------|----------------|
| A (domain + test fake) | S01–S11, S14–S19, S23, S25, S26 (+ projection rules S12–S13, S15–S18) |
| B (PG) | persistence for all rows when events stored |
| C | S08 ingest paths |
| D | S12–S13, S15–S18, S20–S22 evaluator |
| E | S24 post-hoc append |
| F | L8 reader index (deferred) |

UNRESOLVED_GAPS: none for planning. Evaluator/Apply/AI Package tests deferred honestly per slice.
