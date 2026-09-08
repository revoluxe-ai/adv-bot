# FORENSICS ROOT-001

CASE_ID: BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z
INTAKE_ID: INTAKE-001
FINDING_ID: ROOT-001
COMMAND: /opsx-fix-bug
GO: no
CREATED_AT: 2026-09-08T02:10:00Z
PERSISTENCE_DECISION: new_finding
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z/ROOT-001/2026-09-08T01:54:19Z
ROUTE_RECONCILIATION: MATCH
CURRENT_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A

## Verdict

VERDICT: fix_now
RUNTIME_REACHABLE: yes
WRITE_BOUNDARY_REACHABLE: yes
DEAD_OR_LEGACY: no
FOLLOW_UP_SCOPE: none
AUTO_MATERIALIZE: false

## Invariant

ClickHouse plan_fact history MUST store base Plan only (`PlanFactProvider.get_plan_data` / AdvSetting). Overlay Plan (`PromoMaxCPO` / `PromoTargetCPO` via `EffectivePromoPlan`) MUST NOT be persisted as plan columns.

## Evidence chain

1. Runtime entrypoint: `app/modules/shop_runner/wb_shop.py` TaskGroup → `coroutines_manager.update_plan_fact_stats(only_bot_active=False)`.
2. Manager: `CoroutinesManager.update_plan_fact_stats` (decorator 5 min) → `WBShopDataManager.get_pre_complex_advs` → `PlanFactManager.process_and_save_pre_complex_advs`.
3. Seed construction: `WBShopDataManager._build_pre_complex_adv` вызывает `overlay_for_adv` → `plan_data = overlay.plan` (scaled effective plan, не base).
4. Write boundary defect: `PlanFactController.process_pre_adv` пишет `plan=pre_adv.plan_data` в `PlanFactStatDTO.create` → `insert_plan_fact_stats` (ClickHouse `default_db.plan_fact_stats` plan columns).
5. Sibling correct path: `PlanFactController.process_adv` читает `PlanFactProvider.get_plan_data(adv.adv_setting)` на write boundary — base Plan.
6. Promo overlay module docstring: «без мутации базового Plan»; attach_overlay_fields не трогает persisted Plan columns — CH write нарушает тот же инвариант.

## Callers

- runtime_entrypoints: `wb_shop.py` shop-runner TaskGroup; `CoroutinesManager.update_plan_fact_stats`
- direct_callers: `PlanFactManager.process_and_save_pre_complex_advs` → `PlanFactController.process_pre_adv`
- indirect_callers: `WBShopDataManager.get_pre_complex_advs` → `_build_pre_complex_adv`
- test_only_callers: `test_plan_fact_resolve_fact.py` (fact resolution only; не проверяет plan column source); `test_update_plan_fact_stats_coroutine.py` (mock PreComplexAdv, не assert plan source)

## Existing tests (gap)

- `test_get_plan_data_stays_raw` покрывает raw vs effective read на AdvSetting, не CH write path.
- `test_process_pre_adv_returns_none_when_no_fact` не assert-ит source plan columns.
- Нет regression, который падает, когда `pre_adv.plan_data` = overlay plan, а CH DTO должен получить base Plan.

## Minimal fix plan (not applied this hop)

- files allowed: `plan_fact_controller.py` (предпочтительно: `process_pre_adv` читает `PlanFactProvider.get_plan_data(pre_adv.auto_adv)` как `process_adv`); опционально `wb_shop_data_manager.py` если seed semantics уточняются отдельно.
- files forbidden: tests (RED пишет `/opsx-test`); CHILD-001 consumers; openspec/**; enable `RaisePlanOnPromobonuses`; leftover/P0 mix; HIGH6 mutation.
- exact behavior: `insert_plan_fact_stats` получает base Plan (`get_plan_data`), даже когда `PreComplexAdv.plan_data` несёт overlay для runtime resolution.
- paired regression: overlay active → DTO.plan == base; allowed path `process_adv` / zero fraction unchanged.

## Stop conditions

- GO отсутствует → production/app не менять.
- RED принадлежит `/opsx-test`.
- CHILD-001 не стартовать в этом hop.
- Не закрывать finding (`closed_fixed` запрещён из fix-bug без GREEN).

## Next

/opsx-test case=BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z finding=ROOT-001
