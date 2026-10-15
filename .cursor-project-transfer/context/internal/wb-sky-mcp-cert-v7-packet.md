# PROVIDER-PACKET-v7 — HOME-PC certification

Supersedes PROVIDER-PACKET-v6 (audited head `f94b856396676980fb1f5541f7668b9e440d020e`).
V5 and V6 authorizations stay consumed. Do not reset them.

Bound head: `6761824ee938c2a4712b6f4872ebabf3d33a2557` on `cursor/wb-sky-mcp-read-interface-127c` (stage `a2e8453e7` integrated).

Cloud guard verify only: **PERMITTED**, `authorization_state=AUTHORIZED_UNUSED`, `spawn_count=0`, `provider_result=NOT_RUN`.
Do not run `guard run` on the cloud VM.

## Binding

| Field | Value |
| --- | --- |
| packet_evidence_id | PROVIDER-PACKET-v7 |
| audited_head | `6761824ee938c2a4712b6f4872ebabf3d33a2557` |
| one_shot_authorization_id | `cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af` |
| canonical_pytest_argv_sha256 | `329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30` |
| allowed_run_block_sha256 | `e46a8a0bd94c61913782a3d09ebd87d618118431cd8ee3966efc00a3ef0a700d` |
| run_spec_sha256 | `94394260d8af684caa35dfd0022944bab6af545d31d0e3b03868b5042f4fc859` |
| status / tracked diff / untracked manifest | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (clean tree; packet path is gitignored) |

pytest argv (exact, SHA-bound):

```
poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local -vv --tb=short
```

## Constraints

- Separate git worktree. Do not reuse a dirty checkout.
- Docker Desktop running. `docker info` must succeed.
- Git Bash. The sealed block is bash, not PowerShell.
- Local test stack only (`tests/docker-compose.test.yml`). No production migration. No WB API writes. No V5/V6 token reuse.
- One `guard run` only.
- Do not commit `.opsx/runs/`.

## Worktree (Git Bash)

```bash
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git worktree add ../adv-bot-mcp-v7 6761824ee938c2a4712b6f4872ebabf3d33a2557
cd ../adv-bot-mcp-v7
git rev-parse HEAD
git status --porcelain
```

`HEAD` must equal `6761824ee938c2a4712b6f4872ebabf3d33a2557`. Porcelain must be empty before writing the packet file. `poetry install` in that worktree if needed.

If Docker npipe denies the pytest child, raise `.venv` `python.exe` / `pytest.exe` to medium integrity in this worktree only. That must not change git status.

## Packet file

Write this JSON unchanged to:

`.opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json`

