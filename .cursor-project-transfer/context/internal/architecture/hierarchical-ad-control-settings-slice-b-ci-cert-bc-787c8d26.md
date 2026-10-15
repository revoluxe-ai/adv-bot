---
cursor:
  subagentId: "bc-787c8d26-1c03-557c-acf0-f99bf2b65b62"
---

# Slice B — CI gate repair + certification status

Prior: [final CAS](./hierarchical-ad-control-settings-slice-b-final-cas-bc-787c8d26.md)

## RETURN

```
CHANGE: hierarchical-ad-control-settings
SLICE: B
PRE_REPAIR_HEAD: 0c8d25bef1d033219c9424503ba600b5351e2e64
CERTIFIED_HEAD: a59e9a00c2655fb74d6675a09a6251de70d917c8
PR: https://github.com/revoluxe-ai/adv-bot/pull/473
STAGE: d5a41b7c5382cef91e64fe87c4e03b4b1cdc8f6c

ALEMBIC_HEAD: b1c2d3e4f5a7
ALEMBIC_HEAD_COUNT: 1
MIGRATION_STATIC: REPAIRED (test_alembic_heads expects b1)
MIGRATION_EPHEMERAL_PG: REPAIRED (wbautobudgettopup stub + ad-control table assert + pytest mirror)

CI_FIXTURE_CHANGE: app/db/migration_ephemeral_baseline.py; .github/workflows/migration-gates.yml
HISTORICAL_MIGRATIONS_MODIFIED: NO

PG_INTEGRATION_TESTS: suite ready; VM lacks Docker/Python3.11/poetry env — await CI destructive_local
PG_TEST_COUNT: 17 cases in tests/integration/ad_control_settings/

CLEAR_RECREATE_ABA: implemented + tested (authored)
CONCURRENT_SHOP_CREATE: RevisionConflictError (authored)
CONCURRENT_CAMPAIGN_CREATE: RevisionConflictError (authored)
RAW_INTEGRITY_ERROR_EXPOSED: NO (repository translates)
NO_OP_REVISION_CONSUMED: NO (ledger test added)

TRANSACTION_CONFLICT_BOUNDARY: documented on repository; rollback required after flush conflict

UNIT_TESTS: 35 PASS (--noconftest on VM); poetry-native NOT_RUN (no py3.11)
ADJACENCY_TESTS: included in unit bundle on VM
RUFF: NOT_RUN
PYRIGHT: NOT_RUN
OPENSPEC: NOT_RUN strict
OPSX_VERIFY: NOT_RUN
INDEPENDENT_REVIEW: NOT_RUN

MCP_TOPOLOGY_FOLLOWUP: after Slice B merge, MCP #452 rebuild merge to include b1 head

UI: NO | RUNTIME_CPO: NO | WB_WRITES: NO | PRODUCTION_MIGRATION_APPLIED: NO | DEPLOY: NO | MERGE: NO

CRITICAL: —
HIGH: CI must green migration-gates + destructive_local PG on runner
MEDIUM: full poetry certification chain on CI
LOW: —

FINAL_STATUS: BLOCKED_PG_INTEGRATION (local VM); BLOCKED_VERIFICATION until CI confirms
```
