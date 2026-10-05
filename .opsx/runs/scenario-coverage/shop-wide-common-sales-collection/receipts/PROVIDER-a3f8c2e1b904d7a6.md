# PROVIDER_EXECUTION_RECEIPT

SCHEMA_VERSION: 1
CHANGE_ID: shop-wide-common-sales-collection
GAP_ID: shop-wide-common-sales-collection::s12-ch-roundtrip::1
GAP_FILE_ID: a3f8c2e1b904d7a6
SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Task-owned scratch CH endpoint proven
KIND: CH
CONTRACT_ID: wb_common_stat_write_read_freshness
CONTRACT_SHA: unknown
PROVIDER_TEST_IDS:

- tests/integration/test_shop_wide_common_sale_stat_coverage.py::test_shop_wide_coverage_read_write_roundtrip
- tests/integration/test_shop_wide_common_sale_stat_coverage.py::test_collect_by_nmids_uses_production_writer

TEST_CONTENT_SHA: unknown
PRODUCTION_BOUNDARY_SHA: unknown
SCHEMA_SHA: unknown
WORKTREE_FINGERPRINT: 7ccebe8a8c0d5455d39d28f406ca7031b1d7a9b54c3c3734d45964a795d48c8c
EXECUTED_AT: 2026-10-05T01:58:25+03:00
EXECUTION_CLASS: destructive_local
RESULT: PASS
TESTS_PASSED: 2
TESTS_FAILED: 0
AUTHORIZATION_STATUS: consumed
LOG_PATH: openspec/changes/shop-wide-common-sales-collection/scenario-coverage/logs/integration-ch-coverage.log
LOG_SHA: 47bff5dc48a30bf3916324a98a72618d968a3d69681859a190024fbec3f87a8d
SECRETS_REDACTED: YES

Materialized during WB-SKY-COMMON-SALES-EVIDENCE-CLOSE-20261005-0250. Provider evidence only — not scenario coverage PASS.
