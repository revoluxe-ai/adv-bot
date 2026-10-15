---
cursor:
  subagentId: "bc-64d8213c-dd5a-5e62-af1b-0a3f6a6574d3"
---

# WB Sky MCP PostgreSQL provider-gap authorship

Read-only audit of `wb-sky-mcp-read-interface` at `fb5410ad`. The PostgreSQL connection boundary is already session-injectable, so this run did not author a provider test and did not edit the worktree.

```text
WB_SKY_MCP_PG_PROVIDER_GAP_AUTHORSHIP_REPORT

PR: #452
BASE_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
FINAL_WORKTREE_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
PLAN_EVIDENCE_ID: SCPV1-f0d1412a12fa9174
PLAN_FRESH: YES
SCENARIO_AUDIT: FAIL
PG_GAP_DISPOSITION: TEST_ONLY
GAP_ID: GAP-MCP-PG-CONNECTION-WRITE-READ
PACKET_ID_OR_FINGERPRINT: SCP-TEST-ONLY-fb5410ad-mcp-pg-connection
HELPER_DISCOVERY: reuse candidate exists; not modified. Searched tests/integration/**, tests/support/destructive_pg_reset.py, root conftest.py async_session / async_engine / setup_test_database, MCP connection tests. Found live fixture async_session (conftest.py:703) gated by destructive_local. No MCP integration test. init_postgres_schema_and_seed does not import McpConnection. PG_TRUNCATE_TABLES does not list mcp_connection.
HELPER_STRATEGY: reuse
PRODUCTION_SEAM_CHANGED: NO
SEAMS_AUTHORED: none
PROVIDER_TESTS_AUTHORED: none
REAL_PG_FIXTURE: conftest.py::async_session (existing; requires @pytest.mark.destructive_local). Not executed.
PERSISTED_WRITE_ASSERTED: NO
VERSION_READ_ASSERTED: NO
MOCK_ONLY_EVIDENCE_NOT_MISCLASSIFIED: PASS
PG_SESSION_MODE: PASS
UNIT_MOCK_CHECKS: PASS
RUFF_CAUSAL_SCOPE: PASS
PYRIGHT_CAUSAL_SCOPE: NOT_RUN
DIFF_CHECK: PASS
LIVE_RUN: not_attempted
PROVIDER_RECEIPT: NONE
INDEPENDENT_REAUDIT_REQUIRED: YES
STATUS: BLOCKED_REDIRECT_TEST_ONLY
COMMIT: NONE
PUSH: NO
PRODUCTION_CONNECTIVITY: NONE
PRODUCTION_WRITES: NONE
```

`RUFF_CAUSAL_SCOPE: PASS` means there was no causal diff to lint. Ruff was not run against the unrelated 13 MCP findings. Pyright was not run because no production or test-support file was edited.

## Why this stopped

The missing evidence is real PostgreSQL persistence of the MCP connection and a read-back of `authorization_version`. That semantic gap is unchanged. The production store is already testable without a seam refactor.

`SqlConnectionRepository.__init__` takes `AsyncSession`. Parent `_PgConnections._run` in `app/modules/wb_sky_mcp/http.py` opens `get_async_session_maker(read_only=read_only)` and passes that session in. Writes (`add`, `save`, `apply_refresh_rotation`) use `read_only=False`. Pure reads (`get`, `list_for_user`, `find_by_refresh_hash`) use `read_only=True`. `SqlShopGrantReader` is the same parent-to-child pattern with `read_only=True`. `_bind_principal` uses `_sm(read_only=False)` and passes the session to `create_user`.

Scenario-coverage dispositions:

- `TEST_ONLY` when `tests/**` is enough and the production seam is already usable.
- `REFACTOR_AND_TEST` when a PG/CH session handoff is missing (`PG_CH_NO_INJECTABLE_SEAM`, `PG_CH_MISSING_PARENT_SESSION_HANDOFF`, `PRODUCTION_CAUSAL_PATH_UNTESTABLE`).

This gap is `TEST_ONLY_BOUNDARY_GAP`. The previous certify packet's `DISPOSITION: CERTIFY` with `PROVIDER_TEST_IDS: NONE_AUTHORED` does not match the contract: `CERTIFY` is only for authored provider tests that still need an authorized live run. No such test exists. `test_sql_refresh_rotation_selects_for_update` builds a fake session and asserts compiled SQL contains `FOR UPDATE`. It is not provider evidence.

