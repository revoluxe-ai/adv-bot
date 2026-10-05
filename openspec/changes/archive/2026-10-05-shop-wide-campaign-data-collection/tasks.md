## TASK_GENERATION_READINESS

```text
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID: SCPV1-f61151add8956265
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
SCENARIO_PLAN_SUPERSEDES: SCPV1-0e11e1d5c3a8b2bb
TASKS_STATUS: READY
IMPLEMENTATION_FRONTIER: VERIFY / merge-review
PROVEN_COMPLETE: §1–§9.3 (code + unit test evidence; scenario acceptance 2026-10-05)
OPEN_APPLY: none
REASON: none
```

Upstream: `design.md` (`DESIGN_STATUS: READY`); delta spec
`connected-shop-campaign-ad-data-collection`; proposed decision
`decisions/shop-runner-shop-wide-collection/decision.md`; owner-contract;
architectural debt
[`openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md`](../../architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md)
(MUST cite in apply/verify).

Evidence roles: `LEGACY_BASELINE` — текущий managed-only universe через
`get_complex_advs(only_bot_active=False)` / `__get_advs` (`active_status != 'done'`,
включая `refused`; post-filter непустые `nmids`; search legs через
`search_adv_id` / `ComplexAdv.all_adv_ids`). `TARGET_REGRESSION` /
`FINAL_ACCEPTANCE` — dual-path shop-wide collection без расширения management
writes. LEGACY_BASELINE MUST NOT требовать сохранения «только PG-universe»
assertions после intentional shop-wide expansion.

Cross-change dependency (Owner 2026-10-05): shop-wide `(nmid, date)` funnel /
`wb_common_stat` writer — **`shop-wide-common-sales-collection`**. Campaign change
**MUST NOT** планировать второй independent funnel writer; legacy
`CommonSaleStatUpdater` на managed loader — существующий маршрут под common-sales
coordinator.

Инварианты apply (из design/spec/debt): исполнение **только** shop-runner
(`WBShop.run` / `CoroutinesManager`); **scripts/Job MUST NOT** быть primary
executor; **collection ownership** (§B.1 loader) **≠** **management relationship**
(§B.3; `bot_active` / наличие `AdvSetting` **не** proof of connect); unmanaged
initial slice **без** целого `ClustersAdvStatUpdater`; **без**
`get_sales_funnel_products_history` / `ClickHouseCommonStatManager.insert`;
campaign grains `full_adv_wb_stat` `(adv_id, date)` без `shop_id`; non-atomic
handoff, route epoch, read-latest `argMax`, availability отражает recovery.

## 1. LEGACY_BASELINE и write-gate seams (до расширения universe)

- [x] 1.1 `LEGACY_BASELINE`: characterization текущего shop-runner tick —
  RECORD-корутины с `only_bot_active=False` обрабатывают только `ComplexAdv` из
  loader'а; WB-only id **не** попадают в collectors (spec «Сбор при активном
  shop-runner» — контраст для S01).
- [x] 1.2 `LEGACY_BASELINE`: зафиксировать predicate `__get_advs`:
  `active_status != 'done'` **включает** `refused`, **исключает** `done`;
  post-filter `nmids` непустые (design §B.1).
- [x] 1.3 `TARGET_REGRESSION`: write-gate тест — forbidden path collection
  **MUST NOT** вызывать `wb_db_manager.update_advs_in_db` / `ShopDataUpdater`
  ради discovery; **MUST NOT** создавать `AdvSetting`, **MUST NOT** менять
  `bot_active`, **MUST NOT** WB management adapters (L8; S10, S21).

## 2. ClickHouse DDL и inventory plane (L3, L6)

- [x] 2.1 DDL/migration: `default_db.shop_campaign_inventory` и
  `default_db.shop_campaign_collection_availability` (design §D.1; CH SQL
  qualification decision). Issued SQL:
  `scripts/clickhouse_migrations/007_create_shop_campaign_inventory_and_availability.sql`
  (sequence **007** — stage merge reserved **006** for
  `create_campaign_settings_history`; ClickHouse migration control plane is
  ledger/target; PostgreSQL is advisory-lock coordinator only, not CH
  migration ledger). `shop_campaign_inventory.route_version` — единственный
  durable source of truth для route epoch; Redis — только coordination/lock, не
  второй SoT. Поля `route`, `version`, diagnostic `reason_code` / `collector_id` —
  harmless naming из design Open Questions.
