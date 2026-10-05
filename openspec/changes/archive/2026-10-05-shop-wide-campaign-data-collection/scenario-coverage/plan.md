# Scenario Coverage Plan

CHANGE_ID: shop-wide-campaign-data-collection
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-f61151add8956265
PLAN_SUPERSEDES: SCPV1-0e11e1d5c3a8b2bb
PLAN_INVALIDATION_REASON: migration sequence reconcile (2026-10-05) — design Migration Plan records CH DDL 007 and control-plane terminology; scenario matrix unchanged from SCPV1-0e11e1d5c3a8b2bb common-sales boundary.
LIFECYCLE_STATUS: DERIVED

This is required-evidence planning only. It does not claim that any listed
test has been authored, executed, or passed.

## Ownership boundary (campaign vs common-sales)

| Owner | Scope |
|-------|--------|
| **`shop-wide-common-sales-collection`** | Shop-wide product/funnel expansion `(nmid, date)`, assortment universe, uncovered routing, common collector, `wb_common_stat` writer, common-sales coverage; coordinator for legacy `CommonSaleStatUpdater` |
| **`shop-wide-campaign-data-collection` (this change)** | WB campaign discovery, inventory/availability, campaign advertising universe, `full_adv_wb_stat` `(adv_id, date)`, managed-only `clusters_adv_stats` |

Campaign scenarios **MUST NOT** require unmanaged `ClickHouseCommonStatManager.insert`
or `get_sales_funnel_products_history` as campaign change write obligations.

## Lifecycle coverage

Derived Lifecycle from `design.md` (`LIFECYCLE_STATUS: DERIVED`):

| Step | Behavior | Mapped scenarios |
|------|----------|------------------|
| L1 Discover WB | WB API campaign discovery | S01, S03, S20 |
| L2 Route | MANAGED / UNMANAGED / UNKNOWN per grain | S02–S09, S15, S19, S20 |
| L3 Inventory | Upsert shop_campaign_inventory including route_version | S15, S17, S20, S22 |
| L4 Collect managed | Legacy RECORD coroutines | S01, S05, S08, S14, S20 |
| L5 Collect unmanaged | Minimal read-only campaign advertising safe seams (`full_adv_wb_stat` only; **not** `wb_common_stat`) | S02, S06, S07, S09, S10, S13, S18, S20 |
| L6 Availability | Append availability rows, including the checked route_version | S11, S12, S15, S17, S20, S22 |
| L7 Handoff | Non-atomic ownership transfer | S16, S17, S18, S19, S22 |
| L8 Invariants | No management writes from collection | S01, S04, S10, S20, S21 |

LIFECYCLE_COVERAGE: all material L1–L8 steps covered by spec scenarios; no SPEC_SCENARIO_MISSING.

## Steady-state / reconcile

- **Read-side recovery (observe):** «Read-side после ошибки» (S12) — already-true prior success with failed latest attempt; read-latest MUST retain last success.
- **Periodic reconcile tick:** «Сбор при активном shop-runner» (S01) and «Полный цикл…» (S20) — periodic shop-runner cycle without requiring a fresh connect/disconnect event.
- **Overlap write gate:** «Overlap window при connect» (S17) — before the fact-grain write, check current `shop_campaign_inventory.route_version` and collection ownership. Stale epoch or ownership mismatch MUST NOT write fact grain. The availability row of that attempt MUST carry the same checked `route_version` and MUST NOT replace the fact-write ban. Read-latest MUST NOT double-count declared grains. S17 is the in-flight pre-write gate and is not the already-true post-switch reconcile.
- **Post-switch already-true reconcile:** «Reconciliation read-latest при уже переключённом маршруте» (S22) — GIVEN the route is already switched and dual-leg history exists, with no fresh connect or disconnect in this scenario; WHEN the periodic or reconcile entry runs; THEN read-latest grains of that dual-leg history are compared, a discrepancy MUST be recorded on availability with `reason_code` `route_transition_reconcile`, and read-latest MUST NOT double-count declared grains. If the checked `route_version` is stale or collection ownership does not match the collector route, the system MUST NOT write the fact grain. The availability row MUST carry that checked `route_version`. S16–S19 remain transition producers. The former `MISSING_STEADY_STATE_RECONCILE_SCENARIO` gap is closed by S22.

