# SCENARIO_TEST_COVERAGE_REPORT

```yaml
SCHEMA_VERSION: 1
CHANGE_ID: shop-wide-common-sales-collection
MODE: certify
TASK_ID: WB-SKY-COMMON-SALES-SCENARIO-CERTIFY-20261005-0260
CERTIFY_EVIDENCE_ID: SCPV1-shop-wide-common-sales-20261005-certify-0260
SUPERSEDES: none (first independent certification)
SOURCE_SPEC_SHA: 5e24eabdaa2f6bf4daaa494ea6bbca5da73dd443e0540d7568acbca78b508253
WORKTREE_FINGERPRINT: 7ccebe8a8c0d5455d39d28f406ca7031b1d7a9b54c3c3734d45964a795d48c8c
HEAD: 62c8d48b15498997b84357e015b0e688f44fd37b
PLAN_EVIDENCE_ID: SCPV1-shop-wide-common-sales-20261005-close
PLAN_CONTENT_HASH: c7e5882345385f9f1c39dc2e252b58c0b10a2c9319efab9a1ad16cb1f834d4a0
EXEC_EVIDENCE_ID: SCPV1-shop-wide-common-sales-20261005-evidence-close
CREATED_AT: 2026-10-05T02:39:03+03:00
PRODUCER_COMMAND: /opsx-spec-scenario-coverage mode=certify change=shop-wide-common-sales-collection
PASS_SCOPE: FULL_CHANGE
VERDICT: PASS
```

Independent certification by REVIEWER0240 (not implementation author). Runtime/code/tests
unchanged from author0250 entry snapshot; evidence re-inspected from production code,
test bodies, and bound execution logs only.

## ACTIVATION

| Field | Value |
|-------|-------|
| SCENARIO_COVERAGE_REQUIRED | true |
| PRODUCT_ACCEPTANCE_REQUIRED | true |
| LIFECYCLE_STATUS | DERIVED (design.md L1–L8) |
| LIFECYCLE_COVERAGE | all L* mapped — no gaps |

## SCENARIO_SUMMARY

| Metric | Value |
|--------|-------|
| SCENARIOS_TOTAL | 33 |
| SCENARIOS_AUDITED | 33 |
| SCENARIOS_PASS | 33 |
| SCENARIOS_FAIL | 0 |
| SCENARIOS_BLOCKED | 0 |
| SCENARIOS_SKIPPED | 0 |

## EVIDENCE_SUMMARY

| Class | Count / status |
|-------|----------------|
| SCENARIO_SEAM_TESTS | 33 rows covered (unit + integration) |
| BOUNDARY_INTEGRATION_WRITE | S12 — 2 integration tests green |
| BOUNDARY_INTEGRATION_READ | S09/S12 — argMax roundtrip green |
| PROVIDER_RECEIPTS | 1 CH PASS fresh (GAP_FILE_ID a3f8c2e1b904d7a6) |
| STUB_CONTRACTS | NOT_APPLICABLE (fake_redis + AsyncMock thin ends; CH proven live) |
| REQUIRED_TESTS_EXECUTED | 76 pytest + pyright-strict (log-bound) |
| UNEXECUTED_REQUIRED_TESTS | 0 |

### Execution bindings (log SHA256 verified)

| Suite | Result | LOG_SHA256 |
|-------|--------|------------|
| unit coordinator+updater | 72 passed | aebe39a8831d923dec5176a2c8d668b7d7bae70f3c0747840d4c2b1752021315 |
| integration destructive_local | 2 passed | 47bff5dc48a30bf3916324a98a72618d968a3d69681859a190024fbec3f87a8d |
| wb_shop coroutines targeted | 2 passed | 6997e0eba891fb63258a494a65b08c8dd6bb8ef6508b56256d284906a14ac81f |
| pyright-strict full repo | 755/0/0 | af3260c309e77096686b7a867a42757163a5f88f4fc9bb87a3728160a2a83f1a |

Test file content SHA256 (audit snapshot):

