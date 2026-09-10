# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID
```

## PLAIN_LANGUAGE_INVARIANT

Telegram rec-bid plan_context must use promo overlay target/max pay when live promo_fraction > 0.

## TECHNICAL_INVARIANT

When `AutoShelfBidControlViewProvider.build_view` computes rec-bid `plan_context`, it must resolve the live Redis overlay `promo_fraction` and pass `fraction=` into `PlanFactProvider.get_effective_promo_plan` so overlay-scaled target/max pay are shown when `promo_fraction > 0`. A rec-bid call of `get_effective_promo_plan(adv)` without `fraction=` or `complex_adv=` treats overlay as `f=0` and surfaces unscaled AdvSetting target/max.

## SCOPE

`auto_shelf_bid_control_view_provider.build_view` rec-bid `plan_context` / `get_effective_promo_plan` (rec_bid, overlay, promo, fraction, plan_context, view_provider). Not intake items 2-6 (`promo_state_service` ledger accounting leftover journal).

## ENTRY_CONDITIONS

`build_view` rec-bid with live Redis overlay fraction > 0 (frozen test f=0.2 expects overlay 125/250 not raw 100/200).

## REQUIRED_BEHAVIOR

Pass live promo_fraction into get_effective_promo_plan so rec-bid plan_context target/max pay use overlay values.

## FORBIDDEN_BEHAVIOR

Do not call get_effective_promo_plan(adv) without fraction= or complex_adv= on the Telegram rec-bid path when overlay fraction can be > 0 (that treats f=0 and shows unscaled AdvSetting target/max).

## KNOWN_WRITERS

- `AutoShelfBidControlViewProvider.build_view` rec-bid path
- `PlanFactProvider.get_effective_promo_plan`
- Redis overlay cache via `RedisPromoStateManager.get` / `fraction_from_cached_state`

## KNOWN_READERS

- Telegram rec-bid `plan_context` (`target_order_cost` / `max_order_cost`)
- Frozen test `test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive`

## PROOF_FROM_ROOT_FINDING

ROOT-001 RED showed `plan_context.target_order_cost=100.0` vs expected overlay 125.0 at f=0.2 because `build_view` called `get_effective_promo_plan(adv)` without `fraction=` / `complex_adv=`. FIX resolved live Redis overlay fraction and passed `fraction=live_fraction` into `get_effective_promo_plan`. GREEN confirmed the frozen node PASSED with overlay 125/250, frozen test SHA256 `7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae` unchanged, and view_provider hash changed vs RED.

## HUNT_SCOPE

Other call sites that compute rec-bid / Telegram plan display via `get_effective_promo_plan` without passing live overlay fraction. Do not hunt unrelated promo ledger/balance/FEFO/journal items.
