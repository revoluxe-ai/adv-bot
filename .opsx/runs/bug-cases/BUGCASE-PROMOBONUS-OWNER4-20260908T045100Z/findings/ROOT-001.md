FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: Promo ledger recovery window omits older cashback spend
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
RELATION_TO_ROOT: INDEPENDENT_ROOT
STATUS: claimed
CHAT_REQUIRED: true
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMOBONUS-OWNER4-MATERIALIZE-20260908
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z/ROOT-001/2026-09-08T05:09:00Z
CLAIM_PRIORITY: 1
CREATED_AT: 2026-09-08T05:03:00Z
CLAIMED_AT: 2026-09-08T05:09:00Z
LAST_ACTIVITY_AT: 2026-09-08T05:09:00Z
COMPLETED_AT:
NEXT_ACTION: classify_before_impl_route
BLOCKER:
RESULT_PATH:
DISPOSITION: needs adjudication
EPISODE_TERMINAL:
RED_EVIDENCE_PATH:
GREEN_EVIDENCE_PATH:
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH:
TEST_ID:
TEST_CONTENT_SHA256:
FANIN_PATH:
PACKET_PURPOSE: adjudication

INVARIANT: needs extraction — the hunt result identifies the accounting/recovery scope but does not provide a finalized invariant.
ORIGINAL_FINDING:
  FINDING_KEY=promo-ledger-upd-recovery-gap
  SEVERITY=MED
  FILES=app/modules/auto_budget_manager/promo_state_service.py, app/modules/auto_budget_manager/promo_ledger.py
  SYMPTOM=all successful allocations and all persisted spend are loaded, but initial/stale GET /adv/v1/upd recovery is limited to 90 days, so older un-ingested cashback spend can be absent from PG and remaining overstated
  PROOF=old live allocation plus old spend not ingested
  SCOPE=accounting/recovery, tests, docstrings
EVIDENCE: The authoritative hunt result records the older live allocation and spend outside the recovery window as the proof scenario.
RUNTIME_PATH: app/modules/auto_budget_manager/promo_state_service.py; app/modules/auto_budget_manager/promo_ledger.py
CAUSAL_BOUNDARY: accounting/recovery; exact causal boundary is not supplied by the hunt result.
WRITE_BOUNDARY: app/modules/auto_budget_manager/promo_state_service.py and app/modules/auto_budget_manager/promo_ledger.py; implementation placement requires adjudication.
SOURCE_SNAPSHOT: INTAKE-001 item 1 from the complete structured hunt result; no repository re-analysis was performed.
DISPOSITION: needs adjudication
NEXT_ACTION: classify_before_impl_route

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-001-20260908"

NEXT_COMMAND (only after claim, before implementation route):
/opsx-classify-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-001 claim_token=CLAIM/BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z/ROOT-001/2026-09-08T05:09:00Z

NEXT_COMMAND (only after classify Route A, or TASK_DELTA NO → fix-bug):
/opsx-fix-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-001 claim_token=<CLAIM_TOKEN>

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not edit tests as a fix
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
