---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# READY_FOR_HOME_PC_PROVIDER_CERT_V5

PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) · change `wb-sky-mcp-read-interface`

## Prior packets (do not consume)

| Packet | Status |
|--------|--------|
| v4 (`44e5e646…`) | **SUPERSEDED_UNUSED** |
| v5 (`82b7d1a07…`, `d50fb7c0…`, `9f634ba7…`) | **SUPERSEDED_UNUSED** |
| v5 (this handoff) | **AUTHORIZED_UNUSED** |

## Final candidate (post stage `f2b96e7b` delta)

| Field | Value |
|-------|-------|
| **BRANCH** | `cursor/wb-sky-mcp-read-interface-127c` |
| **FINAL_CANDIDATE_HEAD** | `f94b856396676980fb1f5541f7668b9e440d020e` |
| **CURRENT_STAGE** | `f2b96e7b1271ad532a2113305f4337b02b723cec` |
| **MERGE_TREE** | CLEAN vs `origin/stage` |
| **PR_HEAD == BRANCH_HEAD == V5_AUDITED_HEAD** | YES |

### Stage delta integrated

- Since `2c163fc3c`: archived **decision-experiment-memory** (OpenSpec only; no runtime MCP changes).
- Overlap review: no `pyrightconfig_strict.json` / Alembic / AI Package code conflicts; MCP read-only unchanged.

### v5 packet

| Field | Value |
|-------|-------|
| **V5_PACKET_ID** | `PROVIDER-PACKET-v5` |
| **V5_AUDITED_HEAD** | `f94b856396676980fb1f5541f7668b9e440d020e` |
| **V5_RUN_SPEC_HASH** | `42e6ee0a39f9b381aa43c56aae633fbc0d042510f8081c8d1fe8629cc9c60d99` |
| **V5_CANONICAL_PYTEST_ARGV_SHA256** | `329442e445bde7c13685db79b8ab1a21fe78132ff38ae2161bf1277f1e7edf30` |
| **V5_AUTHORIZATION_ID** | `3e30fd59f4d08b650bcf75e474ea43f52434ceccf928dc7241da76e16ff73c5e` |
| **V5_AUTH_STATE** | `AUTHORIZED_UNUSED` |

**`AUTHORIZE_ONE_LIVE_RUN` (one-time; do not commit):**

```
baaae4f07aa408e78cbbe6d913166d517416202cac046be8f26d1d4b6caa06e7
```

Cloud guard **verify** (non-consuming):

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

**HOME-PC:** pull exact HEAD, preflight, **re-seal** packet (updates untracked manifest), verify, docker, single `guard run`.

## HOME-PC sequence

```bash
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git checkout cursor/wb-sky-mcp-read-interface-127c
test "$(git rev-parse HEAD)" = "f94b856396676980fb1f5541f7668b9e440d020e"

export AUTHORIZE_ONE_LIVE_RUN='<secret from this file>'

poetry run python .opsx/tools/opsx_provider_preflight.py --repo .

poetry run python .opsx/tools/opsx_seal_provider_packet.py \
  --repo . --change-id wb-sky-mcp-read-interface \
  --live-token "$AUTHORIZE_ONE_LIVE_RUN"

poetry run python .opsx/tools/opsx_provider_run_guard.py verify \
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json \
  --repo .

poetry run python .opsx/tools/opsx_provider_run_guard.py run \
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json \
  --repo .
```

## Cloud gates (this hop)

| Gate | Result |
|------|--------|
| Unit (wb_sky_mcp, opsx, migrations, decision_experiment_memory) | PASS (142) |
| pyright-strict | PASS |
| check-openspec | PASS |
| merge-tree | CLEAN |

**FINAL_STATUS:** `READY_FOR_HOME_PC_PROVIDER_CERT_V5`
