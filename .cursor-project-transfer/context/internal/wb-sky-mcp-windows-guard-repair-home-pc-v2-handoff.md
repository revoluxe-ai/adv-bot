---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# Windows guard repair — Home-PC v2 handoff

**OLD_HEAD:** `b337e076e942b186c50f5103b89413a34d6fd8a8`  
**NEW_HEAD:** `712b1f32ce21393b10d371e0c6d6196f2b5e6f40`

## Defects confirmed

- `Path(file_part).parent` → Windows backslashes broke `provider_test_ids` check.
- `pytest_argv[-1]` was `--tb=short`, not integration directory.

## Repairs

- `PurePosixPath` + `pytest_targets` packet field.
- `extract_pytest_targets_from_argv()` stops before options.
- Frozen block: **guard verify → guard run only** (no direct `poetry run pytest`).
- **ALLOWED_RUN_BLOCK_DOUBLE_RUN_RISK:** was HIGH; **repaired**.

## New one-shot (v2 — old token unused)

```text
AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261007-v2
```

**NEW_ALLOWED_RUN_BLOCK_SHA256** (example seal @ `712b1f32`): `baf47a43411b40351c1fd946d4c978d00298fb11962231818c553a6d5a4cf227`  
**NEW_ONE_SHOT_AUTHORIZATION_ID:** `16247cb07b836ab389f1d05bc20a412497f4b59895331d47a97553f417ac5bda`

After `git pull` @ NEW_HEAD:

```powershell
$env:AUTHORIZE_ONE_LIVE_RUN = 'AUTHORIZE_ONE_LIVE_RUN:wb-sky-mcp-read-interface:PR452:home-pc-20261007-v2'
poetry run python .opsx/tools/opsx_seal_provider_packet.py --live-token $env:AUTHORIZE_ONE_LIVE_RUN
poetry run python .opsx/tools/opsx_provider_run_guard.py verify --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
docker compose -f tests/docker-compose.test.yml up -d test_db test_clickhouse test_redis
poetry run python .opsx/tools/opsx_provider_run_guard.py run --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json --repo .
```

Re-seal on Home-PC so `audited_head` matches pulled HEAD (packet is gitignored).

**Redis:** 6379 | **PG:** 5433 | **CH:** 8124

Cloud: verify PERMIT dry-run only; **no provider spawn**.
