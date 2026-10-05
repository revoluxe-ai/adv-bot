SCENARIO_TEST_COVERAGE_REPORT

STATUS: GAP
VERDICT: FAIL
MODE: READ_ONLY
SCENARIO_MODE: audit
CHANGE: campaign-settings-history
PASS_SCOPE: FULL_CHANGE
PLAN_EVIDENCE_ID: db0349d67c039d806e4a79cde16b8a71a761c0d73e62b64b96b925a6b4c065f3

SCENARIO_SUMMARY:
  SCENARIOS_TOTAL: 30
  SCENARIOS_AUDITED: 30
  SCENARIOS_PASS: 20
  SCENARIOS_FAIL: 10
  SCENARIOS_BLOCKED: 0
  SCENARIOS_SKIPPED: 0

EVIDENCE_SUMMARY:
  TARGETED_NON_DESTRUCTIVE: 178 passed
  PYRIGHT_STRICT: 0 errors / 0 warnings
  RUFF: PASS
  OPENSPEC_STRICT: PASS
  DIFF_CHECK: PASS
  REQUIRED_PROVIDER_TESTS: 4
  REQUIRED_PROVIDER_TESTS_EXECUTED: 0
  UNEXECUTED_REQUIRED_TESTS: 4

PASS GROUPS:
- 8 settings-contract/canonical/Excel scenarios that do not require an external store boundary.
- 12 clickhouse-migration-lifecycle scenarios using the accepted isolated target/coordinator evidence model.

FAIL GROUP:
- Runtime history scenarios whose causal path reaches PostgreSQL discovery/read/advisory-lock or ClickHouse history read/write.
- Scenario/business seams exist and pass, but boundary integration execution is missing on the current snapshot.

UNEXECUTED_REQUIRED_TESTS:
- tests/integration/campaign_settings_history/test_pg_boundary.py::test_pg_reader_discovers_and_loads_real_settings_rows
- tests/integration/campaign_settings_history/test_pg_boundary.py::test_pg_advisory_xact_lock_serializes_real_sessions
- tests/integration/campaign_settings_history/test_clickhouse_boundary.py::test_history_repository_write_persists_real_clickhouse_row
- tests/integration/campaign_settings_history/test_clickhouse_boundary.py::test_history_repository_reads_latest_and_timeline_from_real_clickhouse

GAP_CLASS: BOUNDARY_INTEGRATION_NOT_EXECUTED
PROVIDER_RECEIPTS: missing
PRODUCTION_WRITE: forbidden/not performed
WB_WRITE: forbidden/not performed
PRODUCTION_CLICKHOUSE_MIGRATION_APPLY: forbidden/not performed

NEXT_ACTION: authorized disposable provider execution, then mode=certify.
