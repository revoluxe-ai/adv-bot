---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# Home-PC handoff — Redis 6379 + guard env + sealed packet

**FINAL_HEAD:** `b337e076e942b186c50f5103b89413a34d6fd8a8`  
**ORIGIN_STAGE_CURRENT:** `c956e167393ab5258af5833336207cd5a339830d`

## Redis contract (authoritative)

**CANONICAL_REDIS_PORT: `6379`**

Reason: committed `tests/docker-compose.test.yml` maps `test_redis` as `6379:6379`;
`conftest.py` sets `REDIS_PORT=6379`. Prior audit `6390` matched aspirational
`/opsx-test-env` notes + `env.sample` comment, not shipped compose.

**REDIS_PORT_OLD_PACKET_STALE:** YES (6390)

## Guard child env

**GUARD_CHILD_ENV_DEFECT:** YES (was `env=dict(extra_env or {})` only)  
**GUARD_REPAIR_COMMIT:** `e58e6573535ad9a7b7111be2f66709dd66817888`  
`build_provider_subprocess_env()` now inherits parent env and overrides PG/Redis.

## Sealed packet (untracked; gitignored)

After `git pull` at `b337e076e`:

```bash
export AUTHORIZE_ONE_LIVE_RUN='AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261007'
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token "$AUTHORIZE_ONE_LIVE_RUN"
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
# compose up if needed, then ONE run:
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
```

**NEW_ALLOWED_RUN_BLOCK_SHA256** (after seal at HEAD): `9cc497d5b9f3adef29fa47f76de5d087251f8ddacab353192b4b0f194b107fda`  
**one_shot_authorization_id:** `867cdcec8dca95265317cb8f935b032680ce506563b508d5e0165f9ec9f54128`

Cloud Agent: **did not spawn** provider pytest; authorization **not consumed**.
