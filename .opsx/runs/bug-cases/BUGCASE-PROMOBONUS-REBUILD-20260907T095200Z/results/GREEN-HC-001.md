# GREEN evidence: HC-001

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_returns_none
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-001
COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_returns_none -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/auto_budget_manager/ -vv --tb=short
PRODUCTION_HASH_BEFORE: sha256:da0a710c5039fa700d812bc2a1116afedb7e9b44ea1ec192eae43dc4ba591ca0 (app/modules/auto_budget_manager/promo_state_service.py, unchanged at RED)
PRODUCTION_HASH_AFTER: sha256:d83c97f6b96b73e9f520e96ad891642ff360ca1037136c898bdd3cf5eba45b7c (app/modules/auto_budget_manager/promo_state_service.py, changed vs RED)
TEST_CONTENT_SHA256: 0aebe0f2d17f9dd68069d7966e6cc110efa1f877144c2d20759b00fd41049a4f
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: On get_campaign_balance None return, do not redis.set a fresh pool_usable=false snapshot; miss/stale -> conservative M=1
FINDING_002_FROZEN_SHA256: 4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5
FINDING_002_FROZEN_STILL_PASSES: YES
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- Adjacent: `tests/unit/auto_budget_manager/` — 6 passed, 1 warning in 0.40s (exit 0).
- Adjacent includes frozen FINDING-002 Exception node `test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails` PASSED.
- Adjacent includes HC-001 None node `test_promo_state_none_return_false_empty.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_returns_none` PASSED.
- `TEST_CONTENT_SHA256` of `tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py` equals RED frozen hash `0aebe0f2d17f9dd68069d7966e6cc110efa1f877144c2d20759b00fd41049a4f` (no test edits).
- FINDING-002 frozen file still `4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5`.
- Production `promo_state_service.py` hash after != RED before (`d83c97f6...` vs `da0a710c...`).
- Tests not edited. Production not edited this hop.

## Invariant verified

On `get_campaign_balance` None return, do not `redis.set` a fresh `pool_usable=false` snapshot; miss/stale -> conservative M=1.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/76907a469c`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
DO_NOT_CLOSE: FINDING-002, ROOT-001
NEXT_ACTION: family fanout still needs TASK_COMPLETION / FANIN for FINDING-002 episode
