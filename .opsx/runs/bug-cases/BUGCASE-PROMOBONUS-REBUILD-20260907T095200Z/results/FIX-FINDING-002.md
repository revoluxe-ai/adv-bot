# FIX-FINDING-002

## Status

Implemented skip of Redis derived snapshot on `get_campaign_balance` failure: `PromoStateService.refresh` no longer `RedisPromoStateManager.set` a fresh `pool_usable=false` empty pool.

## Changed paths

- `app/modules/auto_budget_manager/promo_state_service.py`

## Rationale

On WB `get_campaign_balance` exception the previous path logged a warning, continued with `pool_response=None`, built campaigns with `pool_usable=false`, and wrote a fresh Redis snapshot (`updated_at=now`). Overlay readers treated that as an authoritative empty pool instead of cache miss/stale conservative M=1.

Fix:

1. Record `pool_fetch_ok` only after `get_campaign_balance` returns.
2. Keep UPD ingest (PG journal) as before; do not persist watermark via a false-empty Redis snapshot.
3. If pool fetch failed, skip `RedisPromoStateManager.set` and return. Prior cache / miss / stale remains.

Not in scope: `promo_ledger.py`, `promo_accounting.py`, view_provider, journal, 90d/FEFO/leftover fraction. ROOT-001 not reopened. Intake items 3-6 not started. Frozen RED test file not modified.

## Commands and results

- Frozen test SHA256: `4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5` (unchanged)
- `poetry run pytest tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails -vv --tb=short`
  - PASS: 1 passed (local check only; GREEN_VERIFIER owns GREEN).

ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug

CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/2026-09-07T12:15:07Z

MISSION_COMPLETE: no
FINDING_TERMINAL: no