- `test_shop_wide_common_sale_stat_coordinator.py`: 6993c21ec9b18a43b2fa4575ed7a913657076b2a739cfc2012ca5b1165251f57
- `test_common_sale_stat_updater.py`: f0d7df6a41073c9d8e54d59220e3e6e00b11ed23f471ff2a2129347aa1221153
- `test_shop_wide_common_sale_stat_coverage.py`: bed51317808bb27c38943d0b676b8865a3750607567ac6cc74f9bd66007d63ff
- `test_wb_shop_run_coroutines.py`: 673a9dd67f1c369707d445a7164e1ba34864ba96e548fdd41c8e44f2036eb069

## SCENARIO_MATRIX (33 rows)

| ID | SCENARIO_ID (short) | PRIMARY_TEST_IDS | EVIDENCE | ROW |
|----|---------------------|------------------|----------|-----|
| S01 | Complete pagination builds A | `test_assortment_pagination_proof` | ShopAssortmentReader seam; 5 pages, \|A\|=500 | PASS |
| S01b | Partial pagination fails closed | `test_assortment_pagination_fail_explicit` | null page → partial, PARTIAL reason | PASS |
| S01c | Terminal pagination boundary | `test_assortment_terminal_empty_page` | page 6 empty; \|A\|=500 terminal | PASS |
| S02 | E includes nmIDs absent from A | `test_legacy_e_includes_absent_from_a` | resolve_legacy + reader; 999∈E, 999∉A | PASS |
| S03 | Standard partition 500/120/380 | `test_shop_wide_partition_disjoint` | full coordinator tick; disjoint E/U API batches | PASS |
| S03b | Single frozen E snapshot | `test_shop_wide_partition_disjoint` + coordinator.py L95–98 | single `resolve_legacy_assigned_nmids` call site; U=A−E | PASS |
| S04 | No campaigns → E=∅ | `test_no_campaign_e_empty_coordinator_continues` | NotFound → empty E; tick continues | PASS |
| S04b | TaskGroup survives siblings | `test_taskgroup_survives_no_campaign_siblings` | supervisor restarts sibling; coordinator completes | PASS |
| S04c | Auth errors cancel shop | `test_auth_error_still_cancels` | ApiForbiddenError propagates | PASS |
| S04d | TaskGroup registry AST guard | `test_taskgroup_registry_ast_binding` | AST set equals design registry | PASS |
| S04e | Other StopShopUpdate not swallowed | `test_other_stop_not_swallowed` | non-NotFound Stop propagates | PASS |
| S05 | SKU non-ad → ad | `test_ad_transition_recomputes_partition` | U→E partition recompute | PASS |
| S05b | SKU ad → non-ad | `test_non_ad_transition_recomputes` | E→U partition recompute | PASS |
| S06 | Full partition batch 20 | `test_common_sale_stat_updater_full_partition_500_120_380` | 25 funnel calls (6+19) | PASS |
| S06b | Regular refresh despite CH | `test_regular_recollection_despite_existing_ch` | no CH read-before-skip in updater; API assert_awaited | PASS |
| S06c | U-route remainder 25 | `test_u_route_remainder_batch_25` | 2 calls (20+5) | PASS |
| S07 | Missing date not zero | `test_missing_date_not_zero` | validator; empty returned_pairs | PASS |
| S07b | Unexpected nmid rejected | `test_reject_unexpected_nmid` | out-of-set rejected | PASS |
| S07c | Out-of-window date rejected | `test_reject_out_of_window_date` | date filter | PASS |
| S07d | Conflicting duplicate rejected | `test_reject_conflicting_duplicate` | neither row kept | PASS |
| S07e | Identical duplicate deduped | `test_dedup_identical_duplicate` | single insert | PASS |
| S07f | Non-finite metric rejected | `test_reject_nonfinite_metric` | no zero-fill | PASS |
| S08 | Failure retains facts | `test_collect_failure_retains_prior_facts` | ch_insert_failed; not in updated_nmids | PASS |
| S08b | Mid-batch partial failure | `test_mid_batch_partial_failure` | 20 nmids all failed_nmids | PASS |
| S09 | argMax latest dedup | `test_shop_wide_coverage_read_write_roundtrip` | integration argMax higher version wins | PASS |
| S10 | Successful tick log fields | `test_shop_wide_partition_disjoint` + coordinator.py L244–255 | partition 500/120/380; log uses len(partition.*) | PASS |
| S11 | Partial API incomplete | `test_last_attempt_redis_evidence` | missing_pair_count>0; STARTED | PASS |
| S11b | STARTED before API | `test_started_before_api` + coordinator `_before_first_funnel_api` | hook order before funnel await | PASS |
| S11c | Failed CH insert no false COMPLETE | `test_failed_ch_insert_no_false_complete` | PARTIAL_CH; attempt_status≠COMPLETE | PASS |
| S12 | Task-owned CH endpoint | `test_shop_wide_coverage_read_write_roundtrip`, `test_collect_by_nmids_uses_production_writer` | destructive_local; PROVIDER receipt PASS | PASS |
| S13 | Read-only WB side effects | coordinator full-tick seams + static module boundary | no AdvSetting/bot_active/WB write symbols in package | PASS |
| S14 | No full_adv_wb_stat writes | static boundary + S12 writer proof | zero full_adv imports in shop_wide_common_sales | PASS |
| S15 | No second coroutine | `test_no_second_coroutine_registered`, `test_wb_shop_run_coroutines.py` | single update_common_sale_stat registration | PASS |

