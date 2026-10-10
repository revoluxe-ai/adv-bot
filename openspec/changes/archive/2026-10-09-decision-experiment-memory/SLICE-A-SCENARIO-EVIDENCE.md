# Slice A scenario evidence (truthful)

FULL_CHANGE_CERTIFICATION: **deferred** (slices B–F)

Legend: **PASS** = executable Slice A test/seam; **CONTRIBUTION** = vocabulary/projection only;
**DEFERRED** = requires later slice runtime.

| ID | Status | Evidence |
|----|--------|----------|
| S01 | PASS | `test_slice_a_domain::test_decision_without_experiment` |
| S02 | PASS | `test_two_experiments_one_decision` |
| S03 | PASS | `test_distinct_experiment_and_decision_ids` |
| S04 | PASS | `test_plan_revision_immutable_on_save` |
| S05 | PASS | `test_plan_freeze_and_revision_digest_stable` |
| S06 | PASS | `test_protocol_deviation_append_only` |
| S07 | PASS | `test_shadow_mode_not_experiment_design` |
| S08 | CONTRIBUTION | Event taxonomy + refs; ingest deferred Slice C |
| S09 | PASS | `test_no_apply_evidence_no_apply_confirmed` |
| S10 | PASS | LIVE exposure gate tests in `test_live_exposure_and_ports` |
| S11 | PASS | `test_observation_start_from_exposure_not_decision_time` |
| S12 | DEFERRED | Evaluator Slice D |
| S13 | DEFERRED | Evaluator Slice D |
| S14 | PASS | `test_outcome_mapping_invalid_vs_inconclusive` + EVALUATED+INCONCLUSIVE |
| S15 | CONTRIBUTION | Validity projection helpers in `domain/validity.py` |
| S16 | PASS | `test_abort_execution_outcome_pending` |
| S17 | CONTRIBUTION | INVALID mapping via validity vocabulary/tests |
| S18 | CONTRIBUTION | INCONCLUSIVE mapping via validity vocabulary/tests |
| S19 | PASS | `causal_evidence_level_for_design` + observational cap tests |
| S20 | DEFERRED | Evaluator Slice D |
| S21 | DEFERRED | Evaluator Slice D |
| S22 | DEFERRED | Evaluator Slice D |
| S23 | PASS | Interpretation types + `is_post_hoc`; no factual mutation API |
| S24 | CONTRIBUTION | `PostHocAnalysisRecord` + `CONFOUNDER_DETECTED` vocabulary |
| S25 | PASS | `test_canonical_json` + intervention signature digest tests |
| S26 | PASS | `InMemoryDecisionMemoryRepository` test-only module docs + unit usage |
