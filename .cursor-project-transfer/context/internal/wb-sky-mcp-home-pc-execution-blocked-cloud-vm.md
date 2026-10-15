---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# HOME-PC execution request — blocked on Cloud Agent VM

**Requested HEAD:** `b337e076e942b186c50f5103b89413a34d6fd8a8` — **matches** checkout.  
**Worktree:** clean.  
**Runtime:** Linux Cloud Agent (`cursor` kernel); **`docker` not in PATH**.  
**Instruction:** do not run provider certification on Cloud Agent.

**Authorization:** not consumed (no guarded spawn).

See prior handoff: `wb-sky-mcp-home-pc-redis6379-guard-env-handoff.md` (same store `internal/`).

PowerShell sequence for Owner HOME-PC:

```powershell
cd <adv-bot>
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git checkout cursor/wb-sky-mcp-read-interface-127c
git rev-parse HEAD  # must be b337e076e942b186c50f5103b89413a34d6fd8a8
$env:AUTHORIZE_ONE_LIVE_RUN = 'AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261007'
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token $env:AUTHORIZE_ONE_LIVE_RUN
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
```
