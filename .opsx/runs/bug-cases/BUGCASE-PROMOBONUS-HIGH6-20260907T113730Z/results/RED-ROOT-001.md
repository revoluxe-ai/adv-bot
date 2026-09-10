# RED evidence: ROOT-001

```text
TEST_ID: tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero
BUG_CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: ROOT-001
COMMAND: /opsx-test
TARGETED_PYTEST: poetry run pytest tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero -vv --tb=short
EXPECTED_FAILURE: leftover success-tranche remaining>0, not expired, created_at older than 90d, pool=0 must keep campaign_usable=true and overlay usable=true; current load_campaign_ledgers AND-stops via created_at>=now-90d so campaign_usable becomes false
ACTUAL_FAILURE: AssertionError: assert False is True (availability.campaign_usable) at tests/unit/auto_budget_manager/test_promo_ledger.py:238; PromoAvailability(pool_usable=False, pool_amount=0, pool_fraction=Decimal('0'), campaign_usable=False, campaign_remaining=0, campaign_fraction=Decimal('0'), campaign_expires_at=None, fraction=Decimal('0'), usable=False)
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:56a47501eeeeac63876b1e805b04bacb57e7e2e39547d5c2838066da40e74575 (app/modules/auto_budget_manager/promo_ledger.py, unchanged); sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f (app/shared/domains/wb/utils/promo_accounting.py, unchanged); sha256:adace8040975ab7476396137cb9e71699ff770af648f8d060916add4054a70bc (app/shared/domains/wb/utils/promo_overlay.py, unchanged)
TEST_CONTENT_SHA256: ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- adjacent `tests/unit/auto_budget_manager/test_promo_ledger.py`: 3 passed, 1 failed (the RED node)
- exit code: 1
- failing node id: `tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero`
- failure: `assert availability.campaign_usable is True` → `False`; `campaign_remaining=0`, `usable=False` (pool empty)
- causal path exercised: production `load_campaign_ledgers` → `load_success_tranches` SQL `created_at >= now-90d` (fake session honors that predicate) → `campaign_ledger_from_rows` remaining=0 → `resolve_promo_availability` AND-stop
- production not modified during RED authorship
- GO not issued; FINDING-H2..H6 not started

## Behavior protected

A non-expired leftover success-tranche with `remaining>0` and `created_at` older than `PROMO_LOOKBACK_DAYS` must keep `campaign_usable` and overlay usable true when common pool is empty. Dropping that tranche via the 90d ledger window is a false AND-stop.
