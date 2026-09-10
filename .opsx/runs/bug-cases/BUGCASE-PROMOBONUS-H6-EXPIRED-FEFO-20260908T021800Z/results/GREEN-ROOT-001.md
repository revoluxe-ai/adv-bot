# GREEN ROOT-001

**FINDING_ID:** ROOT-001  
**CASE_ID:** BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z  
**WORKER_EXECUTION_ID:** WEX/GREEN_VERIFIER/bccdd72803  
**ATTEMPT:** 3  
**timestamp:** 2026-09-08T03:10:54+03:00

## Primary verification

**PYTEST_COMMAND:** `poetry run pytest tests/app/modules/auto_budget_manager/test_service.py::test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo -v`

**PYTEST_EXIT_CODE:** 0

**EXECUTED:** yes

## Supplementary promo_accounting suite

**PYTEST_COMMAND:** `poetry run pytest tests/unit/wb/utils/test_promo_accounting.py -v`

**PYTEST_EXIT_CODE:** 0

**EXECUTED:** yes

## NODEIDS

- `tests/app/modules/auto_budget_manager/test_service.py::test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo`
- `tests/unit/wb/utils/test_promo_accounting.py::test_payment_type_keshbek_and_cyrillic`
- `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable`
- `tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired`
- `tests/unit/wb/utils/test_promo_accounting.py::test_or_active_and_stop`
- `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_fraction_uses_remaining_not_ceiling`
- `tests/unit/wb/utils/test_promo_accounting.py::test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after`
- `tests/unit/wb/utils/test_promo_accounting.py::test_spend_fingerprint_stable`

## Summary

Primary RED test and full promo_accounting unit suite PASS. Expired tranches skipped; earliest live FEFO tranche selected for top-up.

**DURABLE_FILE_WRITTEN:** YES