Shared evidence rules (all scenarios):
- Entry via shop-runner (`WBShop.run` / `CoroutinesManager`); scripts/Job MUST NOT appear as primary executor.
- Collection ownership routing via legacy loader predicate (`active_status != done`, nmids post-filter, search_adv_id map); distinct from management relationship.
- Forbidden: AdvSetting create from collection, bot_active mutation, WB management writes, `update_advs_in_db` for discovery expansion, whole `ClustersAdvStatUpdater` on unmanaged path.
- CH grains (campaign change): `full_adv_wb_stat` (adv_id, date) without shop_id; clusters out of unmanaged initial slice. `wb_common_stat` (nmid, date) — owner **`shop-wide-common-sales-collection`**; campaign **MUST NOT** second writer.
- Non-atomic handoff. Sole durable route epoch is `shop_campaign_inventory.route_version`. Redis MAY lock or coordinate and MUST NOT be a second epoch source of truth. Before a fact-grain write the collector MUST read the current `route_version` and collection ownership. If the epoch is stale or ownership does not match the collector route, the collector MUST NOT write the fact grain. An in-flight fact write MAY complete only when `route_version` is still current at write time and ownership matches. The availability row of that attempt MUST carry the same checked `route_version` and MUST NOT replace the fact-write ban. Version/timestamp is not business idempotency.
- Debt reference: openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md
- MAPPED_TEST_IDS: NOT_YET; EXECUTION: NOT_EXECUTED; ROW_VERDICT: planned

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: shop-wide-campaign-data-collection
SOURCE_SPEC_SHA: 1104371ec73e146256cbba8f42ae57f48f16415f3bdbbc844b4bd84392eb9679
PLAN_STATUS: ready

