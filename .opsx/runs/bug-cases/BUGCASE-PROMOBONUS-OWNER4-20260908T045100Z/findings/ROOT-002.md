FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
FINDING_ID: ROOT-002
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: Watchdog overlay refresh is visible one tick late
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
RELATION_TO_ROOT: INDEPENDENT_ROOT
STATUS: available
CHAT_REQUIRED: true
PACKET_PATH: findings/ROOT-002.md
OWNER_CHAT:
CLAIM_TOKEN:
CLAIM_PRIORITY: 1
CREATED_AT: 2026-09-08T05:03:00Z
CLAIMED_AT:
LAST_ACTIVITY_AT: 2026-09-08T05:03:00Z
COMPLETED_AT:
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-002-20260908"
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

INVARIANT: needs extraction — the hunt result identifies watchdog overlay timing and the stale fail-closed policy but does not provide a finalized invariant.
ORIGINAL_FINDING:
  FINDING_KEY=watchdog-overlay-next-tick-lag
  SEVERITY=MED
  FILES=app/modules/shop_runner/service_manager/manager.py around line 826 and related promo state/cache code
  SYMPTOM=refresh/derived DTO ordering leaves one-tick overlay lag, while documented 15-minute stale fail-closed behavior disables uplift during live promo
  PROOF=timing regression and explicit stale policy test
  SCOPE=watchdog overlay timing, tests, docstrings
EVIDENCE: The authoritative hunt result records a timing regression and an explicit stale-policy test as the proof scenario.
RUNTIME_PATH: app/modules/shop_runner/service_manager/manager.py around line 826; related promo state/cache code
CAUSAL_BOUNDARY: watchdog overlay timing; exact causal boundary is not supplied by the hunt result.
WRITE_BOUNDARY: app/modules/shop_runner/service_manager/manager.py and related promo state/cache code; implementation placement requires adjudication.
SOURCE_SNAPSHOT: INTAKE-001 item 2 from the complete structured hunt result; no repository re-analysis was performed.
DISPOSITION: needs adjudication
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-002-20260908"

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-002-20260908"

NEXT_COMMAND (only after claim, before implementation route):
/opsx-classify-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z finding=ROOT-002

NEXT_COMMAND (only after classify Route A, or TASK_DELTA NO → fix-bug):
/opsx-fix-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-002 claim_token=<CLAIM_TOKEN>

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
