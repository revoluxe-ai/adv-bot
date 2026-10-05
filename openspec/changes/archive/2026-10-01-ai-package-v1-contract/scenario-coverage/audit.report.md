# Scenario Test Coverage Audit Report

CHANGE_ID: ai-package-v1-contract
MODE: audit
PASS_SCOPE: FULL_CHANGE
PRODUCER_COMMAND: /opsx-spec-scenario-coverage mode=audit change=ai-package-v1-contract run=targeted
EXECUTED_AT: 2026-09-30T14:45:34Z

SCENARIO_TEST_COVERAGE_REPORT:
  SCHEMA_VERSION: 1
  CHANGE_ID: ai-package-v1-contract
  SOURCE_SPEC_SHA: fbf1fc5c56c593089da567e7e5bc2c675d1ee71b2cd9fe4079ee894f83b7a7b4
  WORKTREE_FINGERPRINT: 6f7f802adaa5555fc8507d4e28d0d15589f8685c7df4e701c4f967c9e42da30c
  ACTIVATION:
    SCENARIO_COVERAGE_REQUIRED: true
    PRODUCT_ACCEPTANCE_REQUIRED: true
    ACTIVATION_VERSION: OPSX_SCENARIO_TEST_COVERAGE_V1
  VERDICT: PASS
  SCENARIOS_TOTAL: 26
  SCENARIOS_PASS: 26
  SCENARIOS_FAIL: 0
  SCENARIOS_BLOCKED: 0
  LIFECYCLE_STATUS: DERIVED
  PLAN_EVIDENCE_ID: SCPV1-39d14fba55537e56
  AUDIT_EVIDENCE_ID: SCAR-6f0bb38e5dab934d
  EXECUTION_SUMMARY:
    CACHE_MODE: OFF
    PG_ENDPOINT: 127.0.0.1:5433 (test_adv_bot_db)
    CH_ENDPOINT: 127.0.0.1:8124 (test_adv_bot_clickhouse)
    UNIT: poetry run pytest -m unit tests/unit/ai_package_v1/ -q → 75 passed exit 0
    INTEGRATION: ALLOW_DESTRUCTIVE_TEST_DB=1 ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1 ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1 poetry run pytest -m "integration and destructive_local" tests/integration/ai_package_v1/ -q → 6 passed exit 0
  STUB_CONTRACTS_TOTAL: 4
  STUB_CONTRACTS_PASS: 4
  PROVIDER_RECEIPTS: not_required_for_audit (certify gate)
  ROWS:
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Single shop bounded period
      TRACE_ID: S01
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s01_scenario_seam_bounded_shop_and_period_on_export', 'tests/unit/ai_package_v1/test_export_service.py::test_export_with_scope_builds_manifest_and_payloads']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Shop isolation
      TRACE_ID: S02
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s02_s25_scenario_seam_shop_isolation_on_export_path', 'tests/unit/ai_package_v1/test_shop_id_manifest.py::test_shop_isolation_filters_foreign_shop']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: ch_campaign_stat_contract + test_ch_campaign_stat_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No WB API on export path
      TRACE_ID: S03
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s03_s20_scenario_seam_export_path_zero_wb_http_calls', 'tests/unit/ai_package_v1/test_import_guard.py::test_ai_package_v1_has_no_forbidden_imports']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Missing accumulation is explicit
      TRACE_ID: S04
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s04_s22_scenario_seam_empty_campaign_stat_not_full_coverage', 'tests/unit/ai_package_v1/test_coverage_rules.py::test_empty_inventory_unknown_collection_none_coverage']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Same domain different transport
      TRACE_ID: S05
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s05_scenario_seam_zip_and_raw_validator_parity', 'tests/unit/ai_package_v1/test_zip_validator.py::test_valid_golden_package_passes']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Campaign date grain preserved
      TRACE_ID: S06
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s06_s08_scenario_seam_csv_grain_matches_contract_cases', 'tests/unit/ai_package_v1/test_campaign_stat_grain.py::test_campaign_stat_query_uses_default_db_qualification']
      BOUNDARY_INTEGRATION: ['tests/integration/ai_package_v1/test_ch_pg_read_boundary.py::test_ch_campaign_stat_reader_reads_live_full_adv_wb_stat']
      STUB_PARITY: ch_campaign_stat_contract + test_ch_campaign_stat_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Auto and Search remain separate original rows
      TRACE_ID: S07
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s07_s23_scenario_seam_auto_search_rows_separate_on_export', 'tests/unit/ai_package_v1/test_campaign_stat_grain.py::test_auto_and_search_ids_preserved_separately']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Funnel limited to main nmid per ComplexAdv
      TRACE_ID: S08
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s06_s08_scenario_seam_csv_grain_matches_contract_cases', 'tests/unit/ai_package_v1/test_ch_funnel_reader.py::test_funnel_query_uses_default_db_and_nmids_param']
      BOUNDARY_INTEGRATION: ['tests/integration/ai_package_v1/test_ch_pg_read_boundary.py::test_ch_funnel_reader_reads_live_wb_common_stat']
      STUB_PARITY: ch_funnel_stat_contract + test_ch_funnel_stat_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Funnel orders are not shop product orders
      TRACE_ID: S09
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s09_s21_scenario_seam_funnel_orders_not_shop_orders_card', 'tests/unit/ai_package_v1/test_funnel_orders_boundary.py::test_funnel_orders_never_populate_shop_product_orders_card']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: PG inventory is read-only minimal grain
      TRACE_ID: S10
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s10_scenario_seam_export_uses_pg_readonly_scope_reader', 'tests/unit/ai_package_v1/test_pg_scope_queries.py::test_pg_scope_queries']
      BOUNDARY_INTEGRATION: ['tests/integration/ai_package_v1/test_ch_pg_read_boundary.py::test_pg_export_shop_scope_reader_reads_live_inventory']
      STUB_PARITY: pg_export_scope_contract + test_pg_export_scope_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings not implied by inventory card
      TRACE_ID: S11
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s11_s26_scenario_seam_inventory_card_partial_not_wb_universe', 'tests/unit/ai_package_v1/test_pg_inventory_card.py::test_inventory_card_partial_coverage_not_full_wb_universe']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Explicit unassigned source
      TRACE_ID: S12
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s12_scenario_seam_shop_orders_unassigned_on_export_path', 'tests/unit/ai_package_v1/test_shop_orders_card.py::test_shop_orders_sales_source_not_assigned']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: NO_DATA without automatic incomplete coverage
      TRACE_ID: S13
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s13_scenario_seam_no_data_does_not_force_partial_on_export', 'tests/unit/ai_package_v1/test_coverage_rules.py::test_no_data_does_not_auto_force_partial_coverage']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: UNKNOWN fail-closed
      TRACE_ID: S14
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s14_scenario_seam_unknown_shop_orders_fail_closed_on_export', 'tests/unit/ai_package_v1/test_coverage_rules.py::test_unknown_not_export_success']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No fake coverage from timestamps
      TRACE_ID: S15
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s15_scenario_seam_stale_freshness_does_not_imply_full_coverage', 'tests/unit/ai_package_v1/test_ch_freshness_reader.py']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: ch_freshness_contract + test_ch_freshness_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: No fabricated WB limits
      TRACE_ID: S16
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s16_scenario_seam_no_fabricated_wb_limits_in_manifest', 'tests/unit/ai_package_v1/test_manifest_determinism.py::test_export_manifest_has_no_fabricated_wb_api_limit_fields']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md::#### Scenario: Deterministic sha256
      TRACE_ID: S17
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s17_s24_scenario_seam_dual_export_equal_manifest_and_file_hashes', 'tests/unit/ai_package_v1/test_manifest_determinism.py::test_manifest_hash_stable_across_builds']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Valid package passes
      TRACE_ID: S18
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_zip_validator.py::test_valid_golden_package_passes']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Tampered payload fails
      TRACE_ID: S19
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_zip_validator.py::test_tampered_payload_fails_hash_mismatch']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Export spy shows no WB calls
      TRACE_ID: S20
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s03_s20_scenario_seam_export_path_zero_wb_http_calls', 'tests/integration/ai_package_v1/test_export_no_wb_live_pg_ch.py::test_s20_export_live_pg_ch_orchestration_zero_wb_calls']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Orders sales unassigned
      TRACE_ID: S21
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s09_s21_scenario_seam_funnel_orders_not_shop_orders_card', 'tests/unit/ai_package_v1/test_shop_orders_card.py::test_shop_orders_sales_source_not_assigned']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Empty campaign stat
      TRACE_ID: S22
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s04_s22_scenario_seam_empty_campaign_stat_not_full_coverage', 'tests/unit/ai_package_v1/test_coverage_rules.py::test_empty_campaign_stat_not_full_coverage']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Two campaign ids preserved
      TRACE_ID: S23
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s07_s23_scenario_seam_auto_search_rows_separate_on_export', 'tests/unit/ai_package_v1/test_export_service.py::test_load_scope_preserves_auto_and_search_adv_ids']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Repeatable manifest
      TRACE_ID: S24
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s17_s24_scenario_seam_dual_export_equal_manifest_and_file_hashes', 'tests/unit/ai_package_v1/test_manifest_determinism.py::test_zip_build_twice_same_sha256_entries']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Foreign shop excluded
      TRACE_ID: S25
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s02_s25_scenario_seam_shop_isolation_on_export_path', 'tests/unit/ai_package_v1/test_shop_id_manifest.py::test_shop_isolation_filters_foreign_shop']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: ch_campaign_stat_contract + test_ch_campaign_stat_stub_contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Inventory card partial semantics
      TRACE_ID: S26
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_scenario_seam_export_service.py::test_s11_s26_scenario_seam_inventory_card_partial_not_wb_universe', 'tests/unit/ai_package_v1/test_pg_inventory_card.py::test_inventory_card_partial_coverage_not_full_wb_universe']
      BOUNDARY_INTEGRATION: ['not_applicable']
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      ROW_VERDICT: PASS
  GAPS: none
  ROUTE_PACKETS:
    TEST_ONLY_PACKET: none
    REFACTOR_AND_TEST_PACKET: none
    CERTIFY_PACKET: none

## Independent audit notes

- All 26 delta `#### Scenario:` headings audited; SCENARIOS_SKIPPED=0.
- Steady-state reconcile-on-deploy: not_applicable (on-demand export; plan LIFECYCLE).
- Causal path reaches ExportService.export / validator without patching orchestration.
- CH/PG thin ends: shared contract modules consumed by stub_contract tests and scenario seams.
- mode=audit does not consume PROVIDER_EXECUTION_RECEIPT freshness (certify owns that gate).
