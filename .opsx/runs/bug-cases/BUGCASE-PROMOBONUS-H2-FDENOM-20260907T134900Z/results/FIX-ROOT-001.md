# FIX-ROOT-001 — H2 campaign f denominator (top-up unit)

**CASE_ID:** BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z  
**FINDING_ID:** ROOT-001  
**ATTEMPT:** 1  
**WORKER:** IMPLEMENTATION_EXECUTOR (WEX/IMPLEMENTATION_EXECUTOR/h2fdenom001)

## FIX_STATUS

`FIX_ALREADY_APPLIED`

## Summary

The required H2 denominator fix is already present in the worktree. Executor verified
invariant compliance and made **no duplicate edits**.

## Invariant verified

Campaign leftover 200 with top-up unit 1000 must yield f=0.2 and M=1.25.
Denominator is `tranche.amount` (top-up unit), not `budget_after` / wallet /
`campaign_budget_total`.

## Files verified (no executor change)

| File | Status |
|------|--------|
| `app/shared/domains/wb/utils/promo_accounting.py` | Fix present (untracked in worktree) |

## Code verification

### `apply_spend_fefo` (lines 210–212)

`reference_budget` is set from `row.amount` (top-up unit), not `budget_after`:

```python
if row.amount > 0:
    reference_budget = row.amount
```

### `campaign_ledger_from_rows` (lines 245–253)

`campaign_budget_total` is ignored for mix denominator; fraction uses `reference`
from `apply_spend_fefo`:

```python
del campaign_budget_total
...
if remaining > 0 and reference and reference > 0:
    fraction = promo_fraction_from_amounts(
        promo_amount=remaining, total_amount=reference
    )
```

## Test verification

```text
poetry run pytest -m unit tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -v
```

PYTEST_EXIT: 0 (PASSED)

Vector: remaining=200, amount=1000, budget_after=12000, campaign_budget_total=12000  
Asserts: fraction=0.2, M=1.25

## Pre-fix counterfactual

If `reference_budget` used `budget_after` (12000): f=200/12000≈0.0167, M≈1.017 — test FAIL.

## Executor action

No duplicate edits applied. Worktree remains uncommitted for Owner review.

## Evidence paths

- Diff patch: `results/FIX-ROOT-001-diff.patch`
- RED evidence: `results/RED-ROOT-001.md`