### S01 — Сбор при активном shop-runner

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Сбор при активном shop-runner`
LIFECYCLE_STEPS: L1,L4,L8
GIVEN_WHEN_THEN: Spec scenario «Сбор при активном shop-runner» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: WBShop.run / CoroutinesManager shop-wide tick
CAUSAL_PATH: Periodic shop-runner cycle initiates WB discovery and collectors; MUST NOT delegate to scripts/Job.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S02 — Кампания только в WB API

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Кампания только в WB API`
LIFECYCLE_STEPS: L2,L5
GIVEN_WHEN_THEN: Spec scenario «Кампания только в WB API» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: CampaignCollectionRouteResolver + unmanaged collectors
CAUSAL_PATH: WB-only id not in legacy ownership → unmanaged path facts; no AdvSetting create.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S03 — Завершённая кампания в WB

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Завершённая кампания в WB`
LIFECYCLE_STEPS: L1,L2
GIVEN_WHEN_THEN: Spec scenario «Завершённая кампания в WB» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: CampaignsInfoV2Adapter discovery in shop-runner
CAUSAL_PATH: Finished WB lifecycle still in discovery; not excluded for lack of management.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S04 — Sync-created enrollment без user connect

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Sync-created enrollment без user connect`
LIFECYCLE_STEPS: L2,L8
GIVEN_WHEN_THEN: Spec scenario «Sync-created enrollment без user connect» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: get_complex_advs(only_bot_active=False) routing
CAUSAL_PATH: Sync enrollment in loader → managed collection; management relationship not proven.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S05 — Refused enrollment остаётся на managed path

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Refused enrollment остаётся на managed path`
LIFECYCLE_STEPS: L2,L4
GIVEN_WHEN_THEN: Spec scenario «Refused enrollment остаётся на managed path» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: WBShopDataManager.__get_advs + resolver
CAUSAL_PATH: refused in loader → managed; unmanaged MUST NOT duplicate grain.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S06 — Done enrollment выпадает из managed path

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Done enrollment выпадает из managed path`
LIFECYCLE_STEPS: L2,L5
GIVEN_WHEN_THEN: Spec scenario «Done enrollment выпадает из managed path» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Resolver vs __get_advs predicate
CAUSAL_PATH: done drops from loader → unmanaged when WB-discovered.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S07 — Нет enrollment — unmanaged при WB discovery

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Нет enrollment — unmanaged при WB discovery`
LIFECYCLE_STEPS: L2,L5
GIVEN_WHEN_THEN: Spec scenario «Нет enrollment — unmanaged при WB discovery» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Resolver UNMANAGED branch
CAUSAL_PATH: No PG row + WB id → unmanaged; not treated as non-existent.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S08 — Search-нога на managed path для full advertising grain

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Search-нога на managed path для full advertising grain`
LIFECYCLE_STEPS: L2,L4
GIVEN_WHEN_THEN: Spec scenario «Search-нога на managed path для full advertising grain» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: ComplexAdv.all_adv_ids / search_adv_id map
CAUSAL_PATH: Search leg on managed full_adv_wb_stat grain; not unmanaged for same grain.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S09 — Исключение overlap ownership

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Исключение overlap ownership`
LIFECYCLE_STEPS: L2,L5
GIVEN_WHEN_THEN: Spec scenario «Исключение overlap ownership» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Resolver same-tick grain exclusion
CAUSAL_PATH: Managed ownership → unmanaged MUST NOT CH write same grain same cycle.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S10 — Unmanaged сбор без enrollment side effect

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Unmanaged сбор без enrollment side effect`
LIFECYCLE_STEPS: L5,L8
GIVEN_WHEN_THEN: Spec scenario «Unmanaged сбор без enrollment side effect» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Unmanaged slice CH writers
CAUSAL_PATH: Successful unmanaged collect → no AdvSetting create, bot_active unchanged.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S11 — Сбой одного collector

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Сбой одного collector`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: Spec scenario «Сбой одного collector» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Partial failure + availability writer
CAUSAL_PATH: One collector error → reason recorded; others continue/retry.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S12 — Read-side после ошибки

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Read-side после ошибки`
LIFECYCLE_STEPS: L6
GIVEN_WHEN_THEN: Spec scenario «Read-side после ошибки» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: argMax/read-latest query contract
CAUSAL_PATH: Last failed attempt + prior success → read-side uses last success until newer success.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S13 — WB-only кампания без cluster stats

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: WB-only кампания без cluster stats`
LIFECYCLE_STEPS: L5
GIVEN_WHEN_THEN: Spec scenario «WB-only кампания без cluster stats» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Unmanaged collectors (no ClustersAdvStatUpdater)
CAUSAL_PATH: Unmanaged writes `full_adv_wb_stat` only; MUST NOT write `wb_common_stat` / funnel (common-sales owner); MUST NOT write clusters_adv_stats.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S14 — Managed refused с полным legacy coverage

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Managed refused с полным legacy coverage`
LIFECYCLE_STEPS: L4,L5
GIVEN_WHEN_THEN: Spec scenario «Managed refused с полным legacy coverage» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Managed coroutines incl. update_clusters_adv_stats_*
CAUSAL_PATH: refused managed → clusters allowed; unmanaged no duplicate full_adv grain.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S15 — Неоднозначная классификация

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Неоднозначная классификация`
LIFECYCLE_STEPS: L2,L3,L6
GIVEN_WHEN_THEN: Spec scenario «Неоднозначная классификация» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: UNKNOWN route + inventory/availability
CAUSAL_PATH: After retry UNKNOWN → inventory upsert + availability; no enrollment create.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S16 — User connect переводит collection на managed

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: User connect переводит collection на managed`
LIFECYCLE_STEPS: L7
GIVEN_WHEN_THEN: Spec scenario «User connect переводит collection на managed» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: connect_existing_advs + next-tick resolver
CAUSAL_PATH: Post-connect in loader → managed next tick; unmanaged no new writes on owned grains.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S17 — Overlap window при connect

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Overlap window при connect`
LIFECYCLE_STEPS: L3,L6,L7
GIVEN_WHEN_THEN: WHEN an unmanaged batch started before commit connect AND the collector is ready to write fact grain; THEN before that write it MUST check current `shop_campaign_inventory.route_version` and collection ownership; stale epoch or ownership mismatch MUST NOT write fact grain; in-flight fact write MAY complete only when `route_version` is still current and ownership matches the collector route; the availability row of this attempt MUST carry that same `route_version` and MUST NOT replace the fact-write ban; read-latest MUST NOT double-count declared grains.
PRODUCTION_ENTRYPOINT: shop-runner collector pre-write gate reading `default_db.shop_campaign_inventory.route_version` and collection ownership
CAUSAL_PATH: In-flight unmanaged batch overlaps a connect. Before the fact-grain write, the collector reads the current inventory `route_version` and collection ownership. Stale epoch or ownership mismatch MUST NOT write fact grain. In-flight fact write MAY complete only if `route_version` is still current at write time and ownership matches the collector route. The availability row of this attempt MUST carry that same checked `route_version`. That availability row MUST NOT replace the fact-write ban. Read-latest MUST NOT double-count declared grains. Redis MUST NOT be a second route-epoch source of truth.
THIN_ENDS: CH fact-grain insert `full_wb_adv_stat.insert` (campaign scope) — refused on stale epoch or ownership mismatch; availability writer on `default_db.shop_campaign_collection_availability` — required and must persist the checked `route_version`; inventory read of `route_version` (epoch SoT). WB transport may be stubbed only after the gate decision. `wb_common_stat` — common-sales change, not campaign gate.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Seam through the real pre-write gate. Assert MUST NOT write fact grain when `route_version` is stale or ownership mismatches. Assert fact grain MAY be written only when `route_version` is still current and ownership matches. Assert the availability row of the attempt carries that same checked `route_version` and does not count as the fact-grain write.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity where stubbed. The route_version/ownership gate itself MUST NOT be stubbed.
  BOUNDARY_INTEGRATION_WRITE: CH fact-grain attribution. Stale epoch or ownership mismatch persists no fact grain. A still-current `route_version` with matching ownership may persist the fact. Availability append is a separate write and MUST NOT be accepted as the fact-grain write.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest on declared grains MUST NOT double-count across the overlap window.
  BOUNDARY_INTEGRATION_OTHER: Availability row for the attempt stores the same `route_version` read from `shop_campaign_inventory` at the pre-write check, including when the fact-grain write is refused.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials. Sole epoch SoT is inventory `route_version`. Redis lock is not a second epoch.
MOCKING_CONSTRAINTS: Do not mock away the pre-write `route_version` and ownership gate. Do not treat an availability append as the fact-grain write.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S18 — Disconnect done переводит на unmanaged

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Disconnect done переводит на unmanaged`
LIFECYCLE_STEPS: L7,L5
GIVEN_WHEN_THEN: Spec scenario «Disconnect done переводит на unmanaged» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Terminal done + resolver handoff
CAUSAL_PATH: done → stop managed RECORD; continue unmanaged; CH history retained.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S19 — Refused не меняет managed ownership при disconnect-like событиях

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Refused не меняет managed ownership при disconnect-like событиях`
LIFECYCLE_STEPS: L7,L2
GIVEN_WHEN_THEN: Spec scenario «Refused не меняет managed ownership при disconnect-like событиях» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Loader refused predicate stability
CAUSAL_PATH: refused stays managed ownership; not routed unmanaged due to refused alone.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S20 — Полный цикл с WB-only и managed кампаниями

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Полный цикл с WB-only и managed кампаниями`
LIFECYCLE_STEPS: L1,L2,L3,L4,L5,L6,L8
GIVEN_WHEN_THEN: Spec scenario «Полный цикл с WB-only и managed кампаниями» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Full shop-runner tick orchestration
CAUSAL_PATH: One tick: discover→route→inventory→managed+unmanaged→availability; no duplicate grains.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S21 — Отсутствие surrogate proof of connect

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Отсутствие surrogate proof of connect`
LIFECYCLE_STEPS: L8
GIVEN_WHEN_THEN: Spec scenario «Отсутствие surrogate proof of connect» (exact G/W/T in delta spec).
PRODUCTION_ENTRYPOINT: Routing invariant guards
CAUSAL_PATH: No bot_active/presence-only as connect proof; no new PG provenance column.
THIN_ENDS: WB API adapters (CampaignsInfoV2, wb_data_getter); CH insert path `full_wb_adv_stat` (campaign scope); inventory/availability writers; PG read for loader only. `wb_common_stat` / funnel — **`shop-wide-common-sales-collection`**, not campaign unmanaged.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Unit/integration seam exercising real resolver and collector orchestration for this scenario; assert allowed/forbidden effects per spec.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity tests where stubbed; no stub of routing predicate or forbidden-write guards.
  BOUNDARY_INTEGRATION_WRITE: CH write attribution for in-scope grains (destructive_local where applicable); prove no forbidden PG writes.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest queries for recovery and overlap cases where scenario requires read-side behavior.
  BOUNDARY_INTEGRATION_OTHER: Inventory/availability append contracts on partial failure and UNKNOWN.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials; respect TEMPORARY_DUAL_CAMPAIGN_COLLECTION debt limits.
MOCKING_CONSTRAINTS: Do not mock away collection ownership decision or forbidden management adapters.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned
### S22 — Reconciliation read-latest при уже переключённом маршруте

SCENARIO_ID: `openspec/changes/shop-wide-campaign-data-collection/specs/connected-shop-campaign-ad-data-collection/spec.md::#### Scenario: Reconciliation read-latest при уже переключённом маршруте`
LIFECYCLE_STEPS: L3,L6,L7
GIVEN_WHEN_THEN: GIVEN the campaign route is already switched and dual-leg history exists for the grain, and this scenario has no new connect or disconnect event; WHEN the periodic or reconcile entry runs; THEN the system MUST compare read-latest grains of that dual-leg history; a discrepancy MUST be recorded on availability with `reason_code` `route_transition_reconcile`; read-latest MUST NOT double-count declared grains; if the checked `route_version` is stale or collection ownership does not match the collector route, the system MUST NOT write the fact grain; the availability row MUST carry that checked `route_version`.
PRODUCTION_ENTRYPOINT: shop-runner periodic tick or post-switch reconcile entry reading current `default_db.shop_campaign_inventory.route_version` and collection ownership, then comparing argMax/read-latest dual-leg grains
CAUSAL_PATH: The route is already switched and dual-leg history already exists. No fresh connect or disconnect is the producer of this scenario. The periodic or reconcile entry compares read-latest grains. A discrepancy is appended to `shop_campaign_collection_availability` with `reason_code=route_transition_reconcile` and the checked `route_version`. Stale `route_version` or an ownership mismatch MUST NOT write the fact grain. That availability row MUST NOT replace the fact-write ban. Read-latest MUST NOT double-count declared grains. Redis MUST NOT be a second route-epoch source of truth. S17 remains the separate in-flight overlap pre-write gate.
THIN_ENDS: CH fact-grain insert `full_wb_adv_stat.insert` (campaign scope) — refused when the checked `route_version` is stale or ownership mismatches; availability writer on `default_db.shop_campaign_collection_availability` — required for `route_transition_reconcile` and must persist the checked `route_version`; inventory read of `route_version` (epoch SoT); argMax/read-latest query on campaign grains. WB transport may be stubbed only after the reconcile decision. `wb_common_stat` reconcile — common-sales change.
REQUIRED_EVIDENCE:
  SCENARIO_SEAM: Seam through the real periodic or reconcile entry with an already-switched route and existing dual-leg history, and with no fresh connect or disconnect in the scenario. Assert read-latest comparison, availability `reason_code=route_transition_reconcile` carrying the checked `route_version`, no double-count, and MUST NOT write fact grain when `route_version` is stale or ownership mismatches.
  CONTRACT_CASES: NOT_YET — name at `/opsx-test` from SCENARIO_ID hash.
  STUB_CONTRACT: WB/CH thin-end DTO parity where stubbed. The route_version/ownership check and the reconcile decision itself MUST NOT be stubbed.
  BOUNDARY_INTEGRATION_WRITE: CH fact-grain attribution. Stale checked `route_version` or ownership mismatch persists no fact grain. Availability append for `route_transition_reconcile` is a separate write and MUST NOT be accepted as the fact-grain write.
  BOUNDARY_INTEGRATION_READ: argMax/read-latest on declared dual-leg grains MUST NOT double-count after the route has already switched.
  BOUNDARY_INTEGRATION_OTHER: Availability row stores `reason_code=route_transition_reconcile` and the same `route_version` read from `shop_campaign_inventory` at the reconcile check, including when the fact-grain write is refused.
  LOAD_OR_PERFORMANCE: not_applicable
