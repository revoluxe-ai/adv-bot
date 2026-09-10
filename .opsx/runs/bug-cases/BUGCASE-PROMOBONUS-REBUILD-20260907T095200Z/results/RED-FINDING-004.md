# RED evidence: FINDING-004

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired -vv --tb=short
EXPECTED_FAILURE: apply_spend_fefo(expired leftover 300 + live leftover 200 + spend 50) must yield remaining 150 (spend hits live). Current code absorbs spend into expired leftover and returns remaining 200 (inflation).
ACTUAL_FAILURE: AssertionError at tests/unit/wb/utils/test_promo_accounting.py:104; assert 200 == 150
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f (app/shared/domains/wb/utils/promo_accounting.py, unchanged)
TEST_CONTENT_SHA256: cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired`
- failure: `assert 200 == 150` after `apply_spend_fefo` on expired 300 + live 200 + spend 50
- `apply_spend_fefo` was not mocked; production spend loop consumed expired leftover first
- existing `test_fefo_spend_and_expired_tranche_unusable` still asserts remaining==200 (bug-encoding); not reused as the passing expectation
- production not modified during RED authorship

## Behavior protected

Spend must reduce live leftover. Expired leftover is not usable and must not absorb spend. If spend is applied to expired leftover first, remaining stays 200 instead of 150 and this test fails.
