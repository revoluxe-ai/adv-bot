# GREEN ROOT-001

**FINDING_ID:** ROOT-001  
**CASE_ID:** BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z  
**WORKER_EXECUTION_ID:** WEX/GREEN_VERIFIER/h2fdenom001  
**ATTEMPT:** 1  
**timestamp:** 2026-09-08T03:22:00+03:00

## Primary verification

**PYTEST_COMMAND:** `poetry run pytest -m unit tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -vv --tb=short`

**PYTEST_EXIT_CODE:** 0

**EXECUTED:** yes

## Supplementary promo_accounting suite

**PYTEST_COMMAND:** `poetry run pytest -m unit tests/unit/wb/utils/test_promo_accounting.py -vv --tb=short`

**PYTEST_EXIT_CODE:** 0

**EXECUTED:** yes

## NODEIDS

- `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after`
- `tests/unit/wb/utils/test_promo_accounting.py::test_payment_type_keshbek_and_cyrillic`
- `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable`
- `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired`
- `tests/unit/wb/utils/test_promo_accounting.py::test_or_active_and_stop`
- `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_fraction_uses_remaining_not_ceiling`
- `tests/unit/wb/utils/test_promo_accounting.py::test_spend_fingerprint_stable`

## Contract fields

```text
TEST_ID: test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after
BUG_CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
FINDING_ID: ROOT-001
COMMAND: /opsx-test verify
TEST_CONTENT_SHA256: 8d8738c3572470a5384480f9c659163ab352cdc7a19d42bbd2c3d47949e020d1
TEST_CONTENT_SHA256_MATCH_RED: YES
FROZEN_TEST_HASH_STATUS: MATCH
NON_WEAKEN_DELTA: none
STATUS: GREEN_CONFIRMED
TARGETED_REGRESSIONS: leftover 200 / top-up unit 1000 -> f=0.2 M=1.25; denominator tranche.amount not budget_after/campaign_budget_total
DURABLE_FILE_WRITTEN: YES
```

## Summary

Primary RED regression test and full `test_promo_accounting.py` unit suite PASS (7/7).
`reference_budget=row.amount` fix verified; campaign ledger fraction uses tranche amount.

**GREEN_WRITER:** `/opsx-test verify` (WEX/GREEN_VERIFIER/h2fdenom001)
