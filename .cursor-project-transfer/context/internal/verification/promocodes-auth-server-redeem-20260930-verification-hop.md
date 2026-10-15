# Verification hop — promocodes-auth-server-redeem (2026-09-30)

Worktree: `C:/Users/vkita/my_code/game-promocodes-cloud`  
Branch: `fix/promocodes-issuance-redemption-20260927`  
HEAD: `91311ada29721cfb9aab7a00e1dc4d2a0a8d1982` (matches ledger `implementation_snapshot.provenance_head`)

## Commands executed (contract-equivalent)

| Command | Result |
|---------|--------|
| Re-verify receipts (HEAD, apply-green dirs, plan FROZEN) | PASS |
| `/opsx-next-check` via `node .opsx/tools/opsx-verification-ledger.mjs schedule --change promocodes-auth-server-redeem --write` | `CHECK_REQUIRED`, `APPLIED_FAIL`, **4/9 PASS** |
| `/opsx-pipeline NAVIGATE` | READ_ONLY advisory (see coordinator summary) |

Not run (lawful deferral): `/opsx-browser-check` re-smoke (durable FAIL unchanged; product defect open), `/tempo-verification`, `/opsx-verify mode=archive` (no GO).

## Ledger

- `plan_id`: `vp-promocodes-auth-server-redeem-35e6d08e9aa2de7b`
- `ledger_status`: ACTIVE
- **CURRENT**: `bank-promo-redemption×smoke_acceptance` — `last_result=FAIL`, `attempt_count=2`
- **PASS**: promo-redemption-api (backend_tests, security_review), progress-put-coexistence (backend_tests), bank-promo-redemption (frontend_tests)
- **PENDING**: 5 checks (bank security_review, cloud-progress hydrate ×2, frontend_build)

## Smoke failure (bounded result on disk)

`reason=PRODUCT_UI_GAP` — root observations:

1. `promo_put_guard` **TypeError: unhashable type dict** on `PUT /progress` → Bank modal «Баланс недоступен», no `POST /promo/redeem`
2. `PROMO_WRITE_AUTHORITY_CUTOVER_AT` unset in Compose API (cohort/support path)
3. `vue.config.js` devServer proxy missing `^/promo` (secondary to balance gate)

## Apply receipts

`apply-green/SLICE-001` … `009`, `013` have `GREEN.json`. No `SLICE-010`–`012` dirs (slice numbering gap on disk; Owner context claimed 001–013 GREEN).

## Archive distance

1. Product repair hop (`/opsx-apply` slice or `/opsx-bug-team` / `/opsx-fix-bug` per GRAPH browser FAIL) — **not manual edit**
2. Likely `/opsx-plan-verification` disposition if implementation snapshot digest changes (`BLOCKED_SNAPSHOT_DRIFT` otherwise)
3. `/opsx-browser-check mode=bounded` → PASS on CURRENT smoke
4. `/opsx-next-check` through remaining **5** checks → `ALL_REQUIRED_CHECKS_PASS`
5. `/opsx-verify mode=archive` (Owner GO in command output only)
6. `/opsx-archive` (separate GO)

## Owner needed

**Yes** — primary slash to open implementation repair (commands-only); optional env: set cutover in local Compose for faithful smoke.
