# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY
```

## PLAIN_LANGUAGE_INVARIANT

On get_campaign_balance failure, do not redis.set a fresh pool_usable=false snapshot; miss/stale -> conservative M=1.

## TECHNICAL_INVARIANT

When PromoStateService.refresh catches Exception from get_campaign_balance, it must leave pool_fetch_ok=False, skip RedisPromoStateManager.set, and return without writing a fresh redis snapshot that has pool_usable=false. Overlay readers then treat miss/stale cache as conservative M=1 instead of an authoritative empty pool.

## SCOPE

promo_state_service PromoStateService.refresh Exception path around get_campaign_balance: do not persist shop-promo-state with pool_usable=false. Excludes ROOT-001 Telegram rec-bid overlay (view_provider plan_context) and intake items 3-6 (ledger 90d / FEFO / leftover fraction / journal).

## ENTRY_CONDITIONS

PromoStateService.refresh is invoked and get_campaign_balance raises Exception (frozen RED/GREEN node: RuntimeError from WB get_campaign_balance).

## REQUIRED_BEHAVIOR

On Exception from get_campaign_balance, leave pool_fetch_ok=False, skip RedisPromoStateManager.set of a fresh pool_usable=false snapshot, and return so miss/stale stays conservative M=1.

## FORBIDDEN_BEHAVIOR

Do not redis.set a fresh shop-promo-state snapshot with pool_usable=false after get_campaign_balance Exception; that stamps updated_at=now and makes overlay readers treat a fetch failure as a known-empty pool.

## KNOWN_WRITERS

- PromoStateService.refresh
- RedisPromoStateManager.set

## KNOWN_READERS

- Overlay readers via fraction_from_cached_state / RedisPromoStateManager.get
- Frozen test test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails

## PROOF_FROM_ROOT_FINDING

FINDING-002 RED showed PromoStateService.refresh still RedisPromoStateManager.set(pool_usable=false, updated_at=now) after get_campaign_balance raised. FIX skips Redis set on Exception (pool_fetch_ok=False, return). GREEN confirmed the frozen node PASSED with TEST_CONTENT_SHA256 4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5 unchanged and Exception-path skip of Redis set.

## HUNT_SCOPE

Other get_campaign_balance failure modes that still RedisPromoStateManager.set a fresh pool_usable=false shop-promo-state (including None return without Exception). Do not hunt ROOT-001 Telegram rec-bid overlay or intake items 3-6.
