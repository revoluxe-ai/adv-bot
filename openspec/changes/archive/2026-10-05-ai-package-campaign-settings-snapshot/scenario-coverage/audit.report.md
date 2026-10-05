# Scenario Test Coverage Audit Report

CHANGE_ID: ai-package-campaign-settings-snapshot
MODE: audit
PASS_SCOPE: FULL_CHANGE
PRODUCER_COMMAND: /opsx-spec-scenario-coverage mode=audit change=ai-package-campaign-settings-snapshot run=targeted
EXECUTED_AT: 2026-10-05T01:00:00Z
SNAPSHOT: 37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0

SCENARIO_TEST_COVERAGE_REPORT:
  SCHEMA_VERSION: 1
  CHANGE_ID: ai-package-campaign-settings-snapshot
  SOURCE_SPEC_SHA: f6c56b7af60aa41b890ebbc4633f48d0aa1d6b1f39089f893e34d737a36959ac
  WORKTREE_FINGERPRINT: 33eb7a05f94ffcb0cae8001ab966ef0880b8ff5eb8a3d681ea87329a1dfaf459
  ACTIVATION:
    SCENARIO_COVERAGE_REQUIRED: true
    PRODUCT_ACCEPTANCE_REQUIRED: true
    ACTIVATION_VERSION: OPSX_SCENARIO_TEST_COVERAGE_V1
  VERDICT: PASS
  SCENARIOS_TOTAL: 21
  SCENARIOS_PASS: 21
  SCENARIOS_FAIL: 0
  SCENARIOS_BLOCKED: 0
  SCENARIOS_SKIPPED: 0
  LIFECYCLE_STATUS: DERIVED
  PLAN_EVIDENCE_ID: SCPV1-c1eba84a1b0b8a1e
  AUDIT_EVIDENCE_ID: SCAR-96c3a4077c8adb6b
  EXECUTION_SUMMARY:
    CACHE_MODE: OFF
    UNIT: poetry run pytest tests/unit/ai_package_v1/test_campaign_settings_assembler.py tests/unit/ai_package_v1/test_campaign_settings_contract.py tests/unit/ai_package_v1/test_campaign_settings_snapshot_domain.py tests/unit/ai_package_v1/test_export_settings_integration.py -vv --tb=no -q → 30 passed exit 0
    INTEGRATION: not_required_slice1 (PG boundary optional per plan OPEN-01)
  STUB_CONTRACTS_TOTAL: 2
  STUB_CONTRACTS_PASS: 2
  STUB_CONTRACTS_FAIL: 0
  PROVIDER_RECEIPTS: not_required_for_audit (certify gate)
  ROWS:
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export payload is not control-plane snapshot
      TRACE_ID: S01
      LIFECYCLE_STEPS: L1, L2
      PRODUCTION_ENTRYPOINT: CampaignSettingsAssembler.assemble(shop_id)
      CAUSAL_PATH: FakeSettingsReader/PG rows → assembler projection → CampaignSettingsSnapshotV1
      THIN_ENDS: PG session (FakeSettingsReader stub)
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_payload_schema_is_campaign_settings_snapshot_v1', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_payload_type_guard_non_aliasing']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: FakeSettingsReader + make_adv_setting fixture (slice-1 protocol stub; PG integration optional)
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (assembler causal logic unpatched; reader injected at protocol boundary)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export payload is not Redis tick DTO
      TRACE_ID: S02
      LIFECYCLE_STEPS: L2
      PRODUCTION_ENTRYPOINT: PgAdvSettingInventoryReader / assembler scope
      CAUSAL_PATH: non-bot-active rows included; payload rejects AdvSettingsSnapshotDTO validation
      THIN_ENDS: PG session (FakeSettingsReader)
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_payload_not_adv_settings_snapshot_dto', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_scope_not_bot_active_only', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_pg_scope_query_has_no_bot_active_filter']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: FakeSettingsReader + SQL query static proof
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Auto and Search legs remain distinguishable
      TRACE_ID: S03
      LIFECYCLE_STEPS: L3
      PRODUCTION_ENTRYPOINT: CampaignSettingsAssembler leg projection
      CAUSAL_PATH: adv_id + search_adv_id → auto_leg/search_leg with distinct wb_adv_id
      THIN_ENDS: PG rows fixture
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_auto_and_search_legs_distinguishable', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_detailed_contract_golden_legs']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: make_adv_setting A/K fixture
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Primary grain uses adv_setting anchor
      TRACE_ID: S04
      LIFECYCLE_STEPS: L2, L3
      PRODUCTION_ENTRYPOINT: CampaignSettingsSnapshotRecordV1 inventory block
      CAUSAL_PATH: AdvSetting.id → inventory.adv_setting_id + shop_id
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_primary_grain_adv_setting_id']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Local policy not masquerading as WB state
      TRACE_ID: S05
      LIFECYCLE_STEPS: L4
      PRODUCTION_ENTRYPOINT: Assembler field_provenance builder
      CAUSAL_PATH: LOCAL_POLICY authority on bot_active and related columns
      THIN_ENDS: PG row fixture
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_local_policy_provenance_not_wb_authoritative']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: make_adv_setting fixture
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (authority map unpatched)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Unsupported field slot stays explicit
      TRACE_ID: S06
      LIFECYCLE_STEPS: L4, L5
      PRODUCTION_ENTRYPOINT: Assembler OPEN leg field slots
      CAUSAL_PATH: UNSUPPORTED authority + UNSUPPORTED_FIELD reason_code on wb_status
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_unsupported_field_explicit']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Null PG column stays null
      TRACE_ID: S07
      LIFECYCLE_STEPS: L4
      PRODUCTION_ENTRYPOINT: Assembler nullable field projection
      CAUSAL_PATH: PG None → JSON null (search_leg absent when search_adv_id null)
      THIN_ENDS: PG row fixture
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_null_pg_column_stays_null']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: make_adv_setting null columns
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Unknown WB field fails closed for mutation eligibility
      TRACE_ID: S08
      LIFECYCLE_STEPS: L5
      PRODUCTION_ENTRYPOINT: CampaignSettingsSnapshotV1.is_mutation_eligible()
      CAUSAL_PATH: UNKNOWN authority → has_unknown_authoritative_field + fail-closed helper
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_snapshot_domain.py::test_unknown_wb_field_fail_closed']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (domain model direct)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Four completeness dimensions stay independent
      TRACE_ID: S09
      LIFECYCLE_STEPS: L6
      PRODUCTION_ENTRYPOINT: build_campaign_settings_snapshot_card
      CAUSAL_PATH: four card fields present; PARTIAL coverage not implied FULL by freshness
      THIN_ENDS: fixed clock fixture
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_four_completeness_dimensions_independent']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: fixed_clock in conftest
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Partial PG WB sync is explicit
      TRACE_ID: S10
      LIFECYCLE_STEPS: L4, L5, L6
      PRODUCTION_ENTRYPOINT: Assembler package-level completeness
      CAUSAL_PATH: PARTIAL coverage + PARTIAL_PG_WB_SYNC reason_code
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_partial_pg_wb_sync_explicit']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: No WB API on settings export path
      TRACE_ID: S11
      LIFECYCLE_STEPS: L4, L5
      PRODUCTION_ENTRYPOINT: CampaignSettingsAssembler.assemble with WB deny spy
      CAUSAL_PATH: PG-only readers; sys.modules deny on app.core.mp.wb.api
      THIN_ENDS: WB import boundary (deny spy)
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_settings_export_zero_wb_api_calls', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_settings_export_spy_no_wb_calls']
      BOUNDARY_INTEGRATION: WB deny contract (zero calls asserted)
      STUB_PARITY: NOT_APPLICABLE (deny-at-boundary, not stub parity)
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (assembler unpatched; WB blocked at module boundary)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Export does not write operational state
      TRACE_ID: S12
      LIFECYCLE_STEPS: L7
      PRODUCTION_ENTRYPOINT: CampaignSettingsAssembler via PgCampaignSettingsReader session path
      CAUSAL_PATH: read path only; session.add/commit/flush never called
      THIN_ENDS: AsyncSession mock
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_export_does_not_write_state']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: session mock tracks write calls
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (PG reader production path; session thin-end stub)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Manifest references domain payload
      TRACE_ID: S13
      LIFECYCLE_STEPS: L6, L7
      PRODUCTION_ENTRYPOINT: build_campaign_settings_snapshot_card / ExportService export
      CAUSAL_PATH: serialize payload → sha256 → card payload_file + hash; validator applies
      THIN_ENDS: stdlib hash
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_manifest_references_domain_payload', 'tests/unit/ai_package_v1/test_export_settings_integration.py::test_manifest_payload_hash_matches_domain_contract', 'tests/unit/ai_package_v1/test_export_settings_integration.py::test_export_service_emits_detailed_settings_json_payload']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-campaign-settings-snapshot/spec.md::#### Scenario: Detailed export flag distinguishes v1 inventory
      TRACE_ID: S14
      LIFECYCLE_STEPS: L6, L7
      PRODUCTION_ENTRYPOINT: build_campaign_settings_snapshot_card / ExportService manifest
      CAUSAL_PATH: detailed_settings_export=true + PARTIAL coverage semantics
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_detailed_export_flag_true', 'tests/unit/ai_package_v1/test_export_settings_integration.py::test_export_service_emits_detailed_settings_json_payload']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: PG inventory is read-only minimal grain
      TRACE_ID: S15
      LIFECYCLE_STEPS: L2
      PRODUCTION_ENTRYPOINT: PgAdvSettingInventoryReader.load_inventory(shop_id)
      CAUSAL_PATH: production calls session_maker(read_only=True) + shop-scoped SELECT; no writes
      THIN_ENDS: _CapturingSessionMaker injectable session factory
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_pg_reader_read_only_session', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_pg_scope_query_has_no_bot_active_filter', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_export_does_not_write_state']
      BOUNDARY_INTEGRATION: not_applicable (optional slice 2+ per plan OPEN-01)
      STUB_PARITY: _CapturingSessionMaker records read_only=True polarity matching SessionMakerProtocol at thin end
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (PgAdvSettingInventoryReader causal path unpatched; session factory stubbed after boundary)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings not implied by inventory card
      TRACE_ID: S16
      LIFECYCLE_STEPS: L5, L6
      PRODUCTION_ENTRYPOINT: Card metadata coverage field / ExportService manifest card
      CAUSAL_PATH: detailed_settings_export=true still yields PARTIAL coverage (not FULL WB universe)
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_partial_pg_wb_sync_explicit', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_four_completeness_dimensions_independent', 'tests/unit/ai_package_v1/test_export_settings_integration.py::test_export_service_emits_detailed_settings_json_payload']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-exporter/spec.md::#### Scenario: Detailed settings export uses dedicated contract when applied
      TRACE_ID: S17
      LIFECYCLE_STEPS: L3, L6, L7
      PRODUCTION_ENTRYPOINT: ExportService.export_with_scope + CampaignSettingsAssembler
      CAUSAL_PATH: end-to-end detailed card + CampaignSettingsSnapshotV1 JSON payload + separate legs
      THIN_ENDS: PG stub (FakeSettingsReader)
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_export_settings_integration.py::test_export_service_emits_detailed_settings_json_payload', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_detailed_contract_golden_legs', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_payload_type_guard_non_aliasing']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: make_adv_setting golden rows
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Inventory card partial semantics before detailed export
      TRACE_ID: S18
      LIFECYCLE_STEPS: L6
      PRODUCTION_ENTRYPOINT: build_campaign_settings_inventory_card (legacy detailed_settings_export=false path)
      CAUSAL_PATH: legacy inventory card builder → PARTIAL coverage + provenance notes; contrast with detailed card
      THIN_ENDS: ExportScopeAdv fixture rows (no WB/network)
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_inventory_partial_before_detailed']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK (production build_campaign_settings_inventory_card + build_campaign_settings_snapshot_card reached; observable THEN on coverage/manifest)
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Detailed settings contract tests when implemented
      TRACE_ID: S19
      LIFECYCLE_STEPS: L2, L3, L4
      PRODUCTION_ENTRYPOINT: Contract test golden fixture path via assembler
      CAUSAL_PATH: CampaignSettingsSnapshotV1 + separate legs + non-aliasing + null/unknown explicit
      THIN_ENDS: PG fixture
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_detailed_contract_golden_legs', 'tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_payload_not_adv_settings_snapshot_dto', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_null_pg_column_stays_null']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: golden JSON via serialize_campaign_settings_payload
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Settings export spy shows no WB calls
      TRACE_ID: S20
      LIFECYCLE_STEPS: L7
      PRODUCTION_ENTRYPOINT: Contract test harness (paired S11)
      CAUSAL_PATH: WB layer spied; zero WB API on settings path
      THIN_ENDS: WB deny spy
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_settings_export_spy_no_wb_calls', 'tests/unit/ai_package_v1/test_campaign_settings_assembler.py::test_settings_export_zero_wb_api_calls']
      BOUNDARY_INTEGRATION: WB deny contract
      STUB_PARITY: NOT_APPLICABLE
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
    - SCENARIO_ID: openspec/changes/ai-package-campaign-settings-snapshot/specs/ai-package-v1-contract-tests/spec.md::#### Scenario: Payload type guard
      TRACE_ID: S21
      LIFECYCLE_STEPS: L7
      PRODUCTION_ENTRYPOINT: CampaignSettingsSnapshotV1.model_validate + negative stubs
      CAUSAL_PATH: schema_version gate; rejects A1 stub and Redis DTO shapes
      THIN_ENDS: none
      SCENARIO_SEAM: ['tests/unit/ai_package_v1/test_campaign_settings_contract.py::test_payload_type_guard_non_aliasing']
      BOUNDARY_INTEGRATION: not_applicable
      STUB_PARITY: CampaignResourceSnapshotV1Stub shared negative contract
      EXECUTION: REQUIRED_TESTS_EXECUTED_AND_GREEN
      MOCK_PLACEMENT: OK
      ROW_VERDICT: PASS
  GAPS: none
  ROUTE_PACKETS:
    TEST_ONLY_PACKET: none
    REFACTOR_AND_TEST_PACKET: none
    CERTIFY_PACKET: none

