---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP formal scenario certification

`mode=certify` for `wb-sky-mcp-read-interface`. Read-only. No provider receipt was created.

```text
WB_SKY_MCP_FORMAL_SCENARIO_CERTIFICATION_REPORT

PR:
#452

CERTIFIED_HEAD:
fb5410ad2815e3529d55058d729ac6ac27dc84b0

ORIGIN_STAGE:
d2166b2d805b27a6656f46c6ccb8e56066b4e888

PLAN_EVIDENCE_ID:
SCPV1-f0d1412a12fa9174

PLAN_FRESH:
YES

PLAN_INTEGRITY:
PASS

SCENARIOS_TOTAL:
21

SCENARIOS_PASS:
5

SCENARIOS_FAIL:
0

SCENARIOS_BLOCKED:
16

PASS_SCOPE:
NONE

FORMAL_SCENARIO_CERTIFICATION:
BLOCKED

READ_ONLY_BOUNDARY:
PASS

TOOLS:
get_profile
list_shops
get_capabilities
get_ai_package

WRITE_TOOLS:
NONE

OAUTH_SCENARIOS:
BLOCKED

CANCEL_ACCESS_DENIED:
PASS

REFRESH_SINGLE_USE:
BLOCKED

DYNAMIC_SHOP_GRANTS:
BLOCKED

PACKAGE_SCENARIOS:
BLOCKED

AUTH_BACKEND_FAILURE:
BLOCKED

MCP_TESTS:
35 passed (tests/unit/wb_sky_mcp/test_mcp_read_interface.py, snapshot fb5410ad)

TELEGRAM_TESTS:
included in those 35 (cancel_mcp, start); no separate Telegram suite

AI_PACKAGE_TESTS:
136 passed (tests/unit/ai_package_v1)

MIGRATION_TESTS:
test_migration_is_forward_connection_table_without_shop_grants passed;
tests/migrations/test_alembic_heads.py::test_exactly_one_alembic_head passed

RUFF:
FAIL (ruff 0.16.10, 13 findings: I001 import sort, TRY203, FURB192 on MCP paths)

PYRIGHT:
12 errors, all reportUnknownMemberType (PyJWT encode/decode, fakeredis dbsize/keys). Third-party typing only.

OPENSPEC:
PASS (openspec validate wb-sky-mcp-read-interface --strict --type change)

DIFF_CHECK:
PASS (git diff --check, clean worktree)

PROVIDER_RECEIPTS:
NONE

PROVIDER_RECEIPTS_FRESH:
NO

SCENARIO_CERTIFY_PACKET:
see below

PRODUCT_CODE_CHANGED:
NO

TEST_CODE_CHANGED:
NO

OPENSPEC_CHANGED:
NO

PRODUCTION_CONNECTIVITY:
NONE

PRODUCTION_WRITES:
NONE

CRITICAL:
NONE

HIGH:
Plan requires a PostgreSQL connection write and version read. No destructive_local provider test is authored. test_sql_refresh_rotation_selects_for_update mocks the session and only checks compiled SQL for FOR UPDATE. No receipt under .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/.

MEDIUM:
ruff 0.16.10 reports 13 style findings on the MCP tree. Not the certification blocker.

LOW:
Pyright strict on app/modules/wb_sky_mcp and tests/unit/wb_sky_mcp: 12 reportUnknownMemberType from PyJWT and fakeredis.

NEXT_GATE:
REPAIR_REQUIRED

FINAL_STATUS:
BLOCKED_NEEDS_PROVIDER_RECEIPT
```

Redis does not need a PostgreSQL-style provider receipt. Scenario seams use fakeredis through `OAuthRedisStore`. ClickHouse is not a required provider end for this change: package tests call real `ExportService` with stubbed readers, and the AI Package suite includes the CH stub contract.

## Row split

PASS (executed seam, no PostgreSQL durable end):