- [x] 2.2 Unit/integration: upsert inventory на WB discovery (S03 finished WB
  lifecycle still discovered — L1/L2); unmapped lifecycle → `unknown`, **не**
  silent drop.
- [x] 2.3 Feature flag per shop: dual-path routing + unmanaged slice;
  rollback = managed-only поведение; CH history retained (design Migration Plan).
  Fail-closed gate (satisfied): ON **requires** resolver §3.1 before unmanaged
  collector starts; resolver implemented — ``CampaignCollectionRouteResolver``;
  prior pre-3.1 slice did not read/write ``shop_campaign_inventory.route_version``.

## 3. CampaignCollectionRouteResolver (L2 routing)

- [x] 3.1 Реализовать resolver per shop tick: ownership sets §B.1 для campaign
  grains `full_adv_wb_stat`, managed-only `clusters_adv_stats` (**not**
  `wb_common_stat` — owner **`shop-wide-common-sales-collection`**); route
  `MANAGED` | `UNMANAGED` | `UNKNOWN` per `(shop_id, wb_adv_id, grain)`.
  Evidence: ``route_resolver.py``; ``test_campaign_collection_route_resolver.py``.
- [x] 3.2 `TARGET_REGRESSION` (S02): WB-only id без PG row → **UNMANAGED**;
  **MUST NOT** create `AdvSetting`.
  Evidence: ``test_task_32_s02_wb_only_unmanaged_no_adv_setting_side_effect``.
- [x] 3.3 `TARGET_REGRESSION` (S04): sync-created row в loader → **MANAGED**
  collection; management relationship **UNKNOWN** (не equate PG row to user
  connect).
  Evidence: ``test_task_33_s04_sync_row_managed_management_unproven``;
  ``is_management_relationship_proven``.
- [x] 3.4 `TARGET_REGRESSION` (S05, S14, S19): `refused` в loader → **MANAGED**
  collection ownership; unmanaged **MUST NOT** duplicate `full_adv_wb_stat`
  grain для того же `adv_id` (S09 overlap).
  Evidence: ``test_task_34_s05_refused_managed_no_unmanaged_duplicate``.
- [x] 3.5 `TARGET_REGRESSION` (S06, S07): `done` выпадает из loader →
  **UNMANAGED** при WB discovery; нет строки PG + WB id → **UNMANAGED**, **не**
  «кампания не существует».
  Evidence: ``test_task_35_s06_s07_done_and_no_enrollment_unmanaged``.
- [x] 3.6 `TARGET_REGRESSION` (S08): search leg через `search_adv_id` /
  `all_adv_ids` на **MANAGED** path для `(adv_id, date)` grain.
  Evidence: ``test_task_36_s08_search_leg_managed_full_adv_grain``.
- [x] 3.7 `TARGET_REGRESSION` (S09): managed ownership → unmanaged **MUST NOT**
  CH write тот же grain в том же tick.
  Evidence: ``test_task_37_s09_managed_ownership_blocks_unmanaged_write_eligibility``;
  ``is_unmanaged_collector_write_eligible``.
- [x] 3.8 `TARGET_REGRESSION` (S15): после bounded retry **UNKNOWN** → inventory
  upsert + availability; **MUST NOT** create `AdvSetting`.
  Evidence: ``test_task_38_s15_unknown_fail_closed_no_write_no_enrollment``;
  ``is_managed_collector_write_eligible`` / ``is_unmanaged_collector_write_eligible``.
- [x] 3.9 `TARGET_REGRESSION` (S21): routing **MUST NOT** использовать
  `bot_active` или presence-only PG как proof of connect; **MUST NOT** новая PG
  provenance column.
  Evidence: ``test_task_39_s21_bot_active_and_presence_not_ownership_proof``.

## 4. UNMANAGED minimal read-only slice (L5)

- [x] 4.1 Orchestrator в `app/modules/shop_runner/`: WB discovery minus ownership
  set; thin ends — `CampaignsInfoV2`, `wb_data_getter.get_full_adv_stat_for_adv_ids`,
  `full_wb_adv_stat.insert`, inventory/availability writers (design §D.3).
  **MUST NOT** `get_sales_funnel_products_history` / `ClickHouseCommonStatManager.insert`
  (owner **`shop-wide-common-sales-collection`**).
  Evidence: ``unmanaged_orchestrator.py``; ``availability_append.py``;
  ``inventory_route_read.py``; ``route_write_gate.py``;
  ``test_unmanaged_campaign_collector.py::test_orchestrator_module_forbids_forbidden_imports``.
