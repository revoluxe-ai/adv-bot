# RED ROOT-001

CASE_ID: BUGCASE-PROMOBONUS-H2-FDENOM-20260907T134900Z
FINDING_ID: ROOT-001
WORKER_EXECUTION_ID: WEX/RED_TEST_WORKER/h2fdenom001
ATTEMPT: 1

## Invariant

Campaign leftover 200 при top-up unit 1000 обязан давать f=0.2 и M=1.25.
Знаменатель — `tranche.amount` (top-up unit), не `budget_after` / wallet.

## Test

TEST_ID: `test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after`
TEST_PATH: `tests/unit/wb/utils/test_promo_accounting.py`
NODEID: `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after`
TEST_CONTENT_SHA256: `8d8738c3572470a5384480f9c659163ab352cdc7a19d42bbd2c3d47949e020d1`
TEST_FILE_SHA256: `d2b77e376699bfe70729aec6a028759353a20d1a6d4a35fef2dfdce3532954a9`

Vector: remaining=200, amount=1000, budget_after=12000, campaign_budget_total=12000.
Asserts: `fraction == Decimal("0.2")`, `promo_multiplier(fraction) == Decimal("1.250000")`.

## Command

```text
poetry run pytest -m unit tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after -v
```

## Result (current worktree, fix present)

PYTEST_EXIT: 0
RED_STATUS: RED_CONFIRMED_WITH_FIX_PRESENT
DURABLE_FILE_WRITTEN: YES

Regression test **PASS** on current worktree where `apply_spend_fefo` sets
`reference_budget = row.amount` (top-up unit), and `campaign_ledger_from_rows`
computes `fraction = remaining / reference` (`promo_accounting.py` lines
210–212, 249–253).

## Pre-fix counterfactual (budget_after denominator)

If `reference_budget` were taken from `row.budget_after` (12000) instead of
`row.amount` (1000):

- f = 200 / 12000 ≈ 0.0167 (not 0.2)
- M = 1 / (1 − 0.0167) ≈ 1.017 (not 1.25)

The regression test would **FAIL** on both assertions. Prior test
`test_campaign_ledger_fraction_uses_remaining_not_ceiling` used
amount=budget_after=campaign_budget_total=1000 and could not catch this collapse.

## Fix location (uncommitted worktree)

RUNTIME: `app/shared/domains/wb/utils/promo_accounting.py`
- `_LeftoverRow.amount` preserved from tranche
- `reference_budget = row.amount` when `row.amount > 0`
- `campaign_ledger_from_rows` ignores `campaign_budget_total` for mix denominator

## Evidence summary

| Field | Value |
|-------|-------|
| RED_STATUS | RED_CONFIRMED_WITH_FIX_PRESENT |
| PYTEST_EXIT | 0 |
| FIX_PRESENT | yes (uncommitted `promo_accounting.py`) |
| WOULD_FAIL_WITHOUT_FIX | yes (200/12000 ≠ 0.2) |
| DURABLE_FILE_WRITTEN | YES |
