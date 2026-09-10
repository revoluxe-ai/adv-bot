# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/LEFTOVER-FRACTION-TRANCHE-AMOUNT
```

## PLAIN_LANGUAGE_INVARIANT

Campaign leftover fraction must use remaining over the top-up unit (`tranche.amount`), not `budget_after` or `campaign_budget_total`. Leftover remaining 200 with amount 1000 and budget_after 12000 must yield fraction 0.2 (`M=1.25`), not `200/12000`.

## TECHNICAL_INVARIANT

In `apply_spend_fefo`, `reference_budget` is the last live leftover `tranche.amount`. In `campaign_ledger_from_rows`, mix uses that top-up unit. `campaign_budget_total` stays in the signature and is not the mix denominator.

## SCOPE

promo_accounting leftover mix only. Excludes ROOT-001 overlay, FINDING-002/HC-001 pool-failure, FINDING-003 90d leftover cutoff, FINDING-004 FEFO skip-expired, intake item 6 journal.

## ENTRY_CONDITIONS

campaign_ledger_from_rows leftover remaining 200, tranche.amount 1000, budget_after 12000, campaign_budget_total 12000 (frozen node test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after).

## REQUIRED_BEHAVIOR

leftover fraction = remaining / tranche.amount; 200/1000 = 0.2 (M=1.25).

## FORBIDDEN_BEHAVIOR

do not mix leftover remaining over budget_after or campaign_budget_total (200/12000 collapse).

## KNOWN_WRITERS

- apply_spend_fefo
- campaign_ledger_from_rows

## KNOWN_READERS

- load_campaign_ledgers
- frozen GREEN node

## PROOF_FROM_ROOT_FINDING

FINDING-005 RED/FIX/GREEN. Frozen TEST_CONTENT_SHA256 d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9 MATCH. Production promo_accounting.py after 1d6abbe7ef349a46ce659d2827b70ccd60e017850ec8e484b9dcd5f1e750ba1b. GREEN_CONFIRMED fraction==0.2.

## HUNT_SCOPE

Hunt CLEAR. No sibling. Do not hunt intake item 6.