- [x] 4.2 `TARGET_REGRESSION` (S10): успешный unmanaged collect → **MUST NOT**
  create `AdvSetting`, **MUST NOT** change `bot_active`.
  Evidence: ``test_unmanaged_campaign_collector.py::test_task_42_s10_unmanaged_collect_no_enrollment_side_effects``.
- [x] 4.3 `TARGET_REGRESSION` (S13): unmanaged пишет `full_adv_wb_stat` only;
  **MUST NOT** write `wb_common_stat` / funnel (owner common-sales change);
  **MUST NOT** write `clusters_adv_stats`; **MUST NOT** invoke whole
  `ClustersAdvStatUpdater` (debt Limits §cluster gap).
  Evidence: ``test_unmanaged_campaign_collector.py::test_task_43_s13_unmanaged_writes_full_adv_only_not_forbidden_seams``.
- [x] 4.4 Перед записью unmanaged collector MUST сверить актуальный
  `shop_campaign_inventory.route_version` и collection ownership (design §C,
  §D.1). Durable route epoch — только inventory `route_version`; Redis MUST NOT
  быть вторым SoT epoch. Если epoch устарел или ownership не совпадает с
  маршрутом collector, MUST NOT писать fact grain. Availability row MUST нести
  тот же `route_version` и MUST NOT заменять запрет записи fact grain.
  Evidence: ``route_write_gate.py``; ``test_unmanaged_campaign_collector.py::test_task_44_route_epoch_stale_skips_fact_write``;
  ``test_task_44_route_epoch_current_allows_fact_write``;
  ``test_route_write_gate_pure_stale_epoch``; ``test_route_write_gate_pure_ownership_mismatch``.

## 5. MANAGED path preservation (L4)

- [x] 5.1 Сохранить legacy RECORD coroutines без large refactor; universe =
  §B.1 ownership only (`only_bot_active=False` на full/common/clusters RECORD).
  Evidence: ``managed_record_contract.py``; docstrings RECORD в ``manager.py``;
  ``test_managed_path_preservation.py::test_task_51_*``.
- [x] 5.2 `TARGET_REGRESSION` (S14): refused managed → legacy path **MAY**
  `update_clusters_adv_stats_*` (clusters in scope managed only); unmanaged **MUST
  NOT** duplicate full_adv для того же id.
  Evidence: ``test_managed_path_preservation.py::test_task_52_s14_refused_managed_clusters_no_unmanaged_full_adv_duplicate``.
- [x] 5.3 `LEGACY_BASELINE` → `TARGET_REGRESSION`: paired tests — managed
  collectors still run for loader universe; shop-wide flag OFF = prior behavior.
  Evidence: ``test_managed_path_preservation.py::test_task_53_paired_baseline_target_flag_preserves_managed_tick``.

## 6. Partial failure, availability, read-latest (L6)

- [x] 6.1 `TARGET_REGRESSION` (S11): сбой одного collector → `reason_code` в
  availability; другие collectors **MUST** continue/retry next cycle.
  Evidence: ``unmanaged_orchestrator.py`` per-adv fetch/write isolation;
  ``REASON_COLLECTOR_SOURCE_ERROR`` / ``REASON_FACT_WRITE_ERROR`` in
  ``route_write_gate.py``;
  ``test_partial_failure_availability_read_latest.py::test_task_61_s11_*``.
- [x] 6.2 `TARGET_REGRESSION` (S12): prior CH success + failed latest attempt →
  read-latest (`argMax` / ReplacingMergeTree) **MUST** retain last success until
  superseded (design §F.3).
  Evidence: ``full_adv_read_latest.py`` ``load_read_latest_full_adv_facts``;
  ``test_partial_failure_availability_read_latest.py::test_task_62_s12_*``.
- [x] 6.3 Integration: append-only availability; partial token/source failure
  **MUST NOT** stop остальные источники (owner-contract).
  Evidence: ``test_partial_failure_availability_read_latest.py::test_task_63_*``
  (multi-campaign partial failure, append-only rows, stale route fail-closed).

## 7. Handoff UNMANAGED ↔ MANAGED (L7, non-atomic)

- [x] 7.1 `TARGET_REGRESSION` (S16): после user connect (`connect_existing_advs`)
  следующий tick → **MANAGED** collection; unmanaged **MUST NOT** new writes на
  owned grains; management relationship остаётся unproven.
  Evidence: ``route_handoff.py``; ``test_route_handoff.py::test_task_71_*``.