- Write tool is not advertised
- Authorize creates a one-time session
- Authorize rejects weak or foreign requests
- Deep link is not an API credential
- Opening the bot is not consent

BLOCKED (production path reads or writes PostgreSQL connection or cabinet grants; memory stand-in; no fresh receipt):

- Mutation request is rejected
- Confirm binds the canonical principal
- Return completes the original transaction
- Token exchange checks PKCE
- Profile hides credentials
- Shop list follows current cabinets
- Removed shop disappears immediately
- Foreign shop id fails closed
- Disconnect invalidates tokens
- Already revoked connection stays denied
- Capabilities list only real read support
- Capabilities without a grant fail closed
- Package returns structured canonical content
- Oversized payload is omitted honestly
- One shop per package
- Auth backend unavailable

Cancel `access_denied` with original `state` and `iss` is covered by the executed seam (`test_cancel_error_redirect_includes_exact_issuer`, `test_telegram_cancel_uses_completion_url`) and does not itself require a PostgreSQL receipt.

Tool boundary observed in `test_tools_list_is_exactly_four_read_only_tools`: exactly those four names; mutation and unknown tools fail closed.

## Packet

`PROVIDER_TEST_IDS` is empty on purpose. The mocked SQL unit test is not a provider test and must not be executed as one.

```text
SCENARIO_CERTIFY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID: wb-sky-mcp-read-interface
  WORKTREE_FINGERPRINT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
  PLAN_EVIDENCE_ID: SCPV1-f0d1412a12fa9174
  ITEMS:
    - GAP_ID: GAP-MCP-PG-CONNECTION-WRITE-READ
      GAP_FILE_ID: mcp-pg-connection
      SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Confirm binds the canonical principal
      ALSO_BLOCKED_SCENARIO_IDS:
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Return completes the original transaction
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Token exchange checks PKCE
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Profile hides credentials
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Shop list follows current cabinets
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Removed shop disappears immediately
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Foreign shop id fails closed
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Disconnect invalidates tokens
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Already revoked connection stays denied
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Capabilities list only real read support
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Capabilities without a grant fail closed
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Package returns structured canonical content
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Oversized payload is omitted honestly
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::One shop per package
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Auth backend unavailable
        - openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Mutation request is rejected
      DISPOSITION: CERTIFY
      KIND: PG
      CONTRACT_ID: mcp-connection-write-and-version-read
      CONTRACT_SHA: 31cd2828bc9c325b2f17d8552ec1c88e75a71aebc4a99214140b46d16495e123
      PROVIDER_TEST_IDS: NONE_AUTHORED
      EXCLUDED_UNIT_TEST: tests/unit/wb_sky_mcp/test_mcp_read_interface.py::test_sql_refresh_rotation_selects_for_update
      TEST_CONTENT_SHA: c5eaf6effa2b44d9d40c4e1d862b52f5ddb3ebcf11e2a6e0dbb3af110db841df
      PRODUCTION_BOUNDARY_SHA: 31cd2828bc9c325b2f17d8552ec1c88e75a71aebc4a99214140b46d16495e123
      PRODUCTION_BOUNDARY: app/modules/wb_sky_mcp/connection_repository.py::SqlConnectionRepository
      SCHEMA_SHA: 6325ea9178f40467fdbc01c71384e8053a332d5894edeb1c5ba72ef15fd6f66b
      SCHEMA_PATH: alembic_/versions/a9c0e7b41d22_add_mcp_connection.py
      GRANTS_BOUNDARY_SHA: 9b59f782f0947baf78e2120bd04c4dac0d22ef6d5396f89d3d4ad29241386583
      REQUIRED_EXECUTION_CLASS: destructive_local
      RECEIPT_PATH_EXPECTED: .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/receipts/PROVIDER-mcp-pg-connection.md
```

`/opsx-close-external-gap` cannot mint a valid receipt until a `destructive_local` test exists for connection insert and authorization-version read. That test is not in this certifier's write boundary.

Stop. No deploy. No merge.
