FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
FINDING_ID: ROOT-004
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: Promo cashback alias normalization and fingerprint identity are incomplete
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
RELATION_TO_ROOT: INDEPENDENT_ROOT
STATUS: available
CHAT_REQUIRED: true
PACKET_PATH: findings/ROOT-004.md
OWNER_CHAT:
CLAIM_TOKEN:
CLAIM_PRIORITY: 1
CREATED_AT: 2026-09-08T05:03:00Z
CLAIMED_AT:
LAST_ACTIVITY_AT: 2026-09-08T05:03:00Z
COMPLETED_AT:
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-004-20260908"
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

INVARIANT: needs extraction — the hunt result identifies normalization and fingerprint identity concerns but does not provide a finalized invariant.
ORIGINAL_FINDING:
  FINDING_KEY=promo-cashback-alias-fingerprint
  SEVERITY=LOW
  FILE=app/shared/domains/wb/utils/promo_accounting.py
  SYMPTOM=aliases broader than documented Keshbek/Кэшбэк and fingerprint without upd_num can collide on advert_id+upd_time+upd_sum+payment_type
  PROOF=canonical alias and idempotency/collision tests
  SCOPE=normalization/fingerprint, tests, docstrings
EVIDENCE: The authoritative hunt result records canonical alias coverage and idempotency/collision tests as the proof scenario.
RUNTIME_PATH: app/shared/domains/wb/utils/promo_accounting.py
CAUSAL_BOUNDARY: cashback normalization/fingerprint identity; exact causal boundary is not supplied by the hunt result.
WRITE_BOUNDARY: app/shared/domains/wb/utils/promo_accounting.py; implementation placement requires adjudication.
SOURCE_SNAPSHOT: INTAKE-001 item 4 from the complete structured hunt result; no repository re-analysis was performed.
DISPOSITION: needs adjudication
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-004-20260908"

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-004-20260908"

NEXT_COMMAND (only after claim, before implementation route):
/opsx-classify-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z finding=ROOT-004

NEXT_COMMAND (only after classify Route A, or TASK_DELTA NO → fix-bug):
/opsx-fix-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-004 claim_token=<CLAIM_TOKEN>

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
