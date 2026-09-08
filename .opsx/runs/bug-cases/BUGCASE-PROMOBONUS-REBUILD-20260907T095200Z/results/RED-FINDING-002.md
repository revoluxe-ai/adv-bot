# RED evidence: FINDING-002

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-002
COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails -vv --tb=short
EXPECTED_FAILURE: PromoStateService.refresh still RedisPromoStateManager.set(pool_usable=false, updated_at=now) after get_campaign_balance raises; overlay would treat that as a fresh empty pool instead of miss/stale -> M=1
ACTUAL_FAILURE: AssertionError at tests/unit/auto_budget_manager/test_promo_state_service.py:121; captured set kwargs pool_usable=False, pool_amount=0, campaigns[101].usable=False; log shows RuntimeError from get_campaign_balance then continue-to-set
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:7bff3dac792567671fb3beba0cd53b840a9c2db4cff780b4a7c010ea7f5d04c0 (app/modules/auto_budget_manager/promo_state_service.py, unchanged)
TEST_CONTENT_SHA256: 4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails`
- failure: `assert [{... 'pool_usable': False ...}] == []` after `get_campaign_balance` raised `RuntimeError: WB get_campaign_balance failed`
- `get_campaign_balance` was not mocked away (AsyncMock side_effect); production except path logged then called `set`
- production not modified during RED authorship

## Behavior protected

On `get_campaign_balance` failure, refresh must not write a fresh Redis snapshot with `pool_usable=false`. Overlay readers must keep miss/stale conservative M=1. Removing that guard (continue-to-set after except) must fail this test.
