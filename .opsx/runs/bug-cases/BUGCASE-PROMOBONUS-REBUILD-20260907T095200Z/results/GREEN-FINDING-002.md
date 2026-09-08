# GREEN evidence: FINDING-002

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-002
COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/auto_budget_manager/ -vv --tb=short
PRODUCTION_HASH_BEFORE: sha256:7bff3dac792567671fb3beba0cd53b840a9c2db4cff780b4a7c010ea7f5d04c0 (app/modules/auto_budget_manager/promo_state_service.py, unchanged at RED)
PRODUCTION_HASH_AFTER: sha256:da0a710c5039fa700d812bc2a1116afedb7e9b44ea1ec192eae43dc4ba591ca0 (app/modules/auto_budget_manager/promo_state_service.py, changed vs RED)
TEST_CONTENT_SHA256: 4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: On get_campaign_balance failure, do not redis.set a fresh pool_usable=false snapshot; miss/stale -> conservative M=1
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- Adjacent pair/file: `tests/unit/auto_budget_manager/` (includes `test_promo_ledger.py`) — 5 passed, 1 warning in 0.40s (exit 0). Frozen node included and PASSED.
- `TEST_CONTENT_SHA256` of `tests/unit/auto_budget_manager/test_promo_state_service.py` equals RED frozen hash `4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5` (no test edits).
- Production `promo_state_service.py` hash after != RED before (`da0a710c...` vs `7bff3dac...`).
- Tests not edited. Production not edited this hop.

## Invariant verified

On `get_campaign_balance` failure, do not `redis.set` a fresh `pool_usable=false` snapshot; miss/stale -> conservative M=1.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/2770822420`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
