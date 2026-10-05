# Scenario Coverage Plan

CHANGE_ID: ai-package-keyword-performance-history
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-dad56a1027545bc3
LIFECYCLE_STATUS: DERIVED

Required-evidence planning only. Does not claim tests exist, were executed, or passed.

## Lifecycle coverage

LIFECYCLE_COVERAGE (Derived Lifecycle L1–L7 from design.md):

- L1 → S-LEG-01 — validate export inputs / shop scope gate
- L2 → S-LEG-02, S26 — PG inventory scope read-only
- L3 → S06, S07, S40 — keyword scope + rebound Redis membership expansion
- L4 → S03, S04, S32, S39, S45, S51 — CH MIN/MAX bounds, ExportPeriod, package cutoff
- L5 → S01, S02, S05, S08, S09, S10, S11, S12, S18, S19, S25, S41, S42, S43, S44 — daily facts strict grain
- L6 → S14, S15, S16, S17, S20, S21, S22, S23, S27, S47, S48 — windows/current/changes/decision probe
- L7 → S13, S24, S29, S30, S31, S35, S36, S49, S50 — DATA_MAP/manifest/default export

Steady-state reconcile: **not_applicable** — on-demand export read path; invariants proven per export invocation.

OPEN_QUESTIONS: none blocking plan ready.

## Owner acceptance mapping (AT-01..AT-26)

| AT | Scenarios |
|---|---|
| AT-01 | S01 |
| AT-02 | S03, S04, S39, S45, S51 |
| AT-03 | S05 |
| AT-04 | S02 |
| AT-05 | S06, S07, S40, S46 |
| AT-06 | S08 |
| AT-07 | S09 |
| AT-08 | S10, S42 |
| AT-09 | S11, S12 |
| AT-10 | S13 |
| AT-11 | S14, S17 |
| AT-12 | S14 |
| AT-13 | S15 |
| AT-14 | S16 |
| AT-15 | S20, S47 |
| AT-16 | S17 |
| AT-17 | S18, S19, S41 |
| AT-18 | S24, S25, S48 |
| AT-19 | S35 |
| AT-20 | S35 |
| AT-21 | S36 |
| AT-22 | S26, S46 |
| AT-23 | S24, S32, S44 |
| AT-24 | S29, S30, S49, S50 |
| AT-25 | S37 |
| AT-26 | S28, S38 |

SCENARIOS_TOTAL: 51

## Apply traceability index

