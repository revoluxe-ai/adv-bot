---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# READY_FOR_HOME_PC_PROVIDER_CERT_V6

PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) · change `wb-sky-mcp-read-interface`

## V5 historical (immutable — do not retry or reset)

| Field | Value |
|-------|-------|
| **V5_PACKET_ID** | `PROVIDER-PACKET-v5` |
| **V5_AUDITED_HEAD** | `f94b856396676980fb1f5541f7668b9e440d020e` |
| **V5_AUTHORIZATION_ID** | `3e30fd59f4d08b650bcf75e474ea43f52434ceccf928dc7241da76e16ff73c5e` |
| **V5_FINAL_RESULT** | `FAILED` (LOCAL_ENVIRONMENT / DOCKER_PIPE_PERMISSION) |
| **V5_AUTH_STATE** | `AUTHORIZED_CONSUMED` |
| **V5_SPAWN_COUNT** | `1` |
| **provider_exit_code** | `1` |

V5 failure was disposable `.venv` **LOW integrity** blocking `dockerDesktopLinuxEngine` npipe. Remediation: raise `.venv\Scripts\python.exe`, `pytest.exe`, `py.test.exe` to **MEDIUM** integrity in the **cert worktree only**. Post-fix: `poetry run python` → `docker info` RC=0; local Docker probe pytest **1 passed**.

## V6 candidate (fresh one-shot)

| Field | Value |
|-------|-------|
| **BRANCH** | `cursor/wb-sky-mcp-read-interface-127c` |
| **V6_AUDITED_HEAD** | `f94b856396676980fb1f5541f7668b9e440d020e` |
| **CURRENT_STAGE** | `f2b96e7b1271ad532a2113305f4337b02b723cec` |
| **V6_PACKET_ID** | `PROVIDER-PACKET-v6` |
| **V6_RUN_SPEC_HASH** | `42e6ee0a39f9b381aa43c56aae633fbc0d042510f8081c8d1fe8629cc9c60d99` |
| **V6_CANONICAL_PYTEST_ARGV_SHA256** | `329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30` |
| **V6_AUTHORIZATION_ID** | `8ed2d31deac24370ff32284016aa9e313df294825bcf6faca8d6b3eb08e2ac9c` |
| **V6_AUTH_STATE** | `AUTHORIZED_UNUSED` |
| **V6_SPAWN_COUNT** | `0` |

**`AUTHORIZE_ONE_LIVE_RUN` (one-time; do not commit):**

```
a492314ac4da9634263038666dfc79f2f473322a09b6ad001a6869a29f95dbeb
```

Cloud **guard verify** (non-consuming, same HEAD):

```json
{
  "status": "PERMIT",
  "guard_permission": "PERMITTED",
  "provider_spawned": false,
  "provider_result": "NOT_RUN",
  "authorization_state": "AUTHORIZED_UNUSED",
  "spawn_count": 0
}
```

## HOME-PC sequence (after integrity remediation)

Use the **same disposable cert worktree** where `.venv` integrity was fixed.

```powershell
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git checkout cursor/wb-sky-mcp-read-interface-127c
# HEAD must be f94b856396676980fb1f5541f7668b9e440d020e

$env:AUTHORIZE_ONE_LIVE_RUN = '<secret from this file>'

poetry run python .opsx/tools/opsx_provider_preflight.py --repo .

poetry run python .opsx/tools/opsx_seal_provider_packet.py `
  --repo . --change-id wb-sky-mcp-read-interface `
  --live-token $env:AUTHORIZE_ONE_LIVE_RUN
# After seal: confirm packet_evidence_id=PROVIDER-PACKET-v6 (or set only in untracked packet JSON),
# one_shot_authorization_id matches V6_AUTHORIZATION_ID above, audited_head matches certified HEAD.

poetry run python .opsx/tools/opsx_provider_run_guard.py verify `
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json `
  --repo .

# Start tests/docker-compose.test.yml disposable stack per sealed block, then:
poetry run python .opsx/tools/opsx_provider_run_guard.py run `
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json `
  --repo .
```

Run **guard run exactly once**. Do not reuse V5 secret or ledger.

**FINAL_STATUS:** `READY_FOR_HOME_PC_PROVIDER_CERT_V6`
