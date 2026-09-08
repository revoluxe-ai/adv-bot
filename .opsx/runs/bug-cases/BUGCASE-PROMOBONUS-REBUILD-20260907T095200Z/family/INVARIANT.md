# INVARIANT

```text
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
```

## PLAIN_LANGUAGE_INVARIANT

apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150.

## TECHNICAL_INVARIANT

In apply_spend_fefo spend loop, skip leftover where is_expired(item.expires_at, now=now); remaining sums only live leftover. Same fixture as frozen GREEN node.

## SCOPE

promo_accounting.apply_spend_fefo spend loop + remaining filter. Excludes ROOT-001 overlay, FINDING-002/HC-001 pool-failure, FINDING-003 90d leftover cutoff, intake items 5-6 leftover-fraction/journal.

## ENTRY_CONDITIONS

apply_spend_fefo with expired leftover 300 + live leftover 200 + spend 50 (frozen node test_fefo_spend_hits_live_leftover_not_expired).

## REQUIRED_BEHAVIOR

skip expired leftover in spend loop; remaining == 150.

## FORBIDDEN_BEHAVIOR

do not apply spend to expired leftover before live leftover (that inflates remaining to 200).

## KNOWN_WRITERS

- apply_spend_fefo

## KNOWN_READERS

- campaign_ledger_from_rows
- load_campaign_ledgers
- frozen GREEN node
- sibling test_fefo_spend_and_expired_tranche_unusable (still stale remaining==200)

## PROOF_FROM_ROOT_FINDING

FINDING-004 RED/FIX/GREEN. Frozen TEST_CONTENT_SHA256 cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2 MATCH. Production promo_accounting.py after 4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b. GREEN_CONFIRMED remaining==150.

## HUNT_SCOPE

other apply_spend_fefo / remaining==200 siblings that still encode expired-leftover spend inflation. Already found HC-FINDING-004-STALE-TEST. Do not hunt items 5-6.
