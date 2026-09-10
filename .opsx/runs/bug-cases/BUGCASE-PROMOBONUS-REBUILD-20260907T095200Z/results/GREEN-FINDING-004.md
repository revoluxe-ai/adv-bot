# GREEN evidence: FINDING-004

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short
PRODUCTION_HASH_BEFORE: sha256:271f404d1569658207038cd45092e5fa04a98efd3a6dd67b5702aae214d24f4f (app/shared/domains/wb/utils/promo_accounting.py, unchanged at RED)
PRODUCTION_HASH_AFTER: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (app/shared/domains/wb/utils/promo_accounting.py, changed vs RED)
TEST_CONTENT_SHA256: cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- `TEST_CONTENT_SHA256` utf-8 of `tests/unit/wb/utils/test_promo_accounting.py` equals RED frozen hash `cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2` (no test edits).
- Production `promo_accounting.py` hash after != RED before (`4bef922a...` vs `271f404d...`). Matches FIX-FINDING-004 production SHA after.
- Tests not edited this hop. Production not edited this hop.

## Adjacent (honest; not the GREEN gate)

`/opsx-test` verify-mode GREEN_CONFIRMED is frozen TEST_ID PASS + hash MATCH. Adjacent is reported, not used to rewrite assertions.

- Adjacent file `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short`: **1 failed, 5 passed, 1 warning, exit 1**.
- Sibling node `test_fefo_spend_and_expired_tranche_unusable`: **FAILED** `assert 150 == 200` at `tests/unit/wb/utils/test_promo_accounting.py:67`.
- That sibling historically encodes remaining==200 (same fixture as the frozen node; RED already recorded it as bug-encoding and did not reuse it as the passing expectation). After the fix, remaining is 150. Tests were not edited to make it pass.
- Frozen node in the same file run: PASSED.

## Invariant verified

`apply_spend_fefo` does not apply spend to expired leftover before live leftover. Expired leftover 300 + live leftover 200 + spend 50 yields remaining 150.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/ce96b5a340`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
DURABLE_FILE_WRITTEN: YES
