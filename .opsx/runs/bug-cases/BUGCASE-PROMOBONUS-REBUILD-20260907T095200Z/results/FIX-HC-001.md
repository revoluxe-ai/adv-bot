# FIX-HC-001

## Retry

RETRY: true
ATTEMPT: 2 of 2
RETRY_OF: WEX/IMPLEMENTATION_EXECUTOR/5db3e08ddd
RETRY_REASON: FAIL_WRITE_BOUNDARY (attempt 1 wrote LEDGER.md and findings/HC-001.md, which are FORBIDDEN for IMPLEMENTATION_EXECUTOR)

This hop does **not** rewrite LEDGER.md or findings/. Production was already patched in attempt 1 and is left as-is.

## Status

FIX_STATUS: CONFIRMED_ALREADY_APPLIED
COMMIT_CREATED: NO
MISSION_COMPLETE: no
FINDING_TERMINAL: no
ACTUAL_EXECUTION_ROUTE: /opsx-fix-bug
CHOSEN_ROUTE: ROUTE_A

`PromoStateService.refresh` already treats a non-raising `None` from `get_campaign_balance` as fetch failure. Confirmed this hop; production not re-written.

## Changed paths

- `app/modules/auto_budget_manager/promo_state_service.py` (already patched; this hop did not mutate it)

## Hashes

- PRODUCTION_HASH_BEFORE (pre-fix, attempt 1): `da0a710c5039fa700d812bc2a1116afedb7e9b44ea1ec192eae43dc4ba591ca0`
- PRODUCTION_HASH_AFTER (expected and confirmed): `d83c97f6b96b73e9f520e96ad891642ff360ca1037136c898bdd3cf5eba45b7c`
- This hop production hash (before = after): `d83c97f6b96b73e9f520e96ad891642ff360ca1037136c898bdd3cf5eba45b7c`

## Confirmation (this hop)

1. After `await wb_modifier.get_campaign_balance()`, `pool_fetch_ok = pool_response is not None` (`promo_state_service.py:150`).
2. Exception path unchanged: `except Exception` logs warning and leaves `pool_fetch_ok` False (`:151-156`).
3. `if not pool_fetch_ok:` still skips Redis set and returns (`:179-185`).
4. Identity check, not truthiness: a successful non-None empty cashback object remains fetch-ok.

Not in scope: tests (GREEN owns verification; frozen hashes must stay), `promo_ledger.py`, `promo_accounting.py`, view_provider, journal, 90d/FEFO/leftover fraction. ROOT-001 not reopened. Intake items 3-6 not started.

## Frozen tests (unchanged)

- FINDING-002: `tests/unit/auto_budget_manager/test_promo_state_service.py` sha256 `4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5`
- HC-001 RED: `tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py` sha256 `0aebe0f2d17f9dd68069d7966e6cc110efa1f877144c2d20759b00fd41049a4f`
- FROZEN_TESTS_UNCHANGED: true

Confirmed by sha256 this hop; files not edited.

## Local sanity (not GREEN authority)

Attempt 1 ran focused pytest on the RED node (1 passed). This hop did not re-run GREEN and does not claim GREEN_CONFIRMED. GREEN_VERIFIER owns `/opsx-test verify finding=HC-001`.

## Next

PRIMARY: `/opsx-test verify finding=HC-001`
MISSION_COMPLETE: no
COMMIT_CREATED: NO
