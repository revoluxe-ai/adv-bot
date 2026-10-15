---
cursor:
  subagentId: "bc-1d9d0829-ea97-5f99-ac15-78ecc4eaa622"
---

# HOME-PC live cert handoff (read-only)

Cloud Agent `bc-1d9d0829` cannot place shell on HOME-PC: `Task` + `workerId` `cfa9762d` / `a5123599` still runs on Linux `cursor` (`PLACEMENT_FAIL`). Workers list shows HOME-PC online with `revoluxe-ai/adv-bot` root.

Run **only** on HOME-PC in `C:\Users\vkita\my_code\meta-repo\adv-bot` at detached `f6c18bb76843a73a0ec929d087592d50d6dcedad`. Do not print secrets.

```powershell
cd C:\Users\vkita\my_code\meta-repo\adv-bot
git fetch origin
git worktree add --detach C:\Users\vkita\my_code\cursor-sdk-task-runner\.runner-temp\leg-cpo-live-cert f6c18bb76843a73a0ec929d087592d50d6dcedad
cd C:\Users\vkita\my_code\cursor-sdk-task-runner\.runner-temp\leg-cpo-live-cert
$env:TEMP='C:\Users\vkita\my_code\cursor-sdk-task-runner\.runner-temp'
$env:TMP=$env:TEMP
poetry run python - <<'PY'
# Paste from coordinator or run cert script once added to runner tasks
PY
```

Cert script requirements: `SELECT 1` via `get_clickhouse_client`; PG `SELECT` only for `adv_id` / `search_adv_id` scope; raw SQL matching `get_stats_by_adv_ids_last_days`; `load_leg_cpo_snapshot`; compare `spend/max(orders,1)` per leg; missing Search `None`; no CH/PG/WB writes.

Cross-link: [live certification report](./separate-auto-search-cpo-live-certification.md).
