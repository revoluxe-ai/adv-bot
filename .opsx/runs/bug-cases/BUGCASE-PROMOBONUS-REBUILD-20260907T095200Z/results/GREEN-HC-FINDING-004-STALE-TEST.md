# GREEN evidence: HC-FINDING-004-STALE-TEST

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-FINDING-004-STALE-TEST
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short
FINDING_004_NODE: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired
FINDING_004_NODE_STILL_PASSES: YES
PRODUCTION_HASH_BEFORE: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (app/shared/domains/wb/utils/promo_accounting.py, unchanged at RED; skip-expired already live)
PRODUCTION_HASH_AFTER: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (same file; test-only stale-assertion fix; production exception path)
TEST_CONTENT_SHA256: 233084e637cfaa1f4c3ac5bea151f5f1cb8a377f6f30b286ac19f2bba9f50c53
RED_TEST_CONTENT_SHA256: cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2
FROZEN_TEST_HASH_STATUS: MATCH
TEST_CONTENT_SHA256_MATCH_POST_FIX: YES
TEST_CONTENT_SHA256_MATCH_RED: NO
SHA_CHANGE_EXPECTED: YES
NON_WEAKEN_DELTA: Owner/dispatch authorized. Assertion remaining==200 -> remaining==150 plus docstring; failing expectation preserved as remaining 150 (expired 300 + live 200 + spend 50). MATCH is current file vs post-fix SHA 233084e6..., not RED SHA cd926666....
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- `TEST_CONTENT_SHA256` utf-8 bytes of `tests/unit/wb/utils/test_promo_accounting.py` = `233084e637cfaa1f4c3ac5bea151f5f1cb8a377f6f30b286ac19f2bba9f50c53` (post-fix). MATCH vs expected post-fix SHA. Differs from RED `cd926666...` as expected (assertion 200->150).
- Production `promo_accounting.py` hash after equals RED before (`4bef922a...`). Test-only fix; production already skip-expired.
- Tests and production not edited this hop.

## Adjacent (honest; expected all-pass after stale-assert fix)

- Adjacent file `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short`: **6 passed, 1 warning, exit 0**.
- FINDING-004 frozen node `test_fefo_spend_hits_live_leftover_not_expired`: **PASSED** in the same file run.
- Sibling/frozen HC node `test_fefo_spend_and_expired_tranche_unusable`: **PASSED** (`remaining == 150`).

## Invariant verified

`apply_spend_fefo` does not apply spend to expired leftover before live leftover. Expired leftover 300 + live leftover 200 + spend 50 yields remaining 150.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/05c283a184`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
DURABLE_FILE_WRITTEN: YES
