# GREEN evidence: ROOT-001

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero
BUG_CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: ROOT-001
COMMAND: /opsx-test verify
TARGETED_PYTEST: poetry run pytest tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_ledger.py -vv --tb=short
EXIT_CODE: 0
PRODUCTION_PATCHED: YES
PRODUCTION_HASH_BEFORE: sha256:56a47501eeeeac63876b1e805b04bacb57e7e2e39547d5c2838066da40e74575 (app/modules/auto_budget_manager/promo_ledger.py, RED); sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f (app/shared/domains/wb/utils/promo_accounting.py); sha256:adace8040975ab7476396137cb9e71699ff770af648f8d060916add4054a70bc (app/shared/domains/wb/utils/promo_overlay.py)
PRODUCTION_HASH_AFTER: sha256:ddb653b68b87befc63f62154558fde66b732623a330f3801ecff3112c3917598 (app/modules/auto_budget_manager/promo_ledger.py, changed vs RED; matches FIX-ROOT-001); sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f (app/shared/domains/wb/utils/promo_accounting.py, unchanged); sha256:adace8040975ab7476396137cb9e71699ff770af648f8d060916add4054a70bc (app/shared/domains/wb/utils/promo_overlay.py, unchanged)
TEST_CONTENT_SHA256: ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: leftover success-tranche remaining>0, not expired, created_at older than 90d, pool=0 keeps campaign_usable=true and overlay usable=true (no 90d AND-stop)
DURABLE_FILE_WRITTEN: YES
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- Adjacent `tests/unit/auto_budget_manager/test_promo_ledger.py`: collected 4 items; 4 passed, 1 warning in 0.43s (exit 0). Frozen node included and PASSED.
- `TEST_CONTENT_SHA256` of `tests/unit/auto_budget_manager/test_promo_ledger.py` equals RED frozen hash `ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a` (no test edits).
- Production `promo_ledger.py` hash after ≠ RED before (`ddb653b6…` vs `56a47501…`); equals FIX `PRODUCTION_HASH_AFTER`.
- Tests not edited this hop. Production not edited this hop. `production_patched` already in place from `/opsx-fix-bug` GO.
- FINDING-H2..H6 not started. Finding not closed.

## Invariant verified

A non-expired leftover success-tranche with `remaining>0` and `created_at` older than `PROMO_LOOKBACK_DAYS` keeps `campaign_usable` and overlay usable true when the common pool is empty.

## Writer

GREEN_WRITER: `/opsx-test verify`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