- [x] 7.2 `TARGET_REGRESSION` (S17): overlap window — перед записью fact grain
  collector MUST сверить актуальные `shop_campaign_inventory.route_version`
  и collection ownership. Если epoch устарел или ownership не совпадает с
  маршрутом collector, collector MUST NOT писать fact grain. In-flight MAY
  завершиться только если на момент write epoch актуален и ownership совпадает.
  Availability row этой попытки MUST нести тот же `route_version` и MUST NOT
  заменять запрет записи fact grain. Read-latest **MUST NOT** double-count
  declared grains.
  Evidence: ``route_write_gate.py``; ``test_route_handoff.py::test_task_72_*``.
- [x] 7.3 `TARGET_REGRESSION` (S18): `active_status` → `done` → stop managed
  RECORD; continue **UNMANAGED**; CH history по `adv_id` retained.
  Evidence: ``route_handoff.py``; ``test_route_handoff.py::test_task_73_*``.
- [x] 7.4 `TARGET_REGRESSION` (S19): `refused` **MUST NOT** переводить ownership
  на unmanaged из-за disconnect-like событий alone.
  Evidence: ``route_handoff.py``; ``test_route_handoff.py::test_task_74_*``.
- [x] 7.5 `TARGET_REGRESSION` (S22): маршрут уже переключён, dual-leg history
  существует; нового connect или disconnect в этом сценарии нет. Periodic или
  reconcile entry сверяет read-latest grains. Расхождение фиксируется в
  availability с `reason_code` `route_transition_reconcile`, несущим сверенный
  `shop_campaign_inventory.route_version`. Устаревший epoch или несовпадение
  ownership MUST NOT писать fact grain. Availability MUST нести сверенный
  `route_version` и MUST NOT заменять запрет записи fact grain. Read-latest
  MUST NOT double-count declared grains.
  Evidence: ``route_transition_reconcile.py``; ``test_route_handoff.py::test_task_75_*``.

## 8. Shop-runner orchestration entry (L1, L8)

- [x] 8.1 Wire resolver + unmanaged orchestrator в `CoroutinesManager` /
  `WBShop.run` decorator cycle; **MUST NOT** scripts/Job entry (proposed decision).
  Evidence: ``manager.collect_shop_wide_campaign_advertising``;
  ``tick_wiring.run_shop_wide_unmanaged_tick``; ``wb_shop.py`` dual-path task;
  ``PromotionManager.discover_cabinet_campaigns``; ``test_shop_campaign_inventory_upsert.py::test_inventory_upsert_is_wired_via_shop_runner_tick``.
- [x] 8.2 `TARGET_REGRESSION` (S01): periodic shop-runner tick initiates
  discovery + dual-path collectors без delegate to scripts/Job.
  Evidence: ``test_shop_wide_tick_orchestration.py::test_task_82_s01_*``;
  ``test_shop_wide_collection_feature_flag.py::test_wb_shop_run_keeps_managed_record_coroutines``.
- [x] 8.3 `FINAL_ACCEPTANCE` (S20): один tick discover → route → inventory →
  managed + unmanaged → availability; no duplicate grains; debt safeguards cited
  in module docstring/tests.
  Evidence: ``test_shop_wide_tick_orchestration.py::test_task_83_s20_*``;
  debt cite in ``tick_wiring.py`` / ``manager.collect_shop_wide_campaign_advertising`` docstrings.

## 9. Scenario plan closure и quality gates

- [x] 9.1 `FINAL_ACCEPTANCE`: закрыть материализованный scenario plan
  `SCPV1-f61151add8956265` всеми сценариями **S01–S22** (`scenario-coverage/plan.md`);
  evidence roles согласованы с plan; durable receipt:
  `scenario-coverage/acceptance.md` + `acceptance.receipt.json` (plan lineage
  preserved — `plan.receipt.json` unchanged).
- [x] 9.2 Targeted pytest: unit routing/resolver; integration CH write attribution
  (destructive_local где применимо); write-gates **MUST** fail при удалении
  guarded condition; narrow patch boundaries (rules tasks — no mock routing
  predicate). Evidence: 82 passed (10 suites); production
  ``CampaignCollectionRouteResolver`` exercised directly.
- [x] 9.3 `poetry run pyright-strict` (0 errors); docstrings RU на новых публичных
  модулях/методах/тестах; ссылка на debt file в orchestrator/resolver module
  docstring (`route_resolver.py`, `tick_wiring.py`, all `shop_wide_collection/*`).
