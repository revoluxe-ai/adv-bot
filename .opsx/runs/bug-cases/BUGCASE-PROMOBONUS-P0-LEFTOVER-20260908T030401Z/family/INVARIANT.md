# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-P0-LEFTOVER-20260908T030401Z/94fd0959
```

## PLAIN_LANGUAGE_INVARIANT

Пока на кампании есть usable promo (leftover или common pool), overlay fraction f MUST браться из package percent (50% → f=0.5, M=2). Elevated spend remaining = leftover/f затем STOP. Запрещено f = summed leftover / last_tranche.amount.

## TECHNICAL_INVARIANT

While usable promo exists on campaign leftover OR common pool, overlay fraction f MUST come from package percent (promo_amount/amount per tranche via promo_fraction_from_amounts). Elevated spend remaining MUST be leftover/f then STOP. MUST NOT derive f as remaining/last_tranche.amount (causes M~1e6 on multi-tranche campaigns).

## SCOPE

apply_spend_fefo / campaign_ledger_from_rows / pool_usable_from_pick → overlay consumers

## ENTRY_CONDITIONS

multi-tranche campaign ledger with live leftover promo remaining>0

## REQUIRED_BEHAVIOR

fraction=package percent; promo_multiplier≈1/(1-f); f<0.9 on multi-tranche fixture

## FORBIDDEN_BEHAVIOR

f=remaining/last_tranche.amount; overlay M explosion (~1e6); RaisePlanOnPromobonuses persist

## KNOWN_WRITERS

- app/shared/domains/wb/utils/promo_accounting.py
- app/shared/domains/wb/utils/promo_plan_multiplier.py

## KNOWN_READERS

- app/shared/domains/wb/utils/promo_overlay.py
- app/modules/plan_fact/provider.py
- app/modules/shop_runner/service_manager/wb_shop_data_manager/wb_shop_data_manager.py

## PROOF_FROM_ROOT_FINDING

results/GREEN-P0-001.md multi-tranche f=0.5 M=2 GREEN_CONFIRMED

## HUNT_SCOPE

grep/read callers deriving promo fraction from leftover vs last tranche amount; promo_accounting apply_spend_fefo neighborhood; overlay multiplier consumers
