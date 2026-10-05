CERTIFY_PACKET

CHANGE_ID: campaign-settings-history
PURPOSE: execute only the four required disposable-store boundary tests and create fresh provider evidence.

AUTHORIZATION_REQUIRED: true
CURRENT_OPERATOR_OPT_IN:
  ALLOW_DESTRUCTIVE_TEST_DB: false
  ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE: false

FAIL_CLOSED_PROVIDER_SCOPE:
- PostgreSQL: localhost/127.0.0.1:5433, database test_adv_bot_db only.
- ClickHouse: localhost/127.0.0.1:8124, database test_adv_bot_clickhouse only.
- DEV_TUNNELS_* must be disabled/unset.
- Production/stage/dev databases are explicitly forbidden by tests/support validators.
- No WB calls.
- No production ClickHouse migration/apply.
- No writes to production current settings.

REQUIRED_TEST_IDS:
- tests/integration/campaign_settings_history/test_pg_boundary.py::test_pg_reader_discovers_and_loads_real_settings_rows
- tests/integration/campaign_settings_history/test_pg_boundary.py::test_pg_advisory_xact_lock_serializes_real_sessions
- tests/integration/campaign_settings_history/test_clickhouse_boundary.py::test_history_repository_write_persists_real_clickhouse_row
- tests/integration/campaign_settings_history/test_clickhouse_boundary.py::test_history_repository_reads_latest_and_timeline_from_real_clickhouse

EXECUTION_REQUIRES:
- ALLOW_DESTRUCTIVE_TEST_DB=1
- ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1

ON_PASS:
- record fresh PG and CH PROVIDER_EXECUTION_RECEIPT evidence bound to the current implementation/test hashes;
- rerun /opsx-spec-scenario-coverage mode=certify change=campaign-settings-history;
- only after certify PASS run /opsx-verify mode=archive campaign-settings-history.

DO_NOT:
- do not substitute production endpoints;
- do not enable dev tunnels;
- do not run migration 006 against production;
- do not archive before certify PASS.
