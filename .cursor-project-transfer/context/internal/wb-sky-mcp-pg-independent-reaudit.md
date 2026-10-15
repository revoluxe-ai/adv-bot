---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP PG — independent read-only re-audit

Change: `wb-sky-mcp-read-interface` (PR #452)  
Command: `/opsx-spec-scenario-coverage mode=audit change=wb-sky-mcp-read-interface`  
Auditor: subagent `bc-1334b977-28ff-5e36-8226-4f0b5f5822ef`  
FILES_CHANGED: none (read-only)

## Preflight

| Field | Value |
|-------|-------|
| AUDITED_HEAD | `fb5410ad2815e3529d55058d729ac6ac27dc84b0` |
| Branch | `cursor/wb-sky-mcp-read-interface-127c` |
| origin/stage | `d2166b2d805b27a6656f46c6ccb8e56066b4e888` |
| AUDITED_STATUS_SHA256 | `bce7e167f83c02688fd9c8770ccc29284328eb224e66480cb00ff9e3b0085912` |
| AUDITED_TRACKED_DIFF_SHA256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| AUDITED_UNTRACKED_MANIFEST_SHA256 | `d47476a1ff0070dc75f9eda5aed9cbe6c348c6a1ed27cbbf214d4e6cb17f0e95` |

**Dirty scope:** 8 untracked paths (exact manifest below). Matches expected test-only list. No tracked diff. **UNEXPECTED:** none.

**Plan receipt:** `SCPV1-f0d1412a12fa9174` — `INPUT_FRESHNESS: current` (`spec.md` sha `2aeccf0a…` matches receipt `SOURCE_SPEC_SHA` at committed HEAD).

## Non-live execution

| Suite | Result |
|-------|--------|
| `test_mcp_read_interface.py` + stub contracts (38 tests) | **PASS** @ HEAD + untracked stubs |
| `tests/integration/wb_sky_mcp/` | **collect-only: 6** (not executed) |
| `ruff` on touched test paths | **PASS** |
| `git diff --check` | **PASS** (empty tracked diff) |

## Provider test review (authored, not run)

**Connection** (`test_mcp_pg_connection_repository.py`, `connection_repository_contract.py`):

- Uses real `SqlConnectionRepository(async_session)` — no repo mock.
- `run_persist_add_get_disconnect_version`: add/get/save, refresh hash, disconnect `authorization_version==2`, raw `SELECT` re-read.
- `run_refresh_rotation_rejects_reuse`: `apply_refresh_rotation` + `McpError` on spent hash (FOR UPDATE path in production).
- Parametrized `CONNECTION_REPOSITORY_CONTRACT_CASES` shared with memory stub tests.
- `test_sql_refresh_rotation_selects_for_update` in **unit** file compiles SQL only (fake session) — correctly **not** boundary integration.

**Shop grant** (`test_mcp_pg_shop_grant_reader.py`, `shop_grant_contract.py`):

- Real `SqlShopGrantReader(async_session)`; seeds target/foreign users + `WBUserCabinet` / `WBCabinet`.
- Asserts scoped `list_shops` and empty success; no mocked grant decision.

**Session / destructive:** `pytestmark` includes `integration` + `destructive_local`. Root `async_session` requires `destructive_local`, uses test DSN (`127.0.0.1:5433`, `test_adv_bot_db`) from root `conftest.py`, function-scoped rollback. `ensure_mcp_connection_table` creates `mcp_connection` only on test engine. **Not production DB.**

**Stub inventory:** `MemoryConnectionRepository` + `MemoryShopGrantReader` + fakeredis in scenario seam — **stub contract CLOSED at unit layer** via shared `ContractCase` modules; **PG boundary CLOSED only after authorized destructive run**.

## INDEPENDENT_REAUDIT

```text
INDEPENDENT_REAUDIT:
  SCHEMA_VERSION: 1
  SOURCE_COMMAND: /opsx-spec-scenario-coverage
  VERDICT: READY_FOR_ONE_AUTHORIZED_RUN
  CHANGE_ID: wb-sky-mcp-read-interface
  GAP_IDS:
    - wb-sky-mcp-read-interface::pg-sql-connection-repository::1
    - wb-sky-mcp-read-interface::pg-sql-shop-grant-reader::1
  GAP_FILE_IDS:
    - ac6c9f0b4939f81e
    - 6b0cb5efc25d18c2
  CONTRACT_IDS:
    - wb_sky_mcp.connection_repository.pg_boundary.v1
    - wb_sky_mcp.shop_grant.pg_boundary.v1
  CONTRACT_SHAS:
    - 62f266181929e405063a06eb77d220eff97e178f50c7edea9d3e2477b3f2f64a
    - ed6c3daa0e13b6123a1005bce3b49408d16a818398d6d09d11298b46c225d074
  PROVIDER_TEST_IDS:
    - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select
    - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse
    - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]
    - tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]
    - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets
    - tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success
  TEST_CONTENT_SHAS:
    - aa2ffaa1059fd3e420cf437ae55d89696847fa1b246e5b2cbc8a95bf5c98b46e
    - 8749d706eadee3138cbf8c9bb20ac4f4be146793c767833d194a56f36bd57dfe
  PRODUCTION_BOUNDARY_SHAS:
    - 31cd2828bc9c325b2f17d8552ec1c88e75a71aebc4a99214140b46d16495e123
    - 9b59f782f0947baf78e2120bd04c4dac0d22ef6d5396f89d3d4ad29241386583
  SCHEMA_SHAS: n/a
  AUDITED_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
  AUDITED_STATUS_SHA256: bce7e167f83c02688fd9c8770ccc29284328eb224e66480cb00ff9e3b0085912
  AUDITED_TRACKED_DIFF_SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  AUDITED_UNTRACKED_MANIFEST_SHA256: d47476a1ff0070dc75f9eda5aed9cbe6c348c6a1ed27cbbf214d4e6cb17f0e95
  ALLOWED_RUN_BLOCK_SHA256: 65529731494c55d68bbe7d1c03b2a1fa7f9548276f613990b97ec8b321c2675b
  CREATED_AT: 2026-10-06T16:38:00Z
```

## ALLOWED_RUN_BLOCK (frozen — do not execute without `AUTHORIZE_ONE_LIVE_RUN`)

```bash
set -euo pipefail
cd /agent/repos/adv-bot
export PATH="$HOME/.local/bin:$PATH"

# --- Preflight: audited state (must match WB_SKY_MCP_PG_INDEPENDENT_REAUDIT) ---
test "$(git rev-parse HEAD)" = "fb5410ad2815e3529d55058d729ac6ac27dc84b0"
STATUS_SHA256="$(git -c color.ui=false -c core.quotepath=false status --porcelain=v1 -z | sha256sum | awk '{print $1}')"
test "$STATUS_SHA256" = "bce7e167f83c02688fd9c8770ccc29284328eb224e66480cb00ff9e3b0085912"
TRACKED_DIFF_SHA256="$(git -c color.ui=false -c core.quotepath=false diff --binary --full-index --no-ext-diff --no-textconv HEAD -- | sha256sum | awk '{print $1}')"
test "$TRACKED_DIFF_SHA256" = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MANIFEST_SHA256="$(python3 -c "import hashlib,os,subprocess; paths=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).split(b'\0'); paths=sorted([p.decode() for p in paths if p]); rec=b''.join(f\"{p}\t{len(open(p,'rb').read())}\t{hashlib.sha256(open(p,'rb').read()).hexdigest()}\n\".encode() for p in paths); print(hashlib.sha256(rec).hexdigest())")"
test "$MANIFEST_SHA256" = "d47476a1ff0070dc75f9eda5aed9cbe6c348c6a1ed27cbbf214d4e6cb17f0e95"

export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1
export POSTGRES_MASTER_HOST=127.0.0.1
export POSTGRES_REPLICA_HOST=127.0.0.1
export POSTGRES_PORT=5433
export POSTGRES_DBNAME=test_adv_bot_db
export POSTGRES_USER=test_user
export POSTGRES_PASSWORD=test_password
export POSTGRES_SSL_MODE=disable
export POSTGRES_SSL_INSECURE=true

# --- Single pytest process: 6 provider boundary tests only ---
poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local -vv --tb=short

# --- Teardown verification ---
test "${POSTGRES_DBNAME}" = "test_adv_bot_db"
test "${POSTGRES_MASTER_HOST}" = "127.0.0.1"
```

## Scenario matrix (summary)

21/21 scenarios have **scenario_seam** evidence in `tests/unit/wb_sky_mcp/test_mcp_read_interface.py` (fakeredis + `MemoryConnectionRepository` / `MemoryShopGrantReader`, real `McpBroker` / `ExportService` orchestration per plan). **14** scenarios with production PG adapters on the causal path have **boundary integration AUTHORED** but **EXECUTION=BLOCKED_AUTH** → row cannot PASS until provider run + receipt. **7** Redis-primary scenarios pass row-level seam execution without PG run but **full-change PASS** still blocked by `UNEXECUTED_REQUIRED_TESTS=6` and missing `PROVIDER_EXECUTION_RECEIPT`.

Steady-state **Already revoked connection stays denied** — covered by `test_bad_bearer_is_http_401_with_www_authenticate` (disconnect then tool call; durable revoked row, no second disconnect in WHEN).
