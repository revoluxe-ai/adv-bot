# Production fix evidence ROOT-001

BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: ROOT-001
COMMAND: /opsx-fix-bug GO
WORKER_ID: WEX_FIX_ROOT_001_GO
CREATED_AT: 2026-09-08T02:15:00Z

## Change summary

`PlanFactController.process_pre_adv` now resolves plan via
`PlanFactProvider.get_plan_data(pre_adv.auto_adv.adv_setting)` (same as
`process_adv`), instead of passing `pre_adv.plan_data` (overlay Plan) to
`PlanFactStatDTO.create`.

## Files changed

- app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py

## Invariant restored

ClickHouse plan_fact history plan columns receive base Plan only at
`process_pre_adv` write boundary. `PreComplexAdv.plan_data` overlay seed
unchanged for runtime consumers (CHILD-001 separate).

## Optional pytest check (fix-bug hop, not GREEN writer)

```text
poetry run pytest tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary -vv
```

Exit code: 0 (PASSED)

## Next

GREEN confirmation owned by `/opsx-test verify`:

```text
/opsx-test case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z finding=ROOT-001 verify
```

STATUS: PRODUCTION_PATCH_APPLIED
GREEN_EVIDENCE_PATH: (pending /opsx-test verify)
