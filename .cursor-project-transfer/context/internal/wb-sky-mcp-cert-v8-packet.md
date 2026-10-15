---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

> **SUPERSEDED by `wb-sky-mcp-cert-v8r2-packet.md`** (head `ade6117976f31c2e0b976c7ff1c81d3516dda16b`). v8 aborted before guard run; token unused and reused by v8r2.

# PROVIDER-PACKET-v8 — HOME-PC certification (wb-sky-mcp-read-interface)

PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452). Supersedes v7 (token `cdd53355…72af` is `AUTHORIZED_CONSUMED`, `PROVIDER_FAILED`; never reset it). v5/v6 stay consumed too.

Cloud `guard verify` only: **PERMIT**, `AUTHORIZED_UNUSED`, `spawn_count=0`, `provider_result=NOT_RUN`. Do not run `guard run` on the cloud VM.

## Why v8 has a NEW head (not 6761824ee)

v7 on `6761824ee` failed twice over: (1) Docker Desktop pipe denied to the pytest child (Low-integrity `.venv` launchers; the v7 packet only said "if denied, raise integrity", and nothing in the sealed block checked it before the token was claimed), (2) `clickhouse-server:latest` is now 26.x and rejects `tests/clickhouse-config/users.xml`. The HOME-PC local workaround (deleting `users.xml` + `git update-index --assume-unchanged`) hides a tracked deviation from the guard's porcelain/diff fingerprint, so it cannot be reused as cert evidence. Fixing (2) requires a tracked change, hence a new head. Delta vs `6761824ee` is test-infra only (4 files): compose image pin, preflight tool, seal tool, unit test. No `app/` change.

## Binding

| Field | Value |
| --- | --- |
| packet_evidence_id | PROVIDER-PACKET-v8 |
| audited_head | `2876e8c7dc2f63ed26565c566849981107aebb23` (branch `cursor/wb-sky-mcp-read-interface-127c`) |
| one_shot_authorization_id | `7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec` |
| canonical_pytest_argv_sha256 | `329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30` (unchanged from v5-v7) |
| allowed_run_block_sha256 | `952aa6e809b6159a894886841a3d676cb1bbd7304488e4e4fe1ed4048709dd3c` |
| run_spec_sha256 | `0a8a69b3cc8ebb8a25caa3e3814b1c4bc1eed7cc1019608b0ae3d2093493c80e` |
| status / tracked diff / untracked manifest | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (clean tree) |

pytest argv (packet-only): `poetry run pytest tests/integration/wb_sky_mcp/ -m destructive_local -vv --tb=short`

## HOME-PC steps (Git Bash, Docker Desktop running)

Use a FRESH worktree (do not reuse `adv-bot-mcp-v7`: it has the consumed v7 ledger, deleted `users.xml` and an assume-unchanged flag).

```bash
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git worktree add ../adv-bot-mcp-v8 2876e8c7dc2f63ed26565c566849981107aebb23
cd ../adv-bot-mcp-v8
git rev-parse HEAD            # must equal 2876e8c7dc2f63ed26565c566849981107aebb23
git status --porcelain        # must be empty
poetry install
```

No manual icacls step is needed: the sealed block runs `opsx_provider_preflight.py --fix-integrity --require-docker-daemon`, which raises `.venv\Scripts\{python,pytest,py.test}.exe` to Medium, then fails closed (before any ledger file exists) if a launcher is still Low, if `docker info` from the venv python fails, if any `git ls-files -v` hidden flag / dirty tree / stray `tests/tests` exists. Those failures do not consume the token.

If the pinned ClickHouse (`24.8`) does not start with the repo config, set `export TEST_CLICKHOUSE_IMAGE=<another pinned tag>` BEFORE the block (do not edit tracked files, do not delete `users.xml`). The ping step is non-consuming. Record the tag used in the report.

Write this JSON unchanged to `.opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json` (the same file is copied next to this note as `wb-sky-mcp-cert-v8-packet.json`).

## One-shot secret

SHA-256 is `7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec`. Value: see `wb-sky-mcp-cert-v8-secret.txt` in this folder.

```bash
export AUTHORIZE_ONE_LIVE_RUN='hTKmIbhlTTS5YlBd61lw6L0WYVvJ0LYIKnc5GrOzvbCjh8SRs_bfJ5Sk5_py3k9M'
```

## Sealed block

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
test "$(git rev-parse HEAD)" = "2876e8c7dc2f63ed26565c566849981107aebb23"
export POSTGRES_MASTER_HOST=127.0.0.1
export POSTGRES_PORT=5433
export POSTGRES_DBNAME=test_adv_bot_db
export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export AUTHORIZE_ONE_LIVE_RUN="${AUTHORIZE_ONE_LIVE_RUN:?required}"
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
for _ in $(seq 1 30); do pg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db && break; sleep 2; done
pg_isready -h 127.0.0.1 -p 5433 -U test_user -d test_adv_bot_db
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:8124/ping >/dev/null && break; sleep 2; done
curl -fsS http://127.0.0.1:8124/ping >/dev/null
poetry run python .opsx/tools/opsx_provider_preflight.py --repo . --fix-integrity --require-docker-daemon
# PYTEST_TARGETS: tests/integration/wb_sky_mcp/
# CANONICAL_PYTEST_ARGV_SHA256: 329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml down
```

## Receipt expectations

Ledger `…/authorizations/7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec.json` (`AUTHORIZED_CONSUMED` after claim) and `…/7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec.run_result.json`. Same result table as v7 (PASSED/0, FAILED/5, ERROR/6). Do not delete or rewrite either. Report `provider_result`, `guard_status`, `provider_spawned`, `spawn_count`, CLI exit, ClickHouse image tag used, and the preflight JSON.
