# FIX-ROOT-001 — expired FEFO skip in pick_cashback_for_topup

**CASE_ID:** BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z  
**FINDING_ID:** ROOT-001  
**ATTEMPT:** 3  
**WORKER:** IMPLEMENTATION_EXECUTOR (WEX/IMPLEMENTATION_EXECUTOR/d8926c4370)

## FIX_STATUS

`FIX_ALREADY_APPLIED`

## Summary

The required fix is already present in the uncommitted worktree. No additional edits were made in attempt 3.

## Files changed (worktree vs HEAD)

| File | Action |
|------|--------|
| `app/shared/domains/wb/utils/balance_source.py` | Already contains fix (uncommitted) |
| `app/shared/domains/wb/utils/promo_accounting.py` | No change needed — `resolve_promo_availability` already passes `now=now` to `pick_cashback_for_topup` |

## Diff summary

In `balance_source.py`:

1. Added `_is_expired(expiration_date, *, now)` — returns `True` only when a parsed expiration date is `<= now`; undated packages are not expired.
2. Extended `pick_cashback_for_topup` with optional `now: datetime | None = None` parameter.
3. In the FEFO loop, expired packages are skipped via `_is_expired(...); continue` before computing payable amount.
4. Supporting changes: timezone-aware `_parse_iso_dt`, docstrings, and related top-up remainder logic in `select_topup_balance_decision`.

Key hunk (already applied):

```python
for cashback_sum, cashback_percent, expiration_date in rows_sorted:
    if _is_expired(expiration_date, now=ref_now):
        continue
    ...
```

## promo_accounting verification

`resolve_promo_availability` (lines 295–297) already threads `now`:

```python
cashback = pick_cashback_for_topup(
    pool_response, topup_amount=topup_amount, now=now
)
```

No edit required.

## Evidence

- Git diff patch: `results/FIX-ROOT-001-diff.patch`
- RED confirmed fix present: `results/RED-ROOT-001.md`

## Executor action

No duplicate edits applied. Worktree remains uncommitted for Owner review.
