---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# Fresh read-only re-audit — `wb-sky-mcp-read-interface` (post guard repair)

**Audited at HEAD:** `5e3c08bfbbc990fefc6a71535283d1825e80bb72`  
**PR:** #452 (OPEN, MERGEABLE)  
**No provider pytest spawned; no one-shot token consumed.**

## Canonical run block (next authorized execution)

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
test "$(git rev-parse HEAD)" = "5e3c08bfbbc990fefc6a71535283d1825e80bb72"
export POSTGRES_MASTER_HOST=127.0.0.1
export POSTGRES_PORT=5433
export POSTGRES_DBNAME=test_adv_bot_db
export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6390
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
pg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db
curl -fsS http://127.0.0.1:8124/ping >/dev/null
poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local -vv --tb=short
docker compose -f tests/docker-compose.test.yml down
```

**CANONICAL_RUN_BLOCK_SHA256:** `e5c0521e5764340654eec29594b52bdb547cab5cea2e156dc3e599ea31ea0888`  
(Runtime: `allowed_run_block_sha256()` in `.opsx/tools/opsx_provider_run_guard.py`.)

## Authorization packet (paste JSON; stale if worktree changes)

```json
{
  "audited_head": "5e3c08bfbbc990fefc6a71535283d1825e80bb72",
  "audited_status_sha256": "b05dc9a5859bca0f7eeb59fdaead8edcdfd80bc428fc7f27245aaac10a6007e4",
  "audited_tracked_diff_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "audited_untracked_manifest_sha256": "9a7c2b6a208d585c0ca0579a0f18070bdbb6a488b5f1892925fd8c70155d4c8c",
  "allowed_run_block_sha256": "e5c0521e5764340654eec29594b52bdb547cab5cea2e156dc3e599ea31ea0888",
  "allowed_run_block_text": "<exact bash block above>",
  "pytest_argv": [
    "poetry", "run", "pytest", "tests/integration/wb_sky_mcp/",
    "-m", "destructive_local", "-vv", "--tb=short"
  ],
  "provider_test_ids": [
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]",
    "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets",
    "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success"
  ],
  "postgres_host": "127.0.0.1",
  "postgres_port": 5433,
  "postgres_dbname": "test_adv_bot_db",
  "environment_classification": "destructive_local_docker_compose_test_db_5433_redis_6390"
}
```

Execute only via:  
`poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet <packet.json> --repo .`  
after Owner `AUTHORIZE_ONE_LIVE_RUN` (out-of-band; **not** bound in guard today).

## Worktree / untracked classification

| Path | Purpose |
|------|---------|
| `tests/integration/wb_sky_mcp/*` | Intended PG provider boundary tests (uncommitted) |
| `tests/support/wb_sky_mcp/*` | ContractCase helpers for provider tests |
| `tests/unit/wb_sky_mcp/test_*_stub_contract.py` | Unit parity for contracts (not provider evidence) |
| `.opsx/runs/.../receipts/PROVIDER-*.md` | Stale ERROR receipts from prior docker-less run; not certification evidence |

Logs under `.opsx/runs/...` are gitignored (not in manifest).

## Guard re-audit (spawn count before pytest)

All mismatch cases: subprocess mock `call_count=0`, `spawn_count=0`.  
Matching packet on real worktree: `verify` → `PERMIT`.  
Matching packet `run` without `--dry-run`: would `spawn_count=1` (not executed in this audit).

**Gap:** `AUTHORIZATION_STATE_INVALID` is **not** implemented in `opsx_provider_run_guard.py` (no packet field; token is procedural only).

## Environment

- Docker required: **YES** (`conftest` → `destructive_lifecycle` → compose).
- This cloud VM: `docker` **not** in PATH → execution **BLOCKED_ENVIRONMENT** here.
- `PRODUCTION_DB_POSSIBLE`: **NO** (`conftest.py` forces `127.0.0.1:5433` / `test_adv_bot_db`).