```json
{
  "allowed_run_block_sha256": "e46a8a0bd94c61913782a3d09ebd87d618118431cd8ee3966efc00a3ef0a700d",
  "allowed_run_block_text": "set -euo pipefail\ncd \"$(git rev-parse --show-toplevel)\"\ntest \"$(git rev-parse HEAD)\" = \"6761824ee938c2a4712b6f4872ebabf3d33a2557\"\nexport POSTGRES_MASTER_HOST=127.0.0.1\nexport POSTGRES_PORT=5433\nexport POSTGRES_DBNAME=test_adv_bot_db\nexport ALLOW_DESTRUCTIVE_TEST_DB=1\nexport ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1\nexport REDIS_HOST=127.0.0.1\nexport REDIS_PORT=6379\nexport AUTHORIZE_ONE_LIVE_RUN=\"${AUTHORIZE_ONE_LIVE_RUN:?required}\"\ndocker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis\npg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db\ncurl -fsS http://127.0.0.1:8124/ping >/dev/null\n# PYTEST_TARGETS: tests/integration/wb_sky_mcp/\n# CANONICAL_PYTEST_ARGV_SHA256: 329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30\npoetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .\npoetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .\ndocker compose -f tests/docker-compose.test.yml down\n",
  "audited_head": "6761824ee938c2a4712b6f4872ebabf3d33a2557",
  "audited_status_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "audited_tracked_diff_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "audited_untracked_manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "canonical_pytest_argv_sha256": "329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30",
  "change_id": "wb-sky-mcp-read-interface",
  "one_shot_authorization_id": "cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af",
  "packet_evidence_id": "PROVIDER-PACKET-v7",
  "postgres_dbname": "test_adv_bot_db",
  "postgres_host": "127.0.0.1",
  "postgres_port": 5433,
  "provider_test_ids": [
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_persist_and_raw_select",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_refresh_rotation_rejects_reuse",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[persist_add_get_disconnect_version]",
    "tests/integration/wb_sky_mcp/test_mcp_pg_connection_repository.py::test_sql_connection_repository_contract_cases[refresh_rotation_rejects_reuse]",
    "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_lists_only_principal_cabinets",
    "tests/integration/wb_sky_mcp/test_mcp_pg_shop_grant_reader.py::test_sql_shop_grant_reader_empty_grant_is_success"
  ],
  "pytest_argv": [
    "poetry",
    "run",
    "pytest",
    "tests/integration/wb_sky_mcp/",
    "-m",
    "destructive_local",
    "-vv",
    "--tb=short"
  ],
  "pytest_targets": [
    "tests/integration/wb_sky_mcp/"
  ],
  "redis_host": "127.0.0.1",
  "redis_port": 6379,
  "run_spec_sha256": "94394260d8af684caa35dfd0022944bab6af545d31d0e3b03868b5042f4fc859"
}
```

## One-shot secret

SHA-256 of this value is `cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af`.

```
ygC8Mzo3Vck5j2RVoFtT5No8AHxUgPHyXJBSmlRL5dDdsgFIyRkdC3-yizbfpUQ7
```

```bash
export AUTHORIZE_ONE_LIVE_RUN='ygC8Mzo3Vck5j2RVoFtT5No8AHxUgPHyXJBSmlRL5dDdsgFIyRkdC3-yizbfpUQ7'
```

## Sealed block

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
test "$(git rev-parse HEAD)" = "6761824ee938c2a4712b6f4872ebabf3d33a2557"
export POSTGRES_MASTER_HOST=127.0.0.1
export POSTGRES_PORT=5433
export POSTGRES_DBNAME=test_adv_bot_db
export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export AUTHORIZE_ONE_LIVE_RUN="${AUTHORIZE_ONE_LIVE_RUN:?required}"
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
pg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db
curl -fsS http://127.0.0.1:8124/ping >/dev/null
# PYTEST_TARGETS: tests/integration/wb_sky_mcp/
# CANONICAL_PYTEST_ARGV_SHA256: 329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml down
```

Compose mounts are `./postgres-init` and `./clickhouse-config` relative to `tests/`. Startup must not create `tests/tests/`. If that path appears, stop before `guard run`.

## Expected durable outputs

Ledger:

`.opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/authorizations/cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af.json`

`authorization_state` = `AUTHORIZED_CONSUMED` after a successful claim. No secret in the file.

Receipt:

`.opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/authorizations/cdd533556b8504421cf7053b016cb1a62fcddad5b9fc2b69d8126af784ff72af.run_result.json`

| provider_result | guard_status | provider_spawned | spawn_count | CLI exit |
| --- | --- | --- | --- | --- |
| NOT_RUN | PERMIT on verify only (no receipt yet) | false | 0 | 0 |
| PASSED | PROVIDER_PASSED | true | 1 | 0 |
| FAILED | PROVIDER_FAILED | true | 1 | 5 |
| ERROR | PROVIDER_ERROR | true | 1 | 6 |

A consumed ledger without this receipt is `CERTIFICATION_EVIDENCE_CONFLICT`. Do not delete or rewrite either file. Do not rerun.

## Stop conditions

- Fingerprint mismatch before any ledger file: fix the worktree; the token is still unused.
- If a ledger exists, read the receipt. Do not issue another run on this authorization.
