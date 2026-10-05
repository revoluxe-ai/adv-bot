# Independent Scenario Test Coverage Audit Report

CHANGE_ID: ai-package-keyword-performance-history  
MODE: audit  
PASS_SCOPE: FULL_CHANGE  
PRODUCER_COMMAND: /opsx-spec-scenario-coverage mode=audit change=ai-package-keyword-performance-history run=targeted  
TASK_ID: WB-SKY-KEYWORD-HISTORY-INDEPENDENT-REAUDIT-20261005-09  
EXECUTED_AT: 2026-10-05T09:45:00+03:00  
AUDITOR: independent (supersedes SCAR-07 47PASS/4FAIL; validates repair08 cutoff/stub closure)

```text
SCENARIO_TEST_COVERAGE_REPORT:
  SCHEMA_VERSION: 1
  CHANGE_ID: ai-package-keyword-performance-history
  SOURCE_SPEC_SHA: 2ef8006acefcbb8506ce35eefca25cc0120a122f3a0efa2f6bf1caf5465682b4
  WORKTREE_FINGERPRINT: 3929cd8e9e5e22a56c2cc4ef13b64757ca413c5698a188fcc7e6fe268fb75358
  WORKTREE_HEAD_SHA: 37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0
  PLAN_EVIDENCE_ID: SCPV1-dad56a1027545bc3
  AUDIT_EVIDENCE_ID: SCAR-09independent-reaudit-20261005
  ACTIVATION:
    SCENARIO_COVERAGE_REQUIRED: true
    SCENARIO_COVERAGE_REQUIRED_REASON: materialized scenario-coverage/plan.receipt.json (SCPV1-dad56a1027545bc3); tasks.md §6.4 gates on independent audit
    PRODUCT_ACCEPTANCE_REQUIRED: false
    PRODUCT_ACCEPTANCE_REQUIRED_REASON: design.md omits PRODUCT_ACCEPTANCE_REQUIRED; on-demand read-only export (DERIVED lifecycle) without durable runtime SIDE_EFFECT_PROOF per owner-contract D-012 scope
    ACTIVATION_VERSION: OPSX_SCENARIO_TEST_COVERAGE_V1
  VERDICT: PASS
  SCENARIOS_TOTAL: 51
  SCENARIOS_AUDITED: 51
  SCENARIOS_PASS: 51
  SCENARIOS_FAIL: 0
  SCENARIOS_BLOCKED: 0
  SCENARIOS_SKIPPED: 0
  STUB_CONTRACTS_TOTAL: 6
  STUB_CONTRACTS_PASS: 6
  STUB_CONTRACTS_FAIL: 0
  STUB_CONTRACTS_NOT_APPLICABLE: 0
  REQUIRED_TESTS_EXECUTED: 132
  UNEXECUTED_REQUIRED_TESTS: 0
  LIFECYCLE_STATUS: DERIVED
```

## Freshness verification

| Check | Result |
|---|---|
| `verify_plan_evidence_repair3.py` all CHECKS true | PASS |
| SOURCE_SPEC_SHA recomputed | `2ef8006acefcbb8506ce35eefca25cc0120a122f3a0efa2f6bf1caf5465682b4` (matches plan.receipt) |
| WORKTREE_FINGERPRINT recomputed (65 paths) | `3929cd8e9e5e22a56c2cc4ef13b64757ca413c5698a188fcc7e6fe268fb75358` (matches repair08 manifest) |
| Manifest excludes evidence/report outputs | PASS (no circularity) |
| Independent pytest | `132 passed, 0 failed` |
| Pytest log | `evidence/pytest-ai-package-v1-independent-audit09.log` SHA256 `4baff5018cad462a66f2be8a22401f85467dbdf5fca30cb63b175972aed1ff42` |
| pyright strict | 0 errors, 0 warnings |
| openspec validate --strict | PASS |
| git diff --check | PASS |

## Repair08 gap closure verification (formerly FAIL rows)

| Row | Closure evidence | Executed proof |
|---|---|---|
| S45 | `test_cutoff_future_bounds_excluded_from_export_metadata` + `domain/cutoff_guard.effective_last_available` + `ch_keyword_bounds_reader._clamp_last_available` | Assembler export: future CH bounds `2026-03-01` capped to observed valid `2026-01-05` in DATA_MAP/coverage; legit row retained |
| S51 future | `test_contract_cutoff_excludes_future_date_payload` | `keyword_daily`/`keyword_positions` exclude `2026-03-01`; decision timeline excludes future cpm 999.0 |
| S51 same-day | `test_contract_cutoff_excludes_same_day_post_instant_daily_payload` | Cutoff 12Z; daily row 15Z on 2026-01-07 absent from payload |
| S51 version-ms | `test_contract_cutoff_excludes_future_position_version_payload` | Position version > cutoff_instant_ms excluded; current observation stays 2026-01-05 |
| S37/S38 stub | `test_ch_stub_contract.py` (10 cases) + `test_default_pipeline_boundary.py` (4 cases) | Production `ChKeyword*Reader`/`ChBidDecision*`/`PgAdvIdOverlapReader` invoke `FakeClickHouseClient`/`FakePgSession` at client seam; params/SQL predicates asserted; unknown SQL fail-closed; PG commit forbidden |