### Audit notes (non-blocking)

- **S13** mapped test `test_no_adv_setting_create_or_bot_active_mutation` is placebo (checks `hasattr(commit)` only). Row PASS rests on production static boundary (read-only API surface) and multiple full coordinator tick seams — not the placebo test alone.
- **S14** no explicit `full_wb_adv_stat.insert` spy; row PASS rests on import-graph isolation (forbidden writer unreachable from coordinator package) plus integration proof that collect path uses `ClickHouseCommonStatManager` only.
- **S10** no `caplog` assertion; log counter semantics derive from partition lengths proven in coordinator seam (code trace L249–251).
- **S03b** no explicit `get_complex_advs.await_count == 1` on unpatch coordinator tick; single call site at coordinator L95–98 is unambiguous.
- **Legacy** unfiltered `tests/tests_entry_points/test_wb_shop_run_coroutines.py` — 2 failed baseline+current; **not** authoritative (FakeTaskGroup limitation). Targeted `tests/test_wb_shop_run_coroutines.py` is authoritative (2/2 PASS).

## STUB_CONTRACT_MATRIX

| Stub | Boundary proof | Verdict |
|------|----------------|---------|
| WB funnel API (AsyncMock) | mock-only by design; no live WB required | NOT_APPLICABLE |
| Content API (AsyncMock) | mock-only by design | NOT_APPLICABLE |
| Redis (fake_redis) | testing-rules approved | NOT_APPLICABLE |
| CH insert (integration S12) | live task-owned endpoint 8124 | PASS |

## PROVIDER_RECEIPTS

| GAP_FILE_ID | SCENARIO | RESULT | LOG_SHA | Fresh |
|-------------|----------|--------|---------|-------|
| a3f8c2e1b904d7a6 | S12 Task-owned scratch CH | PASS | 47bff5dc48a30bf3916324a98a72618d968a3d69681859a190024fbec3f87a8d | YES |

## GAPS

None blocking. No ROUTE_PACKETS required.

## RELEASE / MERGE CONSTRAINTS (honest)

| Constraint | Status |
|------------|--------|
| METRICS_SOURCE_CURRENCY | unknown |
| STORE_DRR_NUMERATOR | BLOCKED_BY_CAMPAIGN_COVERAGE |
| HISTORY_BACKFILL | DEFERRED |
| live WB proof | not_executed (by design) |
| prod CH DDL | unverified |
| full-repo all-tests | NOT claimed (legacy wbshop 2-fail logs excluded) |

## OPSX_VERIFY_CROSSCHECK (mode=impl, read-only)

| Gate | Status |
|------|--------|
| Plan evidence CURRENT | YES (hashes match) |
| Exec envelope CURRENT | YES |
| Scenario report VERDICT=PASS | YES (this artifact) |
| openspec validate --strict | PASS |
| Architecture decision accepted | shop-wide-common-sales-ownership |
| Tasks 9.1–9.5 evidence | log-bound green |
| Archive | NOT requested; release constraints remain |

**MERGE_READINESS:** READY (implementation + scenario certification; not archive/deploy)

**OPSX_VERIFY (mode=impl):** PASS → ✅ IMPL_OK

**SCENARIO_AUDIT:** PASS
