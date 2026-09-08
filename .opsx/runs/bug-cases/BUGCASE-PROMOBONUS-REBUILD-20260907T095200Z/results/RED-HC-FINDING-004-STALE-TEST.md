# RED evidence: HC-FINDING-004-STALE-TEST

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-FINDING-004-STALE-TEST
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable -vv --tb=short
EXPECTED_FAILURE: assert 150 == 200 at tests/unit/wb/utils/test_promo_accounting.py:67 (stale remaining==200 after FINDING-004 skip-expired; expired leftover 300 + live leftover 200 + spend 50 now yields remaining 150)
ACTUAL_FAILURE: AssertionError at tests/unit/wb/utils/test_promo_accounting.py:67; assert 150 == 200
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (app/shared/domains/wb/utils/promo_accounting.py, unchanged this hop; post-FINDING-004 skip-expired)
TEST_CONTENT_SHA256: cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable`
- failure: `assert 150 == 200` at line 67 after `apply_spend_fefo` on expired 300 + live 200 + spend 50
- `apply_spend_fefo` was not mocked; production skip-expired (FINDING-004) returns remaining 150; sibling still asserts remaining==200
- tests/** not edited this hop; existing failing node reused
- production not modified this hop
- FINDING-004 frozen file unchanged: `tests/unit/wb/utils/test_promo_accounting.py` sha256 `cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2`
- frozen node still PASSES: `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired -vv --tb=short`

## Behavior protected

Sibling `test_fefo_spend_and_expired_tranche_unusable` still encodes the pre-FINDING-004 inflation (`remaining==200`). After skip-expired, remaining is 150 so this node fails. That fail is the RED pin. Do not claim GREEN. Do not weaken the FINDING-004 node (`remaining==150`).
