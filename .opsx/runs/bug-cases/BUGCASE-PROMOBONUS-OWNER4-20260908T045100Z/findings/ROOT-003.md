FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z
FINDING_ID: ROOT-003
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: V3 Raise and promo composition may exceed the combined 2x ceiling
PRODUCTION_CLASSIFICATION: OWNER_SEMANTIC_DECISION_REQUIRED
RELATION_TO_ROOT: INDEPENDENT_ROOT
STATUS: available
CHAT_REQUIRED: true
PACKET_PATH: findings/ROOT-003.md
OWNER_CHAT:
CLAIM_TOKEN:
CLAIM_PRIORITY: 1
CREATED_AT: 2026-09-08T05:03:00Z
CLAIMED_AT:
LAST_ACTIVITY_AT: 2026-09-08T05:03:00Z
COMPLETED_AT:
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-003-20260908"
BLOCKER: Owner semantic decision required before implementation
RESULT_PATH:
DISPOSITION: owner decision required before implementation
EPISODE_TERMINAL:
RED_EVIDENCE_PATH:
GREEN_EVIDENCE_PATH:
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH:
TEST_ID:
TEST_CONTENT_SHA256:
FANIN_PATH:
PACKET_PURPOSE: disposition_decision

INVARIANT: question for user — choose independent composition or enforce an effective multiplier of <=2x.
ORIGINAL_FINDING:
  FINDING_KEY=v3-raise-max-promo-composition
  SEVERITY=MED
  PRODUCTION_CLASSIFICATION=OWNER_SEMANTIC_DECISION_REQUIRED
  RELATION_TO_ROOT=INDEPENDENT_ROOT
  FILE=app/modules/shop_runner/service_manager/services/auto_updater_v3/keyword_dto/dto/adv_state.py
  SYMPTOM=independent V3 Raise and promo flags compose and may exceed combined 2x
  OWNER_DECISION=accept independent composition or enforce <=2x
  SCOPE=semantic decision only
EVIDENCE: The authoritative hunt result states that independent V3 Raise and promo flags may exceed the combined 2x ceiling and explicitly forbids implementation before the Owner decision.
RUNTIME_PATH: app/modules/shop_runner/service_manager/services/auto_updater_v3/keyword_dto/dto/adv_state.py
CAUSAL_BOUNDARY: V3 Raise/promo multiplier composition; exact causal boundary is not supplied by the hunt result.
WRITE_BOUNDARY: no implementation write is authorized until the Owner chooses the composition semantics.
SOURCE_SNAPSHOT: INTAKE-001 item 3 from the complete structured hunt result; no repository re-analysis was performed.
DISPOSITION: owner decision required before implementation
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-003-20260908"

NEXT_COMMAND (when STATUS=available and CHAT_REQUIRED=true, pre-claim):
/opsx-claim-next-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z chat_label="SUP-PROMOBONUS-OWNER4-ROOT-003-20260908"

NEXT_COMMAND (only after claim, before implementation route):
/opsx-classify-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z finding=ROOT-003

NEXT_COMMAND (only after classify Route A, or TASK_DELTA NO → fix-bug):
/opsx-fix-bug case=BUGCASE-PROMOBONUS-OWNER4-20260908T045100Z intake=INTAKE-001 finding=ROOT-003 claim_token=<CLAIM_TOKEN>

MODE:
READ_ONLY

FORBIDDEN:
- do not edit production files
- do not edit tests as a fix
- do not use GO
- do not implement before the Owner semantic decision
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
