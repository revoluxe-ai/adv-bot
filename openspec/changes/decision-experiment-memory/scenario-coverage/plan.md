# Scenario Coverage Plan

CHANGE_ID: decision-experiment-memory
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-f31a3328d581455d
LIFECYCLE_STATUS: DERIVED

Planning evidence only — tests not claimed executed.

## Lifecycle coverage

From `design.md#derived-lifecycle`:

- L1 Decision semantics recorded
- L2 Experiment plan registered / frozen
- L3 Intervention bound without Apply
- L4 Apply bound (LIVE) or SHADOW observe
- L5 Evaluation → EVALUATED + outcome
- L6 Correction / follow-up experiment

LIFECYCLE_COVERAGE:

- L1 → S01, S02 — covered
- L2 → S03, S04 — covered
- L3 → S05, S06 — covered
- L4 → S07, S08 — covered
- L5 → S09, S10, S11 — covered
- L6 → S12 — covered

## Scenarios

| Id | Spec requirement | Lifecycle | Slice A test focus |
|----|------------------|-----------|-------------------|
| S01 | Independent identities | L1 | follow-up `experiment_id` ≠ prior |
| S02 | Decision without experiment | L1 | no experiment row required |
| S03 | Design vs treatment_mode | L2 | SHADOW not in experiment_design |
| S04 | Plan freeze by digest | L2 | amendment bumps revision |
| S05 | Apply optional in domain | L3 | vocabulary without receipt type |
| S06 | No APPLY_CONFIRMED without BOUND | L3 | execution_state guard |
| S07 | LIVE exposure needs Apply | L4 | LIVE + UNBOUND → no exposure claim |
| S08 | SHADOW observe path | L4 | OBSERVING without Apply allowed |
| S09 | EVALUATED + INVALID | L5 | two-axis validity |
| S10 | EVALUATED + INCONCLUSIVE | L5 | partial metrics |
| S11 | Outcome not from narrative | L5 | missing data → INCONCLUSIVE |
| S12 | Follow-up experiment 1:N | L6 | same decision_id, new experiment_id |

UNRESOLVED_GAPS: none for planning.
