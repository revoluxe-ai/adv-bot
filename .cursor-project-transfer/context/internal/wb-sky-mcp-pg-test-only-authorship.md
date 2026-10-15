---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP PostgreSQL test-only authorship

```text
WB_SKY_MCP_PG_TEST_ONLY_AUTHORSHIP_REPORT

PR: #452
BASE_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
FINAL_WORKTREE_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
PROJECT_NATIVE: YES
SUBAGENTS: [SUBAGENT_A_CONNECTION, SUBAGENT_B_SHOP_GRANT, SUBAGENT_C_READ_ONLY_CONTRACT_REVIEW]
PLAN_EVIDENCE_ID: SCPV1-f0d1412a12fa9174
PLAN_FRESH: YES
PACKET_FRESH: YES
SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
WORKTREE_FINGERPRINT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
TEST_ONLY_ITEMS_TOTAL: 2
PRODUCTION_CODE_CHANGED: NO
COMMIT: NONE
PUSH: NO
LIVE_PG_EXECUTION: NOT_RUN
PROVIDER_EXECUTION_RECEIPT: NONE
SCENARIO_CERTIFY_PACKET: NOT_EMITTED (items AUTHORED_AWAITING_CERTIFICATION; certify via /opsx-close-external-gap with destructive_local)
NEXT_ACTION: /opsx-spec-scenario-coverage mode=audit change=wb-sky-mcp-read-interface
FINAL_STATUS: AUTHORED_AWAITING_CERTIFICATION

GAP-MCP-PG-CONNECTION-WRITE-READ:
  RESULT: AUTHORED_AWAITING_CERTIFICATION
  CONTRACT_ID: wb_sky_mcp.connection_repository.pg_boundary.v1
  CONTRACT_CASES_PATH: tests/support/wb_sky_mcp/connection_repository_contract.py
  FAKE_OR_STUB_PATH: tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py
  STUB_CONTRACT: CLOSED (memory ContractCase parity)
  BOUNDARY_ADAPTER: tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py

GAP-MCP-PG-SHOP-GRANT-READ:
  RESULT: AUTHORED_AWAITING_CERTIFICATION
  CONTRACT_ID: wb_sky_mcp.shop_grant.pg_boundary.v1
  CONTRACT_CASES_PATH: tests/support/wb_sky_mcp/shop_grant_contract.py
  FAKE_OR_STUB_PATH: tests/unit/wb_sky_mcp/test_shop_grant_reader_stub_contract.py
  STUB_CONTRACT: CLOSED (memory shape parity)
  BOUNDARY_ADAPTER: tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py

TEST_FILES_CHANGED:
  - tests/support/wb_sky_mcp/__init__.py
  - tests/support/wb_sky_mcp/connection_repository_contract.py
  - tests/support/wb_sky_mcp/shop_grant_contract.py
  - tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py
  - tests/unit/wb_sky_mcp/test_shop_grant_reader_stub_contract.py
  - tests/integration/wb_sky_mcp/conftest.py
  - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py
  - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py

REAL_PG_FIXTURE: conftest.py::async_session (@pytest.mark.destructive_local)
PERSISTED_WRITE_ASSERTED: YES (authored; not live-executed)
VERSION_READ_ASSERTED: YES (authored)
RAW_SELECT_ASSERTED: YES (mcp_connection row)
ROTATION_REUSE_ASSERTED: YES (second presented hash raises McpError)
SHOP_SCOPE_ASSERTED: YES (foreign cabinet absent)
EMPTY_GRANT_ASSERTED: YES
FAKE_FOR_UPDATE_NOT_MISCLASSIFIED: PASS (test_sql_refresh_rotation_selects_for_update unchanged; not provider evidence)

STUB_INVENTORY:
  - MemoryConnectionRepository: CLOSED — tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py + shared ContractCase
  - MemoryShopGrantReader: CLOSED — tests/unit/wb_sky_mcp/test_shop_grant_reader_stub_contract.py
  - fakeredis OAuth store (AsyncKv): CLOSED — approved transport boundary per scenario taxonomy; not a PG provider gap for this packet

PROVIDER_TESTS_AUTHORED:
  - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select
  - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse
  - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]
  - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]
  - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets
  - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success

NON_LIVE_TESTS:
  collect_only: /tmp/mcp-verify-venv/bin/pytest tests/integration/wb_sky_mcp/ --collect-only -q → 6 items, no PG connection at collection
  unit_executed: 38 passed (test_mcp_read_interface.py + 2 new stub_contract modules) via /tmp/mcp-verify-venv
  integration_executed: NONE (cloud constraint: no Docker PG / no destructive_local run)

RUFF_TOUCHED_TESTS: PASS (/tmp/mcp-verify-venv/bin/ruff check on touched paths)
DIFF_CHECK: PASS (git diff --check empty; only tests/** untracked/new)

SOURCE_RESOLUTION:
  PACKET: internal/wb-sky-mcp-pg-provider-gap-authorship.md SCENARIO_TEST_ONLY_PACKET
  SPEC_SHA: matches plan.receipt.json SOURCE_SPEC_SHA
  BRANCH: cursor/wb-sky-mcp-read-interface-127c @ fb5410ad

EXECUTION_PREFLIGHT:
  origin/stage: d2166b2d805b27a6656f46c6ccb8e56066b4e888
  PR452 head: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  worktree: clean tracked tree; new tests/** files uncommitted
```

