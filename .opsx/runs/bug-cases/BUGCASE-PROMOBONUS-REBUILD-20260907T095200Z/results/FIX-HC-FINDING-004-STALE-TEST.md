# FIX-HC-FINDING-004-STALE-TEST

## Status

FIX_STATUS: FIX_APPLIED
COMMIT_CREATED: NO
MISSION_COMPLETE: no
FINDING_TERMINAL: no
GREEN_SELF_CONFIRMED: false
ACTUAL_EXECUTION_ROUTE: /opsx-fix-bug
CHOSEN_ROUTE: ROUTE_A
PRODUCTION_UNCHANGED: true

Stale sibling test now asserts remaining==150. Spend must hit live leftover, not expired leftover.

## Changed paths

- `tests/unit/wb/utils/test_promo_accounting.py`

Only `test_fefo_spend_and_expired_tranche_unusable`:
- `assert remaining == 200` -> `assert remaining == 150`
- added Russian docstring: spend must hit live leftover, not expired leftover; remaining 150

## Unchanged (forbidden)

- `test_fefo_spend_hits_live_leftover_not_expired` (FINDING-004 frozen node, remaining==150 stays)
- `app/shared/domains/wb/utils/promo_accounting.py` (already skip-expired GREEN)

## Hashes

- TEST_CONTENT_SHA256 before (RED): `cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2`
- TEST_CONTENT_SHA256 after (utf-8 file bytes): `233084e637cfaa1f4c3ac5bea151f5f1cb8a377f6f30b286ac19f2bba9f50c53`
- PRODUCTION_HASH (must stay): `4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b`
- PRODUCTION_UNCHANGED: true

## Local sanity (not GREEN)

```text
poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired -vv --tb=short
```

Result: 2 passed. Not claimed as GREEN_CONFIRMED. GREEN_VERIFIER owns `/opsx-test verify`.

## Not in scope

- production `promo_accounting.py`
- FINDING-004 frozen node body
- ROOT-001 / FINDING-002 / HC-001 / FINDING-003 (not reopened)
- intake items 5-6
- git commit / push / deploy

## Next

PRIMARY: `/opsx-test verify case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=HC-FINDING-004-STALE-TEST`
MISSION_COMPLETE: no
COMMIT_CREATED: NO