Production guard (`cutoff_guard.py`) verified: post-fetch filters do not drop legit in-cutoff rows; `effective_last_available` derives from valid observations only (no synthetic cutoff fill when future-only CH bounds).

## Owner criteria spot-check (26 AT — tasks.md authoritative labels)

| AT | Owner label (tasks.md) | Status | Evidence |
|---|---|---|---|
| AT-01 | Daily query history on strict grain | PASS | S01 `test_daily_grain_strict`, S02 |
| AT-02 | Full history not 7/30 clipped | PASS | S03/S39/S45/S51 payload + bounds proofs (repair08 closed) |
| AT-03 | Auto/Search not mixed | PASS | S05 |
| AT-04 | Physical adv_id preserved | PASS | S02 |
| AT-05 | Rebound history not lost | PASS | S06/S07/S40/S46 |
| AT-06 | No duplicate logical counting | PASS | S08 |
| AT-07 | Missing ≠ zero | PASS | S09 |
| AT-08 | Position missing not synthetic max | PASS | S10/S42 |
| AT-09 | Telegram/graph not used | PASS | S11/S12 |
| AT-10 | Position direction documented | PASS | S13 + export_field_matrix |
| AT-11 | Standard windows correct | PASS | S14/S17 + calendar/leap/Jan1 extras |
| AT-12 | Calendar year ≠ rolling 365d | PASS | S14 |
| AT-13 | Comparable prev windows | PASS | S15 |
| AT-14 | Insufficient history partial | PASS | S16 |
| AT-15 | Current state deterministic | PASS | S20/S47 + policy/cap/rebound isolation |
| AT-16 | Derived metrics reproducible | PASS | S17 + aligned cohort null tests |
| AT-17 | Spend not fabricated | PASS | S18/S19/S41 |
| AT-18 | UNKNOWN/UNSUPPORTED explicit | PASS | S24/S25/S48 |
| AT-19 | Deterministic serialization | PASS | S35 manifest hash (unchanged by cutoff repair) |
| AT-20 | Deterministic ZIP/hash | PASS | S35 + `test_export_zip_deterministic_settings_hash` regression slice |
| AT-21 | Tampered package detected | PASS | S36 |
| AT-22 | Cross-shop leakage forbidden | PASS | S26/S46 |
| AT-23 | DATA_MAP grain/joins | PASS | S24/S32/S44 |
| AT-24 | ExportService single authority | PASS | S29/S30/S49 |
| AT-25 | No WB write | PASS | S37 scenario_seam + stub_contract parity |
| AT-26 | No PG/Redis/control-plane write | PASS | S28/S38 scenario_seam + stub_contract parity |

**Intentional non-blockers:** Task 5.7 live CH/PG integration optional — no PROVIDER_EXECUTION_RECEIPT claimed. `current_bid_evidence=UNAVAILABLE` by Owner design. Cutoff proofs supplement (not replace) AT-19/AT-20 serialization/ZIP determinism.

## SCENARIO_MATRIX (S01–S51)

