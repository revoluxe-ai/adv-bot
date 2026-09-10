# GREEN evidence ROOT-001

TEST_ID: tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary
BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: ROOT-001
COMMAND: /opsx-test verify
CREATED_AT: 2026-09-08T02:20:00Z

## Verification

Re-ran exact RED `TEST_ID` on production after `/opsx-fix-bug GO`.
`TEST_CONTENT_SHA256` matches RED (no assertion edits; no `NON_WEAKEN_DELTA`).

## Pytest command

```text
poetry run pytest tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary -vv
```

Exit code: 0 (PASSED)

## Hashes

PRODUCTION_HASH_BEFORE: sha256:63617c061ef7dba3b58c8532f41b8e29a5696572cd53d4c30e2f040aa189895d
PRODUCTION_HASH_AFTER: sha256:b1ffe3307fa17fcdc1f856e9d304034e57971b85a24e319522194863faf8d50d
PRODUCTION_PATH: app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py
TEST_CONTENT_SHA256: 9de02d7aa5a9ce0dc4fe20a87d8bea8f80d4ac6ce84df44c5252f63d6938f0e7
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
FIX_EVIDENCE_PATH: results/FIX-ROOT-001.md

## Invariant confirmed

`PlanFactController.process_pre_adv` persists base Plan from
`PlanFactProvider.get_plan_data(adv_setting)` at CH write boundary.
Overlay Plan on `PreComplexAdv.plan_data` does not leak into
`PlanFactStatDTO` plan columns.

TARGETED_REGRESSIONS: tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary

STATUS: GREEN_CONFIRMED
