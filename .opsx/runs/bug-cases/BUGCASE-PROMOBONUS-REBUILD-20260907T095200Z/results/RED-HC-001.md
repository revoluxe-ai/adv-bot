# RED evidence: HC-001

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_returns_none
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-001
COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py -vv --tb=short
EXPECTED_FAILURE: PromoStateService.refresh still RedisPromoStateManager.set(pool_usable=false, updated_at=now) after get_campaign_balance returns None without raising (pool_fetch_ok=True at promo_state_service.py:146-147); overlay would treat that as a fresh empty pool instead of miss/stale -> M=1
ACTUAL_FAILURE: AssertionError at tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py:120; false_empty_writes == [{'shop_id': 'shop-1', 'pool_usable': False, 'pool_amount': 0, campaigns[101].usable=False, ...}] after AsyncMock(return_value=None); production did not skip Redis set
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:da0a710c5039fa700d812bc2a1116afedb7e9b44ea1ec192eae43dc4ba591ca0 (app/modules/auto_budget_manager/promo_state_service.py, unchanged this hop)
TEST_CONTENT_SHA256: 0aebe0f2d17f9dd68069d7966e6cc110efa1f877144c2d20759b00fd41049a4f
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/auto_budget_manager/test_promo_state_none_return_false_empty.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_returns_none`
- failure: `assert [{... 'pool_usable': False ...}] == []` after `get_campaign_balance` returned `None` (no Exception)
- `get_campaign_balance` was not mocked away (`AsyncMock(return_value=None)`); `refresh()` was not mocked; production set `pool_fetch_ok=True` then called `set`
- production not modified during RED authorship
- FINDING-002 frozen file unchanged: `tests/unit/auto_budget_manager/test_promo_state_service.py` sha256 `4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5`
- frozen node still PASSES: `poetry run pytest tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails -q`

## Behavior protected

On `get_campaign_balance` None return (fetch failure, no Exception), refresh must not write a fresh Redis snapshot with `pool_usable=false`. Overlay readers must keep miss/stale conservative M=1. Treating None as `pool_fetch_ok=True` and continuing to `RedisPromoStateManager.set` must fail this test. FINDING-002 Exception-only frozen test is a sibling and must remain untouched.
