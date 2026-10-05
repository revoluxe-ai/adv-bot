# Case-to-test index (33 scenarios)

TASK_ID: WB-SKY-COMMON-SALES-EVIDENCE-CLOSE-20261005-0250
SOURCE_PLAN: `scenario-coverage/plan.md` (PLAN_EVIDENCE_ID `SCPV1-shop-wide-common-sales-20261005-close`)
SCENARIO_COUNT: 33
PURPOSE: independent audit input — maps plan scenarios to authored test ids.
VERDICT: **not issued** (preparation only).

## Primary test files

| File | Role |
|------|------|
| `tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py` | S01–S11c, S13–S15, F-pagination/evidence guards |
| `tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py` | S06 legacy ComplexAdv path regression |
| `tests/integration/test_shop_wide_common_sale_stat_coverage.py` | S09/S12 CH write+read |
| `tests/test_wb_shop_run_coroutines.py` | S04b/S15 adjacent TaskGroup registry |

## Scenario rows

| Scenario | Test id(s) | Notes |
|----------|------------|-------|
| S01 | `test_assortment_pagination_proof` | |
| S01b | `test_assortment_pagination_fail_explicit` | |
| S01c | `test_assortment_terminal_empty_page` | |
| S02 | `test_legacy_e_includes_absent_from_a` | |
| S03 | `test_shop_wide_partition_disjoint` | |
| S03b | `test_shop_wide_partition_disjoint` (frozen snapshot asserts) | |
| S04 | `test_no_campaign_e_empty_coordinator_continues` | |
| S04b | `test_taskgroup_survives_no_campaign_siblings` | also `tests/test_wb_shop_run_coroutines.py` |
| S04c | `test_auth_error_still_cancels` | |
| S04d | `test_taskgroup_registry_ast_binding` | |
| S04e | `test_other_stop_not_swallowed` | |
| S05 | `test_ad_transition_recomputes_partition` | |
| S05b | `test_non_ad_transition_recomputes` | |
| S06 | `test_common_sale_stat_updater_chunks_and_inserts` | updater file |
| S06b | `test_regular_recollection_despite_existing_ch` | |
| S06c | `test_u_route_remainder_batch_25` | |
| S07 | `test_missing_date_not_zero` | |
| S07b | `test_reject_unexpected_nmid` | |
| S07c | `test_reject_out_of_window_date` | |
| S07d | `test_reject_conflicting_duplicate` | |
| S07e | `test_dedup_identical_duplicate` | |
| S07f | `test_reject_nonfinite_metric` | |
| S08 | `test_collect_failure_retains_prior_facts` | |
| S08b | `test_mid_batch_partial_failure` | |
| S09 | `test_shop_wide_coverage_read_write_roundtrip` | integration argMax |
| S10 | `test_shop_wide_partition_disjoint` (log counter fields) | |
| S11 | `test_last_attempt_redis_evidence` | |
| S11b | `test_started_before_api` | |
| S11c | `test_failed_ch_insert_no_false_complete` | |
| S12 | `test_shop_wide_coverage_read_write_roundtrip`, `test_collect_by_nmids_uses_production_writer` | destructive_local CH |
| S13 | `test_no_adv_setting_create_or_bot_active_mutation` | |
| S14 | architecture-only (coordinator uses CommonSaleStatUpdater only) | no dedicated assert test |
| S15 | `test_no_second_coroutine_registered`, `tests/test_wb_shop_run_coroutines.py` | |

## Open audit notes for independent reviewer

- **S14**: evidence is architectural + coordinator test matrix; confirm adequate or gap.
- **S09**: covered via integration roundtrip (plan allows unit+integration).
- **Legacy regression**: `test_common_sale_stat_updater.py` must remain green (included in 72 suite).
- **WBShop unfiltered legacy logs**: 2 failed — not substitute for S04b/S15 targeted tests.

## NEXT (independent)

```text
/opsx-spec-scenario-coverage mode=audit change=shop-wide-common-sales-collection
```
