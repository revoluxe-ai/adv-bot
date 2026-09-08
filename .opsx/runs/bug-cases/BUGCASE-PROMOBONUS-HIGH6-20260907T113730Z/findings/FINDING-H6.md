FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z
FINDING_ID: FINDING-H6
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID: ROOT-001
TITLE: H6 pick_cashback_for_topup prefers expired package over live FEFO
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: different_invariant
STATUS: promoted_to_root_case
CHAT_REQUIRED: false
CLAIM_PRIORITY: 4
PACKET_PATH: findings/FINDING-H6.md
OWNER_CHAT:
CLAIM_TOKEN:
PACKET_PURPOSE: promotion_decision
INVARIANT: pick_cashback_for_topup обязан пропускать expired пакеты и брать следующий live FEFO row. Expired не должен попадать в WB top-up cashback overlay.
ORIGINAL_FINDING: H6 expired cashback shadows live package: pick_cashback_for_topup must skip expired packages and pick the next live FEFO row.
EVIDENCE: pick_cashback_for_topup сортирует по expiration, но не вызывает is_expired. Первый payable expired выигрывает. select_topup_balance_decision → AutoBudgetService top-up write path использует этот pick без now-filter. pool_usable_from_pick проверяет expiry только для overlay availability, не для top-up. Тест test_pick_cashback_for_topup_prefers_earliest_expiration использует даты 2026-04/05 при today 2026-09 — закрепляет выбор expired.
RUNTIME_PATH: app/shared/domains/wb/utils/balance_source.py
CAUSAL_BOUNDARY: pick_cashback_for_topup → select_topup_balance_decision → AutoBudgetService allocation/top-up
WRITE_BOUNDARY: WB campaign budget deposit with expired cashback amount
SOURCE_SNAPSHOT: intakes/INTAKE-001.md H6; results/ADJUDICATION-INTAKE-001.md
DISPOSITION: promoted_to_root_case
CREATED_AT: 2026-09-07T11:50:00Z
LAST_ACTIVITY_AT: 2026-09-08T02:27:00Z
COMPLETED_AT: 2026-09-08T02:27:00Z
NEXT_ACTION: none
RESULT_PATH: ../BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z/CASE.md
PROMOTED_CASE_ID: BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z

MODE: READ_ONLY
FORBIDDEN:
- do not claim this finding on the parent case (promoted_to_root_case; CHAT_REQUIRED=false)
- do not edit production files from this packet
