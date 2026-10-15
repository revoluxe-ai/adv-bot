---
cursor:
  subagentId: "bc-3b28c79c-f17a-5519-a8b1-88cea3328432"
---

# separate-auto-search-cpo — HOME-PC live cert result

## VERIFIED_HEAD

- Branch: `cursor/separate-auto-search-cpo-clean-a089`
- `origin/cursor/separate-auto-search-cpo-clean-a089`: `f6c18bb76843a73a0ec929d087592d50d6dcedad`
- Detached worktree HEAD matched before removal.

## Host

`HOME-PC` (Windows NT 10.0.19045)

## Execution notes

- Main checkout `C:\Users\vkita\my_code\meta-repo\adv-bot` left untouched; cert ran from detached worktree (removed after run).
- `.env` loaded from main checkout via `dotenv` path (symlink failed — elevation); no secrets logged.
- Local `.env` targets `127.0.0.1` for CH (`18123`) and PG replica (`15432`). Read-only `kubectl port-forward` brought tunnels up for the run only (not a DB write).
- Process env: `POSTGRES_SSL_MODE=disable` for loopback PG tunnel (not written to `.env`).

## Cert script

`scripts/leg_cpo_home_pc_live_cert.py` (ephemeral under removed worktree; same logic as run).

## Results

| Check | Status | Evidence |
|-------|--------|----------|
| LIVE_CH_CONNECTIVITY | PASS | `SELECT 1`; host class `localhost`; database `default_db` |
| READ_ONLY_PROVEN | PASS | PG `SELECT` + `read_only_session=True`; CH `SELECT` only; no WB |
| AUTO_RAW_RECONCILIATION | PASS | `AUTO_ADV_ID=40665427`; CPO `129.630000` raw vs snapshot |
| SEARCH_RAW_RECONCILIATION | PASS | `SEARCH_ADV_ID=40665437`; CPO `111.500000` raw vs snapshot |
| AUTO_TO_SEARCH_FALLBACK | PASS | `auto_cpo=None` when only search stats present |
| SEARCH_TO_AUTO_FALLBACK | PASS | `search_cpo=None` when only auto stats present |
| MISSING_SEARCH_REMAINS_MISSING | PASS | `MISSING_SEARCH_ADV_ID=25338885`; `search_cpo=None` |
| OBSERVED_ZERO_CASE | PASS | `adv_id=40665427` spend `129.63` orders `0` → CPO `129.63` |
| MISSING_VS_ZERO | PASS | Missing leg `None` ≠ zero-orders CPO |
| CH/PG/WB writes | NONE | — |

**CRITICAL:** NONE  
**HIGH:** NONE  
**MEDIUM:** NONE  

**FINAL_STATUS:** PASS

Observation window (UTC-local naive): `2026-10-09T17:07:42` .. `2026-10-10T17:07:42`

PG scope ids: paired `adv_setting_id=1151722186`; missing search `114995429`.
