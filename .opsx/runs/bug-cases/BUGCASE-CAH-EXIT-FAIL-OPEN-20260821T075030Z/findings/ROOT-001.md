FINDING_PACKET

CASE_ID: BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: card_ab_hold EXIT fail-open when callback actor id missing
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
RELATION_TO_ROOT: root
STATUS: closed
CHAT_REQUIRED: false
CLAIM_PRIORITY: 3
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: opsx-bug-team-cah-exit-fail-open
CLAIM_TOKEN: cc0dd12550a6e2e6567733c2372b4084
CREATED_AT: 2026-08-21T07:55:30Z
CLAIMED_AT: 2026-08-21T08:05:56Z
LAST_ACTIVITY_AT: 2026-08-21T09:35:00Z
COMPLETED_AT: 2026-08-21T09:35:00Z
NEXT_ACTION: REVIEW_DIFF_AND_DECIDE_COMMIT
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-ROOT-001.md
DISPOSITION: FIXED_VERIFIED
CLAIM_PRIORITY: 3
EPISODE_TERMINAL: true
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
GREEN_EVIDENCE_PATH: results/GREEN-ROOT-001.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-ROOT-001.md
TEST_ID: tests/unit/auto_updater_v3/card_ab_hold/test_exit_rejects_missing_actor.py
TEST_CONTENT_SHA256: dfecfb3e51d1a771dbe4750f742de6ae0133216b3f0a692981e2cd4dba0a360e
FANIN_PATH: results/FAMILY-FANIN.md

PACKET_PURPOSE: adjudication

INVARIANT:
ORIGINAL_FINDING: |
  Raw intake: «Исправь баг». Supporting chat context: disable_card_ab_hold passes
  telegram_user_id=_callback_actor_id(query); when actor id is None, ownership is
  skipped and mode->OFF / clear epoch still occurs (fail-open). Fail-closed expected
  for public EXIT; None only for internal session-seam callers.
EVIDENCE: |
  CURRENT_CHAT_CONTEXT from materializer input packet; RAW_INTAKE_TEXT verbatim in intakes/INTAKE-001.md.
  No repository re-analysis; classification deferred to CLASSIFIER.
RUNTIME_PATH: app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py
CAUSAL_BOUNDARY: telegram EXIT callback actor resolution → ownership gate → session disable write
WRITE_BOUNDARY: card_ab_hold session mode/epoch mutation path (disable)
SOURCE_SNAPSHOT: PAYLOAD.CURRENT_CHAT_CONTEXT + RAW_INTAKE_TEXT from PKT/WEX/MATERIALIZER/168da3e259/IN

NEXT_COMMAND: REVIEW_DIFF_AND_DECIDE_COMMIT

MODE: READ_ONLY

## Terminal closure

CASE_STATUS=CLOSED
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
CLOSURE_STATUS=CLOSED_FIXED_VERIFIED
LEARNING_STATUS=COMPLETE
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT
HUMAN_SUMMARY_PATH=results/HUMAN_SUMMARY.md
CLOSURE_EVIDENCE_PATH=results/OWNER-CLOSURE-ROOT-001.md

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not classify or propose fix in MATERIALIZER hop
