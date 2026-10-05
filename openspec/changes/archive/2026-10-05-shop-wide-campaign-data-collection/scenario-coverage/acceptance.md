# Scenario Acceptance Evidence

```text
SCENARIO_ACCEPTANCE_RECEIPT

TASK_ID: WB-SKY-CAMPAIGN-COLLECTION-FINAL-CLOSURE-20261005-0440
CHANGE_ID: shop-wide-campaign-data-collection
MODE: certify (bounded local execution; no live PG/CH/WB)
STATUS: COMPLETE
DATE: 2026-10-05
PLAN_EVIDENCE_ID: SCPV1-f61151add8956265
PLAN_RECEIPT_INTEGRITY: CURRENT (PLAN_CONTENT_HASH unchanged)
IMPLEMENTATION_FRONTIER: VERIFY / merge-review
PROVEN_COMPLETE: §1–§9.3
```

Durable scenario plan `plan.md` / `plan.receipt.json` **preserved** (planning
lineage unchanged). This artifact closes §9.1 `FINAL_ACCEPTANCE` by mapping
**S01–S22** to executed unit/scenario-seam tests and production modules.
Chat-only closure is **not** SoT — see `acceptance.receipt.json`.

## Execution summary

| Gate | Result |
|------|--------|
| Targeted pytest (10 shop_runner suites) | 82 passed |
| `poetry run pyright-strict` | 0 errors |
| `openspec validate shop-wide-campaign-data-collection --strict` | PASS |
| `git diff --check` | PASS |
| Plan receipt `PLAN_CONTENT_HASH` | `ad9cc431…dd4387` CURRENT |
| Resolver uses production `CampaignCollectionRouteResolver` (not mocked predicate) | YES |
| Write-gates fail-closed under guarded conditions | YES (feature_flag + route_write_gate tests) |
| Debt cite in orchestrator/resolver modules | YES |

## S01–S22 evidence matrix

Evidence roles: `LEGACY_BASELINE` | `TARGET_REGRESSION` | `FINAL_ACCEPTANCE`.
Production modules cited where seam enters real resolver/gate/orchestration logic.

| Scenario | Role | Primary test IDs | Production seam |
|----------|------|------------------|-----------------|
| S01 | FINAL_ACCEPTANCE | `test_task_82_s01_*`, `test_wb_shop_run_keeps_managed_record_coroutines` | `WBShop.run`, `tick_wiring.run_shop_wide_unmanaged_tick` |
| S02 | TARGET_REGRESSION | `test_task_32_s02_*`, `test_wb_only_id_unmanaged_for_full_adv_not_clusters` | `route_resolver.CampaignCollectionRouteResolver` |
| S03 | TARGET_REGRESSION | `test_finished_and_unmapped_campaigns_are_upserted` | `inventory_upsert`, WB discovery mapping |
| S04 | TARGET_REGRESSION | `test_task_33_s04_*`, `test_sync_created_loader_row_managed_despite_bot_active_false` | `route_resolver` |
| S05 | TARGET_REGRESSION | `test_task_34_s05_*`, `test_refused_loader_universe_managed_for_both_grains` | `route_resolver` |
| S06 | TARGET_REGRESSION | `test_task_35_s06_s07_*`, `test_done_enrollment_absent_from_loader_unmanaged_when_discovered` | `route_resolver` |
| S07 | TARGET_REGRESSION | (same as S06 — `test_task_35_s06_s07_*`) | `route_resolver` |
| S08 | TARGET_REGRESSION | `test_task_36_s08_*`, `test_search_leg_managed_when_parent_in_loader` | `route_resolver`, `ComplexAdv.all_adv_ids` |
| S09 | TARGET_REGRESSION | `test_task_37_s09_*` | `route_resolver.is_unmanaged_collector_write_eligible` |
| S10 | TARGET_REGRESSION | `test_task_42_s10_*`, `test_record_collectors_do_not_reach_forbidden_management_writes` | `unmanaged_orchestrator`, write-gate L8 |
| S11 | TARGET_REGRESSION | `test_task_61_s11_*`, `test_task_63_integration_append_only_partial_failure_multi_campaign` | `unmanaged_orchestrator`, `availability_append` |
| S12 | TARGET_REGRESSION | `test_task_62_s12_*` | `full_adv_read_latest.load_read_latest_full_adv_facts` |
| S13 | TARGET_REGRESSION | `test_task_43_s13_*`, `test_orchestrator_module_forbids_forbidden_imports` | `unmanaged_orchestrator` |
| S14 | TARGET_REGRESSION | `test_task_52_s14_*` | `managed_record_contract`, resolver overlap |
| S15 | TARGET_REGRESSION | `test_task_38_s15_*`, `test_neither_managed_nor_discovered_resolves_unknown_fail_closed` | `route_resolver` UNKNOWN fail-closed |
| S16 | TARGET_REGRESSION | `test_task_71_s16_*` | `route_handoff` post-connect |
| S17 | TARGET_REGRESSION | `test_task_72_s17_*`, `test_task_44_route_epoch_*`, `test_route_write_gate_pure_*` | `route_write_gate` pre-write gate |
| S18 | TARGET_REGRESSION | `test_task_73_s18_*` | `route_handoff` done → unmanaged |
| S19 | TARGET_REGRESSION | `test_task_74_s19_*` | `route_handoff` refused stability |
| S20 | FINAL_ACCEPTANCE | `test_task_83_s20_*`, `test_inventory_upsert_is_wired_via_shop_runner_tick` | full tick orchestration |
| S21 | TARGET_REGRESSION | `test_task_39_s21_*` | `route_resolver` (no bot_active surrogate) |
| S22 | TARGET_REGRESSION | `test_task_75_s22_*` | `route_transition_reconcile` |

## Supporting suites (§9.2)

| Suite | Scope |
|-------|--------|
| `test_shop_campaign_inventory_ddl.py` | DDL **007** qualification, append-only availability |
| `test_shop_campaign_inventory_upsert.py` | L3 inventory upsert, route_version epoch |
| `test_shop_wide_collection_feature_flag.py` | Fail-closed ON gate, rollback managed-only |
| `test_legacy_record_collection_baseline.py` | LEGACY_BASELINE §1, write-gates L8 |
| `test_managed_path_preservation.py` | L4 managed RECORD preservation |

## Ownership invariants (verified by tests)

- Campaign change **MUST NOT** write `wb_common_stat` / funnel (`test_task_43_s13_*`, import guard).
- Common-sales `(nmid, date)` writer remains **`shop-wide-common-sales-collection`**.
- No AdvSetting create / `bot_active` mutation from collection path.
- Sole route epoch SoT: `shop_campaign_inventory.route_version` (not Redis).

## GENERATED_FROM

- `scenario-coverage/plan.receipt.json`: `SCPV1-f61151add8956265`
- `tasks.md` §1–§8 evidence citations (2026-10-05 apply)
- Test execution: bounded local pytest 2026-10-05 (82 passed)
