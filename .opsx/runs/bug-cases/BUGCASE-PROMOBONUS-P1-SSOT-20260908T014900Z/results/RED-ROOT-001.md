# RED evidence ROOT-001

TEST_ID: tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary
BUG_CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
FINDING_ID: ROOT-001
COMMAND: /opsx-test
CREATED_AT: 2026-09-08T02:03:00Z

## Expected failure

When ``PreComplexAdv.plan_data`` carries overlay Plan (``max_pay_for_order=1000``)
while ``PlanFactProvider.get_plan_data(adv_setting)`` returns base Plan
(``max_pay_for_order=500``), ``PlanFactController.process_pre_adv`` must persist
base Plan columns in ``PlanFactStatDTO``. Current production passes
``plan=pre_adv.plan_data`` directly, so overlay values leak to CH write boundary.

## Actual failure

```text
AssertionError: assert 1000 == 500
 +  where 1000 = PlanFactStatDTO(..., plan_target_pay_for_order=800, plan_max_pay_for_order=1000, ...).plan_max_pay_for_order
 +  and   500 = PlanData(..., max_pay_for_order=500).max_pay_for_order
```

## Pytest command

```text
poetry run pytest tests/unit/app/modules/shop_runner/services/plan_fact_controller/test_process_pre_adv_plan_source.py::test_process_pre_adv_persists_base_plan_not_overlay_on_write_boundary -vv
```

Exit code: 1 (FAILED)

FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:63617c061ef7dba3b58c8532f41b8e29a5696572cd53d4c30e2f040aa189895d
PRODUCTION_PATH: app/modules/shop_runner/service_manager/services/plan_fact_controller/plan_fact_controller.py
TEST_CONTENT_SHA256: 9de02d7aa5a9ce0dc4fe20a87d8bea8f80d4ac6ce84df44c5252f63d6938f0e7
STATUS: RED_CONFIRMED

## Invariant under test

ClickHouse plan_fact history MUST store base Plan only (``PlanFactProvider.get_plan_data``).
Overlay Plan MUST NOT appear in ``PlanFactStatDTO`` plan columns at ``process_pre_adv`` write boundary.

## Next

Owner may append ``GO`` then:

```text
/opsx-fix-bug case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z intake=INTAKE-001 finding=ROOT-001 claim_token=CLAIM/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/ROOT-001/2026-09-08T01:54:19Z GO
```
