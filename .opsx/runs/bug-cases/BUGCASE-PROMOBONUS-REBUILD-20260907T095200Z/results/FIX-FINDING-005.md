# FIX-FINDING-005

## Status

Implemented leftover-fraction denominator as remaining over the top-up unit (`tranche.amount`). `campaign_budget_total` and leftover `budget_after` no longer set the mix.

## Changed paths

- `app/shared/domains/wb/utils/promo_accounting.py`

## Rationale

`campaign_ledger_from_rows` used `campaign_budget_total` when present, else `apply_spend_fefo` `reference_budget`. That reference was overwritten to leftover `budget_after`. Leftover remaining 200 over wallet/ceiling 12000 collapsed `f` to `200/12000` and `M=1/(1-f)` toward 1 while leftover stayed usable.

Invariant: leftover remaining 200 with `amount` 1000 and `budget_after` 12000 must yield `f=0.2` (`M=1.25`), not `200/12000`.

Fix:

1. In `apply_spend_fefo`, `reference_budget` is the last live leftover `tranche.amount`, not `budget_after`.
2. In `campaign_ledger_from_rows`, mix uses that top-up unit. `campaign_budget_total` stays in the signature for `load_campaign_ledgers` and is not the mix denominator.

Not in scope: FEFO expired-spend skip / journal / `promo_state_service` pool path / overlay view provider / `promo_ledger` lookback. ROOT-001 / FINDING-002 / HC-001 / FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST not reopened. Intake item 6 not started. Frozen RED test file not modified.

## Commands and results

- Frozen test SHA256: `d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9` (unchanged)
- Production SHA256 after: `1d6abbe7ef349a46ce659d2827b70ccd60e017850ec8e484b9dcd5f1e750ba1b` (`app/shared/domains/wb/utils/promo_accounting.py`)
- `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -vv --tb=short`
  - 1 passed (local sanity check only; GREEN_VERIFIER owns GREEN). Not claimed as GREEN.

ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug

CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/2026-09-07T19:14:25Z

COMMIT_CREATED: NO
MISSION_COMPLETE: no
FINDING_TERMINAL: no