`/opsx-close-external-gap` must not write this test. Next writer is `/opsx-test` with the packet below.

## Preflight

- Local HEAD, `origin/cursor/wb-sky-mcp-read-interface-127c`, and `gh pr view 452` are `fb5410ad2815e3529d55058d729ac6ac27dc84b0`. PR state `OPEN`. Branch `cursor/wb-sky-mcp-read-interface-127c`.
- `origin/stage` is `d2166b2d805b27a6656f46c6ccb8e56066b4e888`.
- Worktree was clean before and after this run. `git diff --check` is empty.
- Plan receipt `SCPV1-f0d1412a12fa9174` matches SHA-256 of LF-normalized `design.md`, `spec.md`, `owner-contract.md`, and `plan.md`. Identity blob recomputes to the same evidence id.

## Audit

`mode=audit change=wb-sky-mcp-read-interface`, `run=targeted`. Read-only. No product, test, or OpenSpec edits.

Targeted unit run (no Docker, no PostgreSQL):

`/tmp/mcp-verify-venv/bin/pytest tests/unit/wb_sky_mcp/test_mcp_read_interface.py -q --tb=line -p no:cacheprovider`

35 passed in 0.47s at snapshot `fb5410ad`.

```text
STATUS: FAIL
VERDICT: SCENARIO_TEST_COVERAGE_FAIL
MODE: READ_ONLY
SCENARIO_MODE: audit
CHANGE: wb-sky-mcp-read-interface
SNAPSHOT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
PASS_SCOPE: FULL_CHANGE

SCENARIO_SUMMARY:
  SCENARIOS_TOTAL: 21
  SCENARIOS_AUDITED: 21
  SCENARIOS_PASS: 5
  SCENARIOS_FAIL: 16
  SCENARIOS_BLOCKED: 0
  SCENARIOS_SKIPPED: 0
```

PASS (executed scenario seam, no PostgreSQL durable end):

- Write tool is not advertised
- Authorize creates a one-time session
- Authorize rejects weak or foreign requests
- Deep link is not an API credential
- Opening the bot is not consent

FAIL (`STUB_PARITY=UNPROVEN`; memory repository stands in for PostgreSQL; no `destructive_local` boundary test):

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

Redis stays on the approved fakeredis boundary. ClickHouse is not a required provider end for this change. Cancel `access_denied` with the original `state` and `iss` is covered by the executed seam and is not itself a PostgreSQL receipt.

Primary gap class: `TEST_ONLY_BOUNDARY_GAP`. Shop-grant read is a second TEST_ONLY item, same disposition, different symbol and `read_only=True`. No new semantic blocker.

## Packet for `/opsx-test`

`REFACTOR_AND_TEST_PACKET`: none. `CERTIFY_PACKET`: none.

