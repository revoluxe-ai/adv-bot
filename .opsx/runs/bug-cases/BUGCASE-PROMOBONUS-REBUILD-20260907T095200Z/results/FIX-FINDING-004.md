# FIX-FINDING-004

## Status

Implemented skip of expired leftover in `apply_spend_fefo` spend loop: spend no longer hits expired leftover before live leftover.

## Changed paths

- `app/shared/domains/wb/utils/promo_accounting.py`

## Rationale

FEFO sorted dated leftover by earliest expiry, then applied all spend without `is_expired` skip. Remaining then counted only live leftover. Expired leftover therefore absorbed spend and live remaining inflated.

Invariant: expired leftover 300 + live leftover 200 + spend 50 must yield remaining 150 (spend hits live). Before the fix remaining was 200.

Fix:

1. In the spend loop, `continue` when `is_expired(item.expires_at, now=now)`.
2. Keep FEFO order among live leftover (`_tranche_sort_key` unchanged).
3. Remaining filter unchanged: still skip expired leftover when summing usable remaining.

Not in scope: leftover-fraction / journal / `promo_state_service` pool path / overlay view provider / `promo_ledger` lookback. ROOT-001 / FINDING-002 / HC-001 / FINDING-003 not reopened. Intake items 5-6 not started. Frozen RED test file not modified.

## Commands and results

- Frozen test SHA256: `cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2` (unchanged)
- Production SHA256 after: `4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b` (`app/shared/domains/wb/utils/promo_accounting.py`)
- `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired -vv --tb=short`
  - 1 passed (local sanity check only; GREEN_VERIFIER owns GREEN). Not claimed as GREEN.

ACTUAL_EXECUTION_ROUTE=/opsx-fix-bug

CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/2026-09-07T16:37:42Z

COMMIT_CREATED: NO
MISSION_COMPLETE: no
FINDING_TERMINAL: no