## Independent audit notes

- Re-audit after TEST_ONLY closure for S15 (`test_pg_reader_read_only_session`) and S18 (`test_inventory_partial_before_detailed`).
- All 21 delta `#### Scenario:` headings audited; SCENARIOS_SKIPPED=0.
- Derived Lifecycle L1–L7 mapped per plan.md; steady-state reconcile-on-deploy not_applicable (on-demand export).
- Slice-1 unit seams use FakeSettingsReader at reader protocol; PG live boundary optional per plan OPEN-01.
- S15: `PgAdvSettingInventoryReader.load_inventory` production path asserts `session_maker(read_only=True)` via `_CapturingSessionMaker` at injectable thin end.
- S18: `build_campaign_settings_inventory_card` production card builder asserts PARTIAL coverage and `detailed_settings_export` not true; contrasts detailed path via `build_campaign_settings_snapshot_card`.
- Causal assembler/export logic runs unpatched; WB blocked at module import boundary (S11/S20).
- mode=audit does not require PROVIDER_EXECUTION_RECEIPT (certify gate).
- INPUT_FRESHNESS: current (SOURCE_SPEC_SHA matches plan.receipt.json; WORKTREE_FINGERPRINT reflects dirty test files at HEAD=37d0ec5f).

WORKTREE_FINGERPRINT_COMPOSITION:
  HEAD: 37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0
  SOURCE_SPEC_SHA: f6c56b7af60aa41b890ebbc4633f48d0aa1d6b1f39089f893e34d737a36959ac
  TEST_CONTENT_SHA: scenario-mapped unit test files (working tree)
  PRODUCTION_BOUNDARY_SHA: pg_adv_setting_inventory_reader, dataset_cards, manifest_cards, campaign_settings_assembler, pg_campaign_settings_reader (working tree at HEAD)

SOURCE_RESOLUTION:
- mode: exact_path via change=ai-package-campaign-settings-snapshot
- primary_path: openspec/changes/ai-package-campaign-settings-snapshot/
- fallback_used: false

EXECUTION_PREFLIGHT:
- tests: EXECUTED targeted unit (30 passed)
- blocked_on_preflight: false

NEXT_ACTION: /opsx-spec-scenario-coverage mode=certify change=ai-package-campaign-settings-snapshot
ALSO_OK: /opsx-verify mode=impl change=ai-package-campaign-settings-snapshot
DO_NOT_DO_YET: /opsx-verify mode=archive until certify PASS (if PG/CH receipts required)
