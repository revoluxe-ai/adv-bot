# GREEN evidence: FINDING-005

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-005
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -vv --tb=short
ADJACENT_COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short
PRODUCTION_HASH_BEFORE: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (app/shared/domains/wb/utils/promo_accounting.py, unchanged at RED)
PRODUCTION_HASH_AFTER: sha256:1d6abbe7ef349a46ce659d2827b70ccd60e017850ec8e484b9dcd5f1e750ba1b (app/shared/domains/wb/utils/promo_accounting.py, changed vs RED)
TEST_CONTENT_SHA256: d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: leftover remaining 200 / amount 1000 / budget_after 12000 => fraction 0.2 (M=1.25), not 200/12000
```

## Run evidence

- Frozen TEST_ID collected 1 item; PASSED (exit 0). Same node as RED.
- Adjacent file `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short`: 7 passed, 1 warning in 0.31s (exit 0). Frozen node included and PASSED. Includes `test_campaign_ledger_fraction_uses_remaining_not_ceiling`.
- `TEST_CONTENT_SHA256` of `tests/unit/wb/utils/test_promo_accounting.py` equals RED frozen hash `d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9` (no test edits).
- Production `promo_accounting.py` hash after != RED before (`1d6abbe7...` vs `4bef922a...`). Matches FIX-FINDING-005 production SHA after.
- Tests not edited this hop. Production not edited this hop. Executor identity not reused.

## Invariant verified

Campaign leftover fraction uses remaining over the top-up unit (`tranche.amount`), not `budget_after` or `campaign_budget_total`. Leftover remaining 200 with amount 1000 and budget_after 12000 yields fraction 0.2 (`M=1.25`), not `200/12000`.

## Writer

GREEN_WRITER: `/opsx-test verify` via GREEN_VERIFIER `WEX/GREEN_VERIFIER/77aab87368`

MISSION_COMPLETE: no
FINDING_TERMINAL: no
DURABLE_FILE_WRITTEN: YES