REALITY_CONSTRAINTS: Feature-flagged dual-path; no production credentials. Sole epoch SoT is inventory `route_version`. Redis lock is not a second epoch. Already-true precondition: route already switched; no fresh connect or disconnect in this scenario.
MOCKING_CONSTRAINTS: Do not mock away the reconcile read-latest comparison or the checked `route_version` and ownership gate. Do not treat an availability append as the fact-grain write. Do not satisfy this scenario with only the S17 in-flight overlap gate or with S16–S19 transition producers.
EXECUTION: NOT_EXECUTED
MAPPED_TEST_IDS: []
ROW_STATUS: planned

## Open questions and gaps

OPEN_QUESTIONS: none
UNRESOLVED_GAPS: none
ACCEPTED_PROVENANCE_GAP: AdvSetting does not prove user connect; no new PG provenance field (owner-contract + design §B.3).

## GENERATED_FROM

GENERATED_FROM:

- owner-contract.md: `2c930383860f870d6b6eadf66d00c2afb227fd31d90b8e1b6f325e8f686d41b9`
- design.md: `ed14f3def581a336c19930fbecd2b14ed5c01bee24707ac8e9e34a8a20620c55`
- specs/connected-shop-campaign-ad-data-collection/spec.md: `1104371ec73e146256cbba8f42ae57f48f16415f3bdbbc844b4bd84392eb9679`
- LIFECYCLE_REVISION source: design.md#Derived Lifecycle (LIFECYCLE_STATUS: DERIVED)
- PLAN_EVIDENCE_ID formula: `SCPV1-` + first 16 hex of sha256(LF of change_id, design hash, spec hash, owner-contract hash joined by newline). Timestamps are not inputs.
- architectural-debt: openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md (reference only; not hashed)
