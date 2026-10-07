# Slice A scenario evidence (truthful)

FULL_CHANGE_CERTIFICATION: **deferred**

## FULLY_CERTIFIED_SLICE_A_SCENARIOS

Evidence: `tests/unit/decision_experiment_memory/` unit/scenario_seam via in-memory fake.

| ID | Scenario |
|----|----------|
| S01 | Decision without experiment |
| S02 | One decision, many experiments |
| S03 | Distinct experiment_id and decision_id |
| S04 | Plan immutable after PLAN_FROZEN |
| S05 | Amendment = new revision/digest |
| S06 | PROTOCOL_DEVIATION append-only |
| S07 | treatment_mode orthogonal to experiment_design |
| S09 | No ApplyEvidenceRef → no APPLY_CONFIRMED |
| S10 | No effective-state → no confirmed LIVE exposure |
| S11 | Observation from exposure + burn-in |

## PARTIAL_SLICE_A_SCENARIOS

| ID | Gap |
|----|-----|
| S08 | Event taxonomy only; ChangeSet/Apply ingest deferred (Slice C) |
| S24 | CONFOUNDER_DETECTED append vocabulary only; detection runtime deferred |

## DEFERRED_SCENARIOS

S12–S18, S20–S22 (evaluator Slice D), S23 (post-hoc Slice E), S25–S26 (AI index Slice F).
