FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-002
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: get_campaign_balance failure still redis.set with pool_usable=false
PRODUCTION_CLASSIFICATION: unclear
RELATION_TO_ROOT: sequential_residual
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 3
PACKET_PATH: findings/FINDING-002.md
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/2026-09-07T12:15:07Z
CLAIMED_AT: 2026-09-07T12:15:07Z
COMPLETED_AT: 2026-09-07T15:10:00Z
PACKET_PURPOSE: adjudication
INVARIANT: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY
ORIGINAL_FINDING: promo_state_service.py:127-201 — get_campaign_balance failure still redis.set with pool_usable=false (false empty pool, not stale→M=1)
EVIDENCE: INTAKE-001 HIGH item 2; RAW_INTAKE_HASH 637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794. Sequential residual after ROOT-001 closed_fixed. Exception path GREEN_CONFIRMED; HC-001 None sibling GREEN_CONFIRMED INTEGRATED then closed_fixed same family.
RUNTIME_PATH: app/modules/auto_budget_manager/promo_state_service.py
CAUSAL_BOUNDARY: get_campaign_balance failure path still redis.set with pool_usable=false (false empty pool, not stale→M=1). Exception skip applied; None sibling HC-001 identity-gated.
WRITE_BOUNDARY: Redis cache write of derived overlay/pool_usable on campaign-balance failure. Fixed: skip Redis set when fetch not ok.
SOURCE_SNAPSHOT: intakes/INTAKE-001.md item 2; team/packets/WEX_MATERIALIZER_5b0aa616a3.in.json
DISPOSITION: CLOSED_FIXED_VERIFIED
CREATED_AT: 2026-09-07T12:08:04Z
LAST_ACTIVITY_AT: 2026-09-07T15:10:00Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-FINDING-002.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-FINDING-002.md
GREEN_EVIDENCE_PATH: results/GREEN-FINDING-002.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-FINDING-002.md
TEST_ID: tests/unit/auto_budget_manager/test_promo_state_service.py::test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails
TEST_CONTENT_SHA256: 4abf693330ccdd5b2aed034bdab31936f9e66f57d6d24669d213f718005414b5
FANIN_PATH: results/FANIN.md
HUMAN_SUMMARY_PATH: results/HUMAN_SUMMARY.md
CLOSURE_EVIDENCE_PATH: results/OWNER-CLOSURE-FINDING-002.md
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

NEXT_COMMAND (finding closed_fixed; CASE residual_intake items 3-6):
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

MODE: READ_ONLY

## Terminal closure

FINDING_STATUS=closed_fixed
EPISODE_TERMINAL=FIXED
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
CLOSURE_STATUS=CLOSED_FIXED_VERIFIED
CASE_STATUS=OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON=partial_residual
RESIDUAL_INTAKE_ITEMS=3, 4, 5, 6
HC001_DISPOSITION=closed_fixed
LEARNING_STATUS=COMPLETE
LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY
PROMOTION_DECISION=RESOLVED_NO_PROMOTE
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT
MISSION_COMPLETE=no
OPEN_SAME_INVARIANT_CANDIDATES=NONE

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not classify (CLASSIFIER owns PRODUCTION_CLASSIFICATION beyond unclear)
- do not reopen ROOT-001 (closed_fixed)
- do not create FINDING-003..006 from residual intake items 3-6 in this hop
- do not rewrite results/FANIN.md
- do not git commit / push / deploy