| Id | SCENARIO_ID suffix | Primary test (apply) | Seam |
|---|---|---|---|
| S01 | Strict daily grain preserved | test_daily_grain_strict | unit_seam |
| S02 | Physical adv_id on every row | test_rebound_row_retains_adv_id | unit_seam |
| S03 | History not clipped to ExportPeriod (generated_at later than history) | test_keyword_dates_ignore_period_end | unit_seam |
| S04 | UI pagination window not used | test_no_ui_pagination_bound | unit_seam |
| S05 | Auto and Search adv_ids distinguishable | test_auto_search_legs_separate | unit_seam |
| S06 | Rebound adv_ids included in CH filter | test_rebound_adv_id_in_scope | unit_seam |
| S07 | Rebound does not invent transition timeline | test_no_rebind_timeline_fields | unit_seam |
| S08 | Same query two legs two rows | test_same_query_two_legs | unit_seam |
| S09 | Missing day not fabricated zeros | test_missing_day_not_zero | unit_seam |
| S10 | Missing position not coerced | test_missing_position_null | unit_seam |
| S11 | Graphic creator not on export path | test_forbidden_graphic_import | unit_seam |
| S12 | UI daily rollup SQL not authority | test_forbidden_ui_sql_path | unit_seam |
| S13 | Delta sign documented in DATA_MAP | test_datamap_position_delta_convention | unit_seam |
| S14 | Rolling 365d differs from previous calendar year | test_rolling_vs_calendar_year_bounds | unit_seam |
| S15 | Comparable previous window aligned | test_prev7d_alignment | unit_seam |
| S16 | Insufficient history partial coverage | test_partial_7d_coverage | unit_seam |
| S17 | CTR from summed clicks and views | test_window_ctr_sum_ratio | unit_seam |
| S18 | NULL spend not fabricated | test_null_spend_unavailable | unit_seam |
| S19 | Factual spend when column populated | test_factual_spend_status | unit_seam |
| S20 | Latest row wins deterministically | test_current_state_deterministic | unit_seam |
| S21 | No AI labels in changes | test_changes_no_ai_labels | unit_seam |
| S22 | Decision log labeled DECISION | test_bid_log_decision_class | unit_seam |
| S23 | Separate position types not merged | test_position_types_separate | unit_seam |
| S24 | DATA_MAP lists keyword_daily grain | test_datamap_grain_keys | unit_seam |
| S25 | Conflicting same-timestamp snapshots ambiguous | test_snapshot_conflict_ambiguous | unit_seam |
| S43 | Identical same-timestamp duplicates collapse | test_snapshot_identical_collapse | unit_seam |
| S44 | norm_query not used as raw_query | test_raw_query_unavailable | unit_seam |
| S45 | Future CH dates excluded from last_available | test_cutoff_excludes_future_bounds | unit_seam |
| S46 | Rebound adv_id without PG ownership / foreign-shop overlap ambiguous | test_rebound_ownership_ambiguous | unit_seam |
| S47 | mv_clusters_last_state not campaign authority; rebound not ACTIVE slot | test_mv_not_campaign_current_state | unit_seam |
| S48 | Empty bid_decision_log marked unsupported | test_bid_log_unsupported_coverage | unit_seam |
| S49 | Default export includes keyword datasets | test_default_export_keyword_enabled | scenario_seam |
| S50 | Default keyword cards present | test_contract_default_keyword_cards | contract |
| S51 | Cutoff excludes future dates, same-day post-instant daily rows, and position rows via version ms | test_contract_cutoff_future_dates | contract |
| S26 | Shop filter enforced | test_cross_shop_forbidden | unit_seam |
| S27 | Bid and CPM fields separate | test_bid_cpm_distinct | unit_seam |
| S28 | Export read-only seam | test_export_no_store_writes | unit_seam |
| S29 | Keyword datasets in same manifest | test_keyword_cards_in_manifest | scenario_seam |
| S30 | ExportService remains sole authority | test_no_second_exporter_entry | unit_seam |
| S31 | DATA_MAP in file descriptors | test_datamap_in_manifest_files | unit_seam |
| S32 | Dual bounds documented | test_datamap_dual_bounds | unit_seam |
| S33 | Fake keyword reader in unit test | test_injected_fake_reader | unit_seam |
| S34 | Legacy integration test uses fake keyword assembler | test_settings_integration_fake_keyword | regression |
| S35 | Repeatable keyword manifest hash | test_keyword_manifest_deterministic | contract |
| S36 | DATA_MAP tamper fails validation | test_datamap_tamper_fails | contract |
| S37 | Keyword export zero WB calls | test_keyword_export_no_wb | contract |
| S38 | No PG Redis writes on keyword export | test_keyword_export_no_writes | contract |
| S39 | Dates beyond period end present within cutoff | test_contract_full_history | contract |
| S40 | Rebound adv_id in query scope | test_contract_rebound_scope | contract |
| S41 | Null spend contract | test_contract_null_spend | contract |
| S42 | Null position contract | test_contract_null_position | contract |

Unit/scenario tests target: `tests/unit/ai_package_v1/keyword_performance/` (authored at apply).

## GENERATED_FROM

Repair hop `WB-SKY-KEYWORD-HISTORY-PLAN-REPAIR3-20261005-0137` (P008 version-ms cutoff,
P009 reproducible identity blob). Supersedes `SCPV1-3bf22597d777c0f1`.

Identity recipe (`OPSX_SCENARIO_TEST_COVERAGE_V1` INPUTS fields only — no plan hash,
no timestamps): canonical JSON UTF-8 with `sort_keys=True`, `separators=(',', ':')`,
no trailing newline. Fields: `CHANGE_ID`, `MODE`, `DESIGN_REVISION`, `SPEC_REVISION[]`,
`LIFECYCLE_REVISION`, `OWNER_CONTRACT_REVISION`, `SOURCE_SPEC_SHA`.
`PLAN_EVIDENCE_ID = SCPV1-first16(sha256(identity_blob))`.

Reproduce: `python openspec/changes/ai-package-keyword-performance-history/evidence/verify_plan_evidence_repair3.py`

- owner-contract.md: unchanged (hash in plan.receipt.json INPUTS)
- delta specs + design hashes: plan.receipt.json INPUTS
- authoritative `PLAN_CONTENT_HASH`, `PLAN_EVIDENCE_ID`, identity blob metadata: plan.receipt.json only

## Architecture constraints

- ADR: `decisions/ai-package-keyword-performance-history-ownership/decision.md`
- Accepted: `ai-package-v1-exporter-ownership`, `shop-data-source-strategy`, CH qualification
- Forbidden: UI SQL rollup, Telegram graph, second exporter, factual CPM×views spend
- Every behavioral scenario: ≥1 scenario_seam through ExportService or assembler orchestration
- Thin ends: CH/Redis/PG stubbed after causal boundary in unit tests
