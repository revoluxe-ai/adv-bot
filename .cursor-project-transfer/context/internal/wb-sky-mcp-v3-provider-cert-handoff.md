---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# v3 HOME-PC provider certification handoff

**OLD_HEAD:** `712b1f32ce21393b10d371e0c6d6196f2b5e6f40`  
**NEW_HEAD:** `73716172b093d0d1198ceb9ecc7fa3f29b3bdcd5`  
**ORIGIN_STAGE_CURRENT:** `7a6ad9b53` (fetch at seal time)

## Guard repair

Provider subprocess outcomes: `PROVIDER_PASSED` (exit 0), `PROVIDER_FAILED` (exit 5),
`PROVIDER_ERROR` (exit 6). `guard_permission=PERMITTED` does not imply pytest success.
Auth stays `AUTHORIZED_CONSUMED` after spawn on failure.

## v3 (do not reuse v1/v2)

**V3_PACKET_ID:** `PROVIDER-PACKET-v3`  
**NEW_HOME_PC_TOKEN:**

```text
AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261008-v3
```

**V3_AUTH_STATE_BEFORE_RUN:** `AUTHORIZED_UNUSED` (new `one_shot_authorization_id`)

**V3_RUN_BLOCK_HASH** (re-seal after pull): `35aae62c3ce29257dac841f9154c9a25f27e957e9e151502eea8f1d4fb8ded3f`  
**V3_AUTHORIZATION_ID:** `b3e161e8a9ab5b94c6751d6bf63381099d495151804c964db18811a31a662ff1`

After `git pull` @ NEW_HEAD:

```powershell
$env:AUTHORIZE_ONE_LIVE_RUN = 'AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261008-v3'
poetry run python .opsx/tools/opsx_provider_preflight.py --repo .
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token $env:AUTHORIZE_ONE_LIVE_RUN
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

**EXPECTED_SUCCESS_RESULT:** JSON `status=PROVIDER_PASSED`, `provider_return_code=0`, exit 0.  
**EXPECTED_FAILURE_RESULT:** JSON `status=PROVIDER_FAILED` or `PROVIDER_ERROR`, exit 5 or 6; auth still consumed.

## Stage note

`merge-tree` vs `origin/stage` shows conflict in `pyrightconfig_strict.json` (ai_package paths).
Rebase before merge needs bounded resolution — not blocking HOME-PC provider cert.

## Cloud

`PROVIDER_RUN_EXECUTED_IN_CLOUD: NO` · `V3_AUTH_CONSUMED: NO`