| Id | L* | Spec heading (suffix) | Primary test | Seam | Exec | Stub parity | Verdict |
|---|---|---|---|---|---|---|---|
| S01 | L5 | Strict daily grain preserved | test_daily_grain_strict | unit_seam | GREEN | N/A | PASS |
| S02 | L5 | Physical adv_id on every row | test_rebound_row_retains_adv_id | unit_seam | GREEN | N/A | PASS |
| S03 | L4 | History not clipped to ExportPeriod | test_keyword_dates_ignore_period_end | scenario_seam | GREEN | fake_reader | PASS |
| S04 | L4 | UI pagination window not used | test_no_ui_pagination_bound | unit_seam | GREEN | N/A | PASS |
| S05 | L5 | Auto and Search adv_ids distinguishable | test_auto_search_legs_separate | unit_seam | GREEN | N/A | PASS |
| S06 | L3 | Rebound adv_ids included in CH filter | test_rebound_adv_id_in_scope | unit_seam | GREEN | N/A | PASS |
| S07 | L3 | Rebound does not invent transition timeline | test_no_rebind_timeline_fields | unit_seam | GREEN | N/A | PASS |
| S08 | L5 | Same query two legs two rows | test_same_query_two_legs_two_adv_ids | unit_seam | GREEN | N/A | PASS |
| S09 | L5 | Missing day not fabricated zeros | test_missing_day_not_zero | unit_seam | GREEN | N/A | PASS |
| S10 | L5 | Missing position not coerced | test_missing_position_null | unit_seam | GREEN | N/A | PASS |
| S11 | L5 | Graphic creator not on export path | test_forbidden_graphic_import | unit_seam | GREEN | N/A | PASS |
| S12 | L5 | UI daily rollup SQL not authority | test_forbidden_ui_sql_path | unit_seam | GREEN | N/A | PASS |
| S13 | L7 | Delta sign documented in DATA_MAP | test_datamap_position_delta_convention | unit_seam | GREEN | N/A | PASS |
| S14 | L6 | Rolling 365d differs from previous calendar year | test_rolling_vs_calendar_year_bounds | unit_seam | GREEN | N/A | PASS |
| S15 | L6 | Comparable previous window aligned | test_prev7d_alignment | unit_seam | GREEN | N/A | PASS |
| S16 | L6 | Insufficient history partial coverage | test_partial_7d_coverage | unit_seam | GREEN | N/A | PASS |
| S17 | L6 | CTR from summed clicks and views | test_window_ctr_sum_ratio | unit_seam | GREEN | N/A | PASS |
| S18 | L5 | NULL spend not fabricated | test_null_spend_unavailable | unit_seam | GREEN | N/A | PASS |
| S19 | L5 | Factual spend when column populated | test_factual_spend_status | unit_seam | GREEN | N/A | PASS |
| S20 | L6 | Latest row wins deterministically | test_current_state_deterministic | unit_seam | GREEN | N/A | PASS |
| S21 | L6 | No AI labels in changes | test_changes_no_ai_labels | unit_seam | GREEN | N/A | PASS |
| S22 | L6 | Decision log labeled DECISION | test_bid_decision_exported_in_current_state | scenario_seam | GREEN | fake_reader | PASS |
| S23 | L6 | Separate position types not merged | test_position_types_separate | unit_seam | GREEN | N/A | PASS |
| S24 | L7 | DATA_MAP lists keyword_daily grain | test_datamap_grain_keys | unit_seam | GREEN | N/A | PASS |
| S25 | L5 | Conflicting same-timestamp snapshots ambiguous | test_snapshot_conflict_ambiguous | unit_seam | GREEN | N/A | PASS |
| S26 | L2 | Shop filter enforced | test_cross_shop_forbidden | scenario_seam | GREEN | fake_reader | PASS |
| S27 | L6 | Bid and CPM fields separate | test_bid_cpm_distinct | unit_seam | GREEN | N/A | PASS |
| S28 | L7 | Export read-only seam | test_export_no_store_writes | scenario_seam | GREEN | fake_reader | PASS |
| S29 | L7 | Keyword datasets in same manifest | test_keyword_cards_in_manifest | scenario_seam | GREEN | fake_reader | PASS |
| S30 | L7 | ExportService remains sole authority | test_no_second_exporter_entry | unit_seam | GREEN | N/A | PASS |
| S31 | L7 | DATA_MAP in file descriptors | test_datamap_in_manifest_files | scenario_seam | GREEN | fake_reader | PASS |
| S32 | L4 | Dual bounds documented | test_datamap_dual_bounds | unit_seam | GREEN | N/A | PASS |
| S33 | L7 | Fake keyword reader in unit test | test_injected_fake_reader | unit_seam | GREEN | N/A | PASS |
| S34 | L7 | Legacy integration test uses fake keyword assembler | test_export_settings_integration | scenario_seam | GREEN | injected fake | PASS |
| S35 | L7 | Repeatable keyword manifest hash | test_keyword_manifest_deterministic | scenario_seam | GREEN | fake_reader | PASS |
| S36 | L7 | DATA_MAP tamper fails validation | test_datamap_tamper_fails | scenario_seam | GREEN | fake_reader | PASS |
| S37 | L7 | Keyword export zero WB calls | test_default_export_service_no_wb_at_boundary | scenario_seam | GREEN | **PASS** (test_ch_stub_contract + boundary) | PASS |
| S38 | L7 | No PG Redis writes on keyword export | test_default_export_service_no_writes_at_boundary | scenario_seam | GREEN | **PASS** (test_ch_stub_contract + boundary) | PASS |
| S39 | L4 | Dates beyond period end present within cutoff | test_contract_full_history | scenario_seam | GREEN | fake_reader | PASS |
| S40 | L3 | Rebound adv_id in query scope | test_contract_rebound_scope | scenario_seam | GREEN | fake_reader | PASS |
| S41 | L5 | Null spend contract | test_contract_null_spend | scenario_seam | GREEN | fake_reader | PASS |
| S42 | L5 | Null position contract | test_contract_null_position | scenario_seam | GREEN | fake_reader | PASS |
| S43 | L5 | Identical same-timestamp duplicates collapse | test_snapshot_identical_collapse | unit_seam | GREEN | N/A | PASS |
| S44 | L5 | norm_query not used as raw_query | test_raw_query_unavailable | unit_seam | GREEN | N/A | PASS |
| S45 | L4 | Future CH dates excluded from last_available | test_cutoff_future_bounds_excluded_from_export_metadata | scenario_seam | GREEN | N/A | PASS |
| S46 | L2/L3 | Rebound adv_id without PG ownership ambiguous | test_rebound_ownership_ambiguous_foreign_shop | unit_seam | GREEN | N/A | PASS |
| S47 | L6 | mv_clusters_last_state not campaign authority | test_mv_not_campaign_current_state | unit_seam | GREEN | N/A | PASS |
| S48 | L6 | Empty bid_decision_log marked unsupported | test_bid_log_unsupported_coverage | scenario_seam | GREEN | fake_reader | PASS |
| S49 | L7 | Default export includes keyword datasets | test_default_export_keyword_enabled | scenario_seam | GREEN | fake_reader | PASS |
| S50 | L7 | Default keyword cards present | test_contract_default_keyword_cards | scenario_seam | GREEN | fake_reader | PASS |
| S51 | L4 | Cutoff excludes future/same-day/version-ms | test_contract_cutoff_excludes_*_payload (+ SQL helpers) | scenario_seam | GREEN | N/A | PASS |

