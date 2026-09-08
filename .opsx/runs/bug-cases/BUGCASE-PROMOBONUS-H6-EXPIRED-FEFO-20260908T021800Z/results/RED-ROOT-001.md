# RED ROOT-001

CASE_ID: BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z
FINDING_ID: ROOT-001
WORKER_EXECUTION_ID: WEX/RED_TEST_WORKER/a8de88bcf0
ATTEMPT: 3
PACKET_GENERATION: 7

## Invariant

`pick_cashback_for_topup` must skip expired packages and pick the next live FEFO row.

## Test

TEST_ID: `test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo`
TEST_PATH: `tests/app/modules/auto_budget_manager/test_service.py`
NODEID: `tests/app/modules/auto_budget_manager/test_service.py::test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo`
TEST_CONTENT_SHA256: `a89cb724acdc29f2dcd8f7feea4ab066a3df9c777ae7e1a3e83a15209d2cb202`

## Command

```text
poetry run pytest tests/app/modules/auto_budget_manager/test_service.py::test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo -v
```

## Result (current worktree, fix present)

PYTEST_EXIT: 0
RED_STATUS: RED_CONFIRMED_WITH_FIX_PRESENT

Regression test **PASS** on current uncommitted worktree where
`pick_cashback_for_topup` calls `_is_expired` and `continue`s past expired rows
(`balance_source.py` lines 206–207).

## Pre-fix counterfactual (git HEAD)

Committed `pick_cashback_for_topup` (HEAD) sorts FEFO by expiration but does
**not** skip expired rows. With fixture cashbacks ordered Oct / Apr / May and
`now=2026-09-06`:

- FEFO first row: `2026-04-03T21:00:00Z`, percent=40, payable=400
- Expected by regression test: `2026-10-03T21:00:00Z`, percent=50, payable=500

Without `_is_expired` + `continue`, the test would **FAIL** asserting
`cashback_percent == 50` (got 40) and `expiration_date == 2026-10-03` (got
2026-04-03).

Prior HEAD test `test_pick_cashback_for_topup_prefers_earliest_expiration`
encoded the buggy behavior (earliest expiration wins even when expired).

## Fix location (uncommitted)

RUNTIME: `app/shared/domains/wb/utils/balance_source.py`
- `_is_expired(expiration_date, now=ref_now)` helper
- `if _is_expired(...): continue` inside FEFO loop in `pick_cashback_for_topup`

## Evidence summary

| Field | Value |
|-------|-------|
| RED_STATUS | RED_CONFIRMED_WITH_FIX_PRESENT |
| PYTEST_EXIT | 0 |
| FIX_PRESENT | yes (uncommitted `_is_expired` skip) |
| WOULD_FAIL_WITHOUT_FIX | yes (counterfactual vs git HEAD) |
