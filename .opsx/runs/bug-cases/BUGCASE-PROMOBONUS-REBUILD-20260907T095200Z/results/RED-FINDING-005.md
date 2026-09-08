# RED evidence: FINDING-005

```text
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after
BUG_CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-005
COMMAND: poetry run pytest tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -vv --tb=short
EXPECTED_FAILURE: campaign_ledger_from_rows leftover remaining 200, tranche.amount 1000, budget_after 12000, campaign_budget_total 12000 must yield fraction 0.2 (M=1.25). Current code uses remaining/(campaign_budget_total|budget_after) so fraction collapses to 200/12000.
ACTUAL_FAILURE: AssertionError at tests/unit/wb/utils/test_promo_accounting.py:196; assert Decimal('0.01666666666666666666666666667') == Decimal('0.2'); remaining=200, reference_budget=12000
FAILURE_MATCH: YES
PRODUCTION_HASH_BEFORE: sha256:4bef922a87c533cd0c202a5b665162428f89395bccbe6efea1a86d122991344b (app/shared/domains/wb/utils/promo_accounting.py, unchanged)
TEST_CONTENT_SHA256: d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9
STATUS: RED_CONFIRMED
```

## Run evidence

- pytest collected 1 item; FAILED
- exit code: 1
- failing node id: `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after`
- failure: `assert Decimal('0.01666666666666666666666666667') == Decimal('0.2')` after `campaign_ledger_from_rows` with leftover 200, amount 1000, budget_after=12000, campaign_budget_total=12000
- `200/12000` is the collapsed mix; required mix is leftover remaining over the top-up unit (`200/1000 -> 0.2`, `M=1.25`)
- `campaign_ledger_from_rows` was not mocked
- existing `test_campaign_ledger_fraction_uses_remaining_not_ceiling` kept amount=budget_after=total=1000 and still PASSES; not rewritten
- production not modified during RED authorship

## Behavior protected

Campaign leftover fraction must use remaining over tranche.amount (top-up unit), not campaign-level budget_after or campaign_budget_total. If leftover 200 is divided by 12000, M collapses toward 1 while leftover remains usable, and this test fails.
