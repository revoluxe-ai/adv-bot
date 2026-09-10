FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-003
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: promo_ledger.py 90-day lookback drops campaign remaining
PRODUCTION_CLASSIFICATION: FALSE_POSITIVE
RELATION_TO_ROOT: sequential_residual
STATUS: closed_false_positive
CHAT_REQUIRED: true
CLAIM_PRIORITY: 3
PACKET_PATH: findings/FINDING-003.md
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-003/2026-09-07T15:33:26Z
CLAIMED_AT: 2026-09-07T15:33:26Z
COMPLETED_AT: 2026-09-07T16:10:12Z
PACKET_PURPOSE: adjudication
INVARIANT: leftover remaining must not be dropped by a 90d lookback into a false AND-stop — already held; leftover-usable load_campaign_ledgers passes no cutoff
ORIGINAL_FINDING: promo_ledger.py 90-day lookback drops campaign remaining -> false AND-stop vs Owner availability law
EVIDENCE: INTAKE-001 HIGH item 3; RAW_INTAKE_HASH 637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794. Sequential residual after ROOT-001 closed_fixed and FINDING-002+HC-001 closed_fixed. CLASSIFIER FALSE_POSITIVE / ROUTE_C: leftover-usable load does not apply 90d cutoff. Hunt CLEAR. Closed closed_false_positive; no implementation.
RUNTIME_PATH: app/modules/auto_budget_manager/promo_ledger.py
CAUSAL_BOUNDARY: Reported 90-day leftover cutoff is a misread of UPD ingest recovery (PROMO_LOOKBACK_DAYS=90 in PromoStateService._resolve_upd_from_date). Leftover-usable load_campaign_ledgers does not pass cutoff=.
WRITE_BOUNDARY: No production write. Route C CLOSED_NO_IMPLEMENTATION.
SOURCE_SNAPSHOT: intakes/INTAKE-001.md item 3; team/packets/WEX_MATERIALIZER_efd2d1333b.in.json
DISPOSITION: CLOSED_FALSE_POSITIVE
CREATED_AT: 2026-09-07T15:24:00Z
LAST_ACTIVITY_AT: 2026-09-07T16:10:12Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-FINDING-003.md
EPISODE_TERMINAL: FALSE_POSITIVE
RED_EVIDENCE_PATH:
GREEN_EVIDENCE_PATH:
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH:
TEST_ID:
TEST_CONTENT_SHA256:
FANIN_PATH: results/FANIN.md
HUMAN_SUMMARY_PATH: results/HUMAN_SUMMARY.md
CLOSURE_EVIDENCE_PATH: results/OWNER-CLOSURE-FINDING-003.md
CLASSIFICATION: FALSE_POSITIVE
CHOSEN_ROUTE: ROUTE_C
FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

NEXT_COMMAND (finding closed_false_positive; CASE residual_intake items 4-6):
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

MODE: READ_ONLY

## Terminal closure

FINDING_STATUS=closed_false_positive
FINDING_TERMINAL_KIND=CLOSED_FALSE_POSITIVE
EPISODE_TERMINAL=FALSE_POSITIVE
EPISODE_TERMINAL_MAPPED=REJECTED
CLASSIFICATION=FALSE_POSITIVE
CHOSEN_ROUTE=ROUTE_C
CLOSURE_STATUS=CLOSED_FALSE_POSITIVE
CASE_STATUS=OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON=partial_residual
RESIDUAL_INTAKE_ITEMS=4, 5, 6
LEARNING_STATUS=COMPLETE
LEARNING_VERDICT=LOCAL_CASE_NOTE_ONLY
PROMOTION_DECISION=RESOLVED_NO_PROMOTE
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT
MISSION_COMPLETE=no
OPEN_SAME_INVARIANT_CANDIDATES=NONE
HARD_BLOCK_READY=PASS

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not reopen ROOT-001 (closed_fixed)
- do not reopen FINDING-002 (closed_fixed)
- do not reopen HC-001 (closed_fixed / INTEGRATED)
- do not create FINDING-004..006 from residual intake items 4-6 in this hop
- do not rewrite results/FANIN.md
- do not git commit / push / deploy