## SCENARIO_TEST_AUTHORSHIP_RESULT

```text
SCENARIO_TEST_AUTHORSHIP_RESULT:
  SCHEMA_VERSION: 1
  CHANGE_ID: wb-sky-mcp-read-interface
  SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
  WORKTREE_FINGERPRINT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  STUB_INVENTORY:
    - MemoryConnectionRepository: CLOSED
    - MemoryShopGrantReader: CLOSED
    - fakeredis OAuth store: CLOSED (approved boundary)
  ITEMS:
    - GAP_ID: GAP-MCP-PG-CONNECTION-WRITE-READ
      GAP_FILE_ID: mcp-pg-connection
      SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Confirm binds the canonical principal
      RESULT: AUTHORED_AWAITING_CERTIFICATION
      CONTRACT_ID: wb_sky_mcp.connection_repository.pg_boundary.v1
      CONTRACT_CASES_PATH: tests/support/wb_sky_mcp/connection_repository_contract.py
      CONTRACT_SHA: 91a60cb5083615b0068ad0715aac4f556949c974f2a955d1dbf8e51b49a24895
      FAKE_OR_STUB_PATH: tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py
      FAKE_SHA: 370e712c8babd78117339ca8d2e980bcc015c80aa65b42b1849b5ce6cde45a1f
      TEST_IDS:
        - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select
        - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse
        - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]
        - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]
        - tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py::test_memory_connection_repository_contract_parity[persist_add_get_disconnect_version]
        - tests/unit/wb_sky_mcp/test_connection_repository_stub_contract.py::test_memory_connection_repository_contract_parity[refresh_rotation_rejects_reuse]
      TEST_CONTENT_SHA:
        integration: aa2ffaa1059fd3e420cf437ae55d89696847fa1b246e5b2cbc8a95bf5c98b46e
        stub_unit: 370e712c8babd78117339ca8d2e980bcc015c80aa65b42b1849b5ce6cde45a1f
        contract: 91a60cb5083615b0068ad0715aac4f556949c974f2a955d1dbf8e51b49a24895
      TESTS_EXECUTED: stub unit only (2 parametrized cases PASS); integration NOT_RUN
      EXECUTION_RESULTS: unit PASS; integration COLLECT_ONLY 6 items
      REMAINING_GAPS: none for stub inventory; live PG certify pending
      NEXT: /opsx-close-external-gap (destructive_local provider run) then /opsx-spec-scenario-coverage mode=audit
    - GAP_ID: GAP-MCP-PG-SHOP-GRANT-READ
      GAP_FILE_ID: mcp-pg-shop-grant
      SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Shop list follows current cabinets
      RESULT: AUTHORED_AWAITING_CERTIFICATION
      CONTRACT_ID: wb_sky_mcp.shop_grant.pg_boundary.v1
      CONTRACT_CASES_PATH: tests/support/wb_sky_mcp/shop_grant_contract.py
      CONTRACT_SHA: ed6c3daa0e13b6123a1005bce3b49408d16a818398d6d09d11298b46c225d074
      FAKE_OR_STUB_PATH: tests/unit/wb_sky_mcp/test_shop_grant_reader_stub_contract.py
      FAKE_SHA: bd8bb8c0e272d53b4ce0c884e24d15bec36a2319ac1af15ebc1427d1044ed382
      TEST_IDS:
        - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets
        - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success
        - tests/unit/wb_sky_mcp/test_shop_grant_reader_stub_contract.py::test_memory_shop_grant_reader_contract_shape
      TEST_CONTENT_SHA:
        integration: 8749d706eadee3138cbf8c9bb20ac4f4be146793c767833d194a56f36bd57dfe
        stub_unit: bd8bb8c0e272d53b4ce0c884e24d15bec36a2319ac1af15ebc1427d1044ed382
      TESTS_EXECUTED: stub unit PASS; integration NOT_RUN
      EXECUTION_RESULTS: unit PASS; integration COLLECT_ONLY
      REMAINING_GAPS: live PG certify pending
      NEXT: /opsx-close-external-gap then scenario re-audit
```

## Notes

- `ensure_mcp_connection_table` autouse fixture registers `mcp_connection` via `create_all(checkfirst=True)` because `init_postgres_schema_and_seed` omits the model.
- SqlConnectionRepository commits bypass fixture rollback; tests delete rows explicitly.
- No commit/push per mission constraints.
