# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z/4ae535b7
```

## PLAIN_LANGUAGE_INVARIANT

A campaign with a living leftover success-tranche must keep overlay usable even when the common pool is empty and the tranche created_at is older than 90 days.

## TECHNICAL_INVARIANT

When promo_ledger load_campaign_ledgers reads leftover success-tranches for overlay, a tranche with remaining>0 and not expired must stay in the campaign ledger even if created_at is older than PROMO_LOOKBACK_DAYS (90d). campaign_usable and overlay usable must stay true when pool=0. The 90d lookback cutoff must not AND-stop a living leftover.

## SCOPE

promo_ledger leftover usable lookback campaign overlay campaign_usable pool

## ENTRY_CONDITIONS

leftover success-tranche remaining>0, not expired, created_at older than PROMO_LOOKBACK_DAYS (90d), pool=0

## REQUIRED_BEHAVIOR

leftover success-tranche remaining>0 and not expired must keep campaign_usable true and overlay usable true even when created_at is older than 90d lookback and pool=0

## FORBIDDEN_BEHAVIOR

90d lookback cutoff must not AND-stop a living leftover; must not drop leftover via created_at>=now-90d so campaign_usable becomes false when remaining>0 not expired and pool=0

## KNOWN_WRITERS

- app/modules/auto_budget_manager/promo_ledger.py:load_campaign_ledgers
- PromoStateService.refresh
- RedisPromoStateManager.set

## KNOWN_READERS

- shop-runner overlay campaigns[].usable
- fraction_from_cached_state
- WBShopDataManager.get_complex_advs

## PROOF_FROM_ROOT_FINDING

ROOT-001 GREEN_CONFIRMED on tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero; RED showed campaign_usable=False after 90d AND-stop; FIX removed PROMO_LOOKBACK_DAYS cutoff from leftover/spend load in promo_ledger.

## HUNT_SCOPE

promo_ledger leftover lookback campaign_usable overlay writers that AND-stop usable leftover when pool=0; bounded to leftover-usable 90d false-stop neighborhood