```text
SCENARIO_TEST_ONLY_PACKET:
  SCHEMA_VERSION: 1
  SOURCE: SCENARIO_TEST_COVERAGE_REPORT
  CHANGE_ID: wb-sky-mcp-read-interface
  SOURCE_SPEC_SHA: 2aeccf0a2abb3f83512483b83847c9acb6e47473ce952536fb93520aa8577bbf
  WORKTREE_FINGERPRINT: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  ITEMS:
    - GAP_ID: GAP-MCP-PG-CONNECTION-WRITE-READ
      GAP_FILE_ID: mcp-pg-connection
      SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Confirm binds the canonical principal
      DISPOSITION: TEST_ONLY
      REQUIRED_ARTIFACTS:
        CONTRACT_CASES: |
          Persist via SqlConnectionRepository.add on a real AsyncSession.
          Re-read with SqlConnectionRepository.get and with a separate select
          of mcp_connection. Assert public_id, user_id (User.id),
          authorization_version, refresh_token_hash, and revoked_at.
          Save a revoked row with authorization_version bumped by the
          existing disconnect/revoke semantics and read that version back
          through the production read path.
          apply_refresh_rotation must persist the rotated hash in the same
          transaction that takes FOR UPDATE. A second use of the previous
          hash must not yield a second success. Do not change token lifetime
          or OAuth semantics.
        FAKE_OR_STUB: tests/unit/wb_sky_mcp/test_mcp_read_interface.py::_World.connections (MemoryConnectionRepository)
        SCENARIO_SEAM_TEST: tests/unit/wb_sky_mcp/test_mcp_read_interface.py::test_opening_start_does_not_confirm_and_confirm_binds_user_id
        STUB_CONTRACT_TEST: new parity test that the memory repository and SqlConnectionRepository agree on add/get/save/version/revoke/rotation outcomes
        BOUNDARY_ADAPTER_TEST: new tests/integration test calling SqlConnectionRepository with conftest.async_session, marked destructive_local, re-reading persisted mcp_connection
      PRODUCTION_ENTRYPOINT: app/modules/wb_sky_mcp/http.py::_PgConnections._run
      REAL_BOUNDARY_SYMBOLS:
        - app/modules/wb_sky_mcp/connection_repository.py::SqlConnectionRepository.add
        - app/modules/wb_sky_mcp/connection_repository.py::SqlConnectionRepository.get
        - app/modules/wb_sky_mcp/connection_repository.py::SqlConnectionRepository.save
        - app/modules/wb_sky_mcp/connection_repository.py::SqlConnectionRepository.apply_refresh_rotation
      REALITY_CONSTRAINTS: |
        Live proof requires @pytest.mark.destructive_local and fixture
        async_session. Do not run it without that marker and a local test
        database. Never target production PostgreSQL.
        SqlConnectionRepository commits the session, so the fixture
        rollback does not undo the row. Delete the test row in cleanup.
        init_postgres_schema_and_seed does not import McpConnection;
        importing the model before create_all registers mcp_connection.
        PG_TRUNCATE_TABLES does not list mcp_connection.
        Parent session mode is already explicit: write and
        read-after-write read_only=False; pure read read_only=True.
        Excluded as provider evidence:
        tests/unit/wb_sky_mcp/test_mcp_read_interface.py::test_sql_refresh_rotation_selects_for_update
      MOCKING_CONSTRAINTS: |
        Do not accept AsyncMock session, compiled SQL only,
        assert_called_once, a fake transaction, or a patched-away
        SqlConnectionRepository as the provider proof.
    - GAP_ID: GAP-MCP-PG-SHOP-GRANT-READ
      GAP_FILE_ID: mcp-pg-shop-grant
      SCENARIO_ID: openspec/changes/wb-sky-mcp-read-interface/specs/wb-sky-mcp-read-interface/spec.md::Shop list follows current cabinets
      DISPOSITION: TEST_ONLY
      REQUIRED_ARTIFACTS:
        CONTRACT_CASES: |
          SqlShopGrantReader.list_shops returns only WBUserCabinet rows
          for that User.id, mapped to ShopGrant(shop_id, name, active).
          Another user's cabinet is absent. Empty list is success.
        FAKE_OR_STUB: app/modules/wb_sky_mcp/grants.py::MemoryShopGrantReader
        SCENARIO_SEAM_TEST: tests/unit/wb_sky_mcp/test_mcp_read_interface.py::test_profile_hides_credentials_and_shop_list_is_scoped
        STUB_CONTRACT_TEST: parity between MemoryShopGrantReader rows and SqlShopGrantReader success/empty shape
        BOUNDARY_ADAPTER_TEST: destructive_local read of WBUserCabinet through SqlShopGrantReader(async_session)
      PRODUCTION_ENTRYPOINT: app/modules/wb_sky_mcp/http.py::_PgGrants.list_shops
      REAL_BOUNDARY_SYMBOLS:
        - app/modules/wb_sky_mcp/grants.py::SqlShopGrantReader.list_shops
      REALITY_CONSTRAINTS: |
        PURE_READ. Production parent uses
        get_async_session_maker(read_only=True). Same destructive_local
        fixture. No connection-table schema change.
      MOCKING_CONSTRAINTS: |
        Do not mock the grant decision inside the boundary test.
```

## Files changed

None in `/agent/repos/adv-bot`. This report is the only new file.

## Next action

`/opsx-test` with the `SCENARIO_TEST_ONLY_PACKET` above.

Do not certify, commit, push, merge, or run the live provider test from this authorship hop.
