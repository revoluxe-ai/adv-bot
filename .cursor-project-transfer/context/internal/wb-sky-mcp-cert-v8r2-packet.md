---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# PROVIDER-PACKET-v8r2 — HOME-PC certification (wb-sky-mcp-read-interface)

PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452). Supersedes PROVIDER-PACKET-v8 (head `2876e8c7d`), which aborted before `guard run` (exit 52, no ledger). The **same one-shot token** is reused: it is still `AUTHORIZED_UNUSED` (no ledger / `run_result.json` exists). v5/v6/v7 tokens stay consumed. Do not use the v8 packet JSON any more (head/block hash differ).

Cloud `guard verify` only: **PERMIT**, `AUTHORIZED_UNUSED`, `spawn_count=0`, `NOT_RUN`. Do not run `guard run` on the cloud VM.

## What was wrong in v8 and what changed (head `ade6117976f31c2e0b976c7ff1c81d3516dda16b`)

| v8 symptom | Root cause | Tracked fix |
| --- | --- | --- |
| block exit 52 at ClickHouse ping | `tests/clickhouse-config/users.xml` (`<yandex>` + `<grants><database>…`) is not valid for CH 24.8 → server dies, docker proxy returns empty reply | `git rm tests/clickhouse-config/users.xml`: its `test_user` is referenced by no code (tests use `CLICK_HOUSE_USER` from `default-user.xml`, compose env). Tracked deletion, so the guard fingerprint stays honest. No assume-unchanged. |
| `pg_isready` missing on Git Bash | host binary assumed | block now probes via `docker compose … exec -T test_db pg_isready` (retry loop + final assert) |
| preflight `icacls` exit 1299 and `docker info` denied from venv python | The calling **process token is Low** (agent sandbox shell): a Low token cannot raise labels (1299) and Docker Desktop denies its pipe regardless of file labels | preflight now (a) reports `process_integrity` and FAILs with remedy when Low, (b) treats `icacls` failures as `WARN` only (label check and `docker info` are the verdict), (c) tries a `/T` tree fallback. Owner one-time machine fix documented in `.opsx/tools/README.md`. |

## Binding

| Field | Value |
| --- | --- |
| packet_evidence_id | PROVIDER-PACKET-v8r2 |
| audited_head | `ade6117976f31c2e0b976c7ff1c81d3516dda16b` on `cursor/wb-sky-mcp-read-interface-127c` |
| one_shot_authorization_id | `7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec` (unchanged) |
| canonical_pytest_argv_sha256 | `329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30` (unchanged) |
| allowed_run_block_sha256 | `085a6103a53f8bf54d1c4cab3dae602abe32546a497a64990bd8926853b03e54` |
| run_spec_sha256 | `210d68155db78c2b1b4fb6988fb7be633d95d42a68882f6f392c9facaf2eecc3` |
| status / diff / untracked | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (clean) |

## HOME-PC instructions (hard requirement: Medium-integrity terminal)

1. Open a NORMAL Git Bash from the Start menu (not the agent terminal / sandbox). `whoami /groups | grep -i "Mandatory Label"` must say `Medium Mandatory Level`. `docker info` must work. If the agent shell cannot be Medium, the Owner runs the block (this is the one-time manual path; nothing else about the cert changes).
2. Fresh worktree (do not reuse `adv-bot-mcp-v7`/`-v8`; they have local deviations):

```bash
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git worktree add ../adv-bot-mcp-v8r2 ade6117976f31c2e0b976c7ff1c81d3516dda16b
cd ../adv-bot-mcp-v8r2
test "$(git rev-parse HEAD)" = "ade6117976f31c2e0b976c7ff1c81d3516dda16b"
test -z "$(git status --porcelain)"
poetry install
```

3. Write `wb-sky-mcp-cert-v8r2-packet.json` (this folder) unchanged to `.opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json`.
4. `export AUTHORIZE_ONE_LIVE_RUN=<value in wb-sky-mcp-cert-v8-secret.txt>` (sha256 = `7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec`).
5. Run the sealed block below. Any failure before `guard run` leaves the token unused; fix the environment (never tracked files) and re-run the same block. If CH 24.8 still fails, `export TEST_CLICKHOUSE_IMAGE=<tag>` and record it. Report the `preflight` JSON and, after `guard run`, `provider_result`, `guard_status`, `spawn_count`, CLI exit.

## Sealed block

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
test "$(git rev-parse HEAD)" = "ade6117976f31c2e0b976c7ff1c81d3516dda16b"
export POSTGRES_MASTER_HOST=127.0.0.1
export POSTGRES_PORT=5433
export POSTGRES_DBNAME=test_adv_bot_db
export ALLOW_DESTRUCTIVE_TEST_DB=1
export ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export AUTHORIZE_ONE_LIVE_RUN="${AUTHORIZE_ONE_LIVE_RUN:?required}"
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
for _ in $(seq 1 30); do docker compose -f tests/docker-compose.test.yml exec -T test_db pg_isready -U test_user -d test_adv_bot_db && break; sleep 2; done
docker compose -f tests/docker-compose.test.yml exec -T test_db pg_isready -U test_user -d test_adv_bot_db
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:8124/ping >/dev/null && break; sleep 2; done
curl -fsS http://127.0.0.1:8124/ping >/dev/null
poetry run python .opsx/tools/opsx_provider_preflight.py --repo . --fix-integrity --require-docker-daemon
# PYTEST_TARGETS: tests/integration/wb_sky_mcp/
# CANONICAL_PYTEST_ARGV_SHA256: 329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml down
```

Receipt: `…/authorizations/7689ab306d8ea404efe54fd1005a066363a153aeec4af8c0e8a106a5391f68ec.json` and `….run_result.json` (PASSED/0, FAILED/5, ERROR/6). Never delete or rewrite them.
