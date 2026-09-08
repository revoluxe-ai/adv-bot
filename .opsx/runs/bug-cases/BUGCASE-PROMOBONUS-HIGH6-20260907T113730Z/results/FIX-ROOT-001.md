# FIX evidence: ROOT-001

```text
BUG_CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: ROOT-001
COMMAND: /opsx-fix-bug
GO: yes
STATUS: PRODUCTION_PATCHED
ACTUAL_EXECUTION_ROUTE: /opsx-fix-bug
ROUTE_RECONCILIATION: MATCH
PRODUCTION_PATH: app/modules/auto_budget_manager/promo_ledger.py
PRODUCTION_HASH_BEFORE: sha256:56a47501eeeeac63876b1e805b04bacb57e7e2e39547d5c2838066da40e74575
PRODUCTION_HASH_AFTER: sha256:ddb653b68b87befc63f62154558fde66b732623a330f3801ecff3112c3917598
TESTS_EDITED: none
GREEN_WRITTEN: no
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
TEST_ID: tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero
TEST_CONTENT_SHA256: ec18863bc09e7075787173b86c854ec6019eac58394d746904b7494c59eeb72a
```

## What changed

In `load_campaign_ledgers`: leftover success-tranches and persisted spend are loaded **without** `PROMO_LOOKBACK_DAYS` cutoff.

Exact behavior:

- leftover success-tranche with remaining>0 and not expired keeps `campaign_usable=true` outside 90d when pool=0
- allocation and spend windows stay aligned (both uncapped on PG load) so remaining is not overstated by dropping spend while keeping allocation
- UPD ingest lookback (`PromoStateService._UPD_LOOKBACK_DAYS`) unchanged
- `PromoStateService.refresh` unchanged (cutoff lived in ledger load, not the caller)
- FINDING-H2..H6 not started; alembic not applied; RaisePlanOnPromobonuses not enabled

## Pytest check (optional executor re-run; not GREEN)

```text
COMMAND: poetry run pytest tests/unit/auto_budget_manager/test_promo_ledger.py::test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero tests/unit/auto_budget_manager/test_promo_ledger.py -vv --tb=short
RESULT: 5 passed (RED nodeid PASS; adjacent file PASS)
EXIT: 0
```

GREEN confirmation is owned by `/opsx-test … verify`, not this worker.

MISSION_COMPLETE: no
FINDING_TERMINAL: no