### Stub contract inventory (S37/S38 boundary)

| Stub | Production adapter | Fake | Contract test | Verdict |
|---|---|---|---|---|
| CH daily reader | `ChKeywordDailyReader.fetch_rows_with_client` | `FakeClickHouseClient` | test_stub_contract_daily_reader_routing_and_cutoff_params | PASS |
| CH position reader | `ChKeywordPositionReader.fetch_rows_with_client` | `FakeClickHouseClient` | test_stub_contract_position_reader_routing_and_version_ms | PASS |
| CH bounds reader | `ChKeywordBoundsReader.fetch_*_with_client` | `FakeClickHouseClient` | test_stub_contract_bounds_reader_daily_and_position_queries | PASS |
| CH bid decision | `ChBidDecisionProbe`/`ChBidDecisionReader` | `FakeClickHouseClient` | test_stub_contract_bid_probe_* / bid_decision_reader_timeline_params | PASS |
| PG session | `PgAdvIdOverlapReader` + session factory | `FakePgSession` | test_stub_contract_fake_session_forbids_commit / pg_overlap_reader_read_only_session | PASS |
| Fail-closed routing | All CH readers via client | `FakeClickHouseClient` | test_stub_contract_unknown_sql_fail_closed_empty_rows | PASS |

### Additional proofs (not separate S-id rows)

- Aligned cohort math: test_window_rates_disjoint_cohort_conservative_null, test_window_cpm_aligned_spend_views_cohort, test_window_cpo_requires_aligned_factual_orders — GREEN
- Source failure fail-closed: test_position_bounds_reader_failure_returns_none_bounds, test_bid_probe_* — GREEN
- Field registry completeness: test_datamap_export_field_matrix_complete — GREEN
- DECISION classification: test_decision_timeline_source_derived_event_class (producer context; no native CH event_class column)
- Default pipeline zero-side-effect: test_default_export_service_no_wb_at_boundary / no_writes_at_boundary — GREEN

## GAPS

None. All audit07 TEST_ONLY_PACKET items closed with executed green tests.

## ROUTE_PACKETS

None (VERDICT=PASS).

## Known limitations (explicit, not claimed)

- Task 5.7 live CH/PG destructive integration: **unchecked by design** — no PROVIDER_EXECUTION_RECEIPT
- `current_bid_evidence` PROVEN path: **unwired** — UNAVAILABLE by Owner design
- **MERGE_READY not certified** — independent merge-review pending against committed stage `9a80c813ed4edaf3c6f2da6ae65af4221f7ec36e`
- Archive path still requires `mode=archive` verify + commit of implementation manifest

STATUS: PASS  
VERDICT: INDEPENDENT_SCENARIO_AUDIT_PASS
