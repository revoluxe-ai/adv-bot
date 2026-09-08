FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: H6 pick_cashback_for_topup prefers expired package over live FEFO
PRODUCTION_CLASSIFICATION: confirmed production bug
RELATION_TO_ROOT: root
STATUS: claimed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 1
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMOBONUS-H6-FIX-20260908
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z/ROOT-001/2026-09-08T02:45:00Z
PACKET_PURPOSE: adjudication
INVARIANT: pick_cashback_for_topup must skip expired packages and pick the next live FEFO row
ORIGINAL_FINDING: H6 expired cashback shadows live package
EVIDENCE: pick_cashback_for_topup сортирует по expiration, но не вызывает is_expired. Первый payable expired выигрывает. select_topup_balance_decision → AutoBudgetService top-up write path использует этот pick без now-filter. pool_usable_from_pick проверяет expiry только для overlay availability, не для top-up. Тест test_pick_cashback_for_topup_prefers_earliest_expiration использует даты 2026-04/05 при today 2026-09 — закрепляет выбор expired.
RUNTIME_PATH: app/shared/domains/wb/utils/balance_source.py
CAUSAL_BOUNDARY: pick_cashback_for_topup → select_topup_balance_decision → AutoBudgetService
WRITE_BOUNDARY: WB campaign budget deposit with expired cashback; overlay pool_usable false while later live package exists
SOURCE_SNAPSHOT: parent findings/FINDING-H6.md; parent intakes/INTAKE-001.md H6; this intakes/INTAKE-001.md
DISPOSITION:
CREATED_AT: 2026-09-08T02:27:00Z
CLAIMED_AT: 2026-09-08T02:45:00Z
LAST_ACTIVITY_AT: 2026-09-08T03:00:00Z
COMPLETED_AT:
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z
BLOCKER:
RESULT_PATH:
EPISODE_TERMINAL:
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
GREEN_EVIDENCE_PATH: results/GREEN-ROOT-001.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH:
TEST_ID: test_pick_cashback_for_topup_skips_expired_prefers_earliest_live_fefo
TEST_CONTENT_SHA256:
FANIN_PATH:

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z chat_label="SUP-PROMOBONUS-H6-FIX-20260908"

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not start FINDING-H2..H5
- do not implement H6 in this materialize hop
- do not enable RaisePlanOnPromobonuses / A1 / alembic
