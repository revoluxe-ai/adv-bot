---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# MCP certification chain — `BLOCKED_ENVIRONMENT` (Owner GO partial)

**PR:** #452  
**BASE_HEAD:** `5e3c08bfbbc990fefc6a71535283d1825e80bb72`  
**FINAL_HEAD:** `2a8f694c8ade7b79978e315f4580239983a8ad9b`  
**ORIGIN_STAGE_CURRENT:** `735aa3e77641ac22b3f3c266712c74c42767e092`

## Completed

1. Provider tests/support committed (bounded MCP PG boundary).
2. `opsx_provider_run_guard.py` — `change_id`, `one_shot_authorization_id`, ledger consumption at spawn.
3. Stale ERROR `PROVIDER-*.md` removed; `receipts/README.md` documents lifecycle.
4. Static: guard 9/9, wb_sky_mcp unit 38/38, provider collect 6, ruff PASS, scoped pyright PASS.

## Not executed (environment)

- `docker` absent on Cloud Agent VM → **no provider pytest**, **authorization not consumed**.

## Fresh fingerprints (clean worktree @ FINAL_HEAD)

| Field | SHA256 |
|-------|--------|
| STATUS | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| TRACKED_DIFF | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| UNTRACKED_MANIFEST | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| RUN_BLOCK (guard-wrapped) | `cdd866204b02e239701fdca2700ea18a0b6aeae3327b13fcad9a948d6a1e5c84` |

Home-PC: mint `one_shot_authorization_id = sha256(UTF-8(AUTHORIZE_ONE_LIVE_RUN))`, write `provider-run-packet.json`, then guarded `run`.

## MCP read surface

`READ_TOOLS` in `broker.py`: `get_profile`, `list_shops`, `get_capabilities`, `get_ai_package` only.
