FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: promo_accounting.py FEFO applies spend to expired leftover first, inflating live remaining
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
RELATION_TO_ROOT: sequential_residual
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 3
PACKET_PATH: findings/FINDING-004.md
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/2026-09-07T16:37:42Z
CLAIMED_AT: 2026-09-07T16:37:42Z
COMPLETED_AT: 2026-09-07T18:54:00Z
PACKET_PURPOSE: adjudication
INVARIANT: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
ORIGINAL_FINDING: promo_accounting.py FEFO applies spend to expired leftover first, inflating live remaining
EVIDENCE: INTAKE-001 HIGH item 4; RAW_INTAKE_HASH 637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794. Sequential residual after ROOT-001 closed_fixed, FINDING-002+HC-001 closed_fixed, FINDING-003 closed_false_positive. Production skip-expired GREEN_CONFIRMED; HC-FINDING-004-STALE-TEST SAME_INVARIANT sibling INTEGRATED then closed_fixed same family.
RUNTIME_PATH: app/shared/domains/wb/utils/promo_accounting.py
CAUSAL_BOUNDARY: apply_spend_fefo spend loop consumed expired leftover before live leftover because the spend iteration had no is_expired skip. Remaining filter already skipped expired leftover.
WRITE_BOUNDARY: apply_spend_fefo spend loop. Fixed: continue when is_expired(item.expires_at, now=now).
SOURCE_SNAPSHOT: intakes/INTAKE-001.md item 4; team/packets/WEX_MATERIALIZER_0c75e0a10d.in.json
DISPOSITION: CLOSED_FIXED_VERIFIED
CREATED_AT: 2026-09-07T16:27:44Z
LAST_ACTIVITY_AT: 2026-09-07T18:54:00Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-FINDING-004.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-FINDING-004.md
GREEN_EVIDENCE_PATH: results/GREEN-FINDING-004.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-FINDING-004.md
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_hits_live_leftover_not_expired
TEST_CONTENT_SHA256: cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2
FANIN_PATH: results/FANIN.md
HUMAN_SUMMARY_PATH: results/HUMAN_SUMMARY.md
CLOSURE_EVIDENCE_PATH: results/OWNER-CLOSURE-FINDING-004.md
CLASSIFICATION: IMPLEMENTATION_BUG
FINDING_TERMINAL_KIND: CLOSED_GREEN
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

NEXT_COMMAND (finding closed_fixed; CASE residual_intake items 5-6):
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

MODE: READ_ONLY

## Terminal closure

FINDING_STATUS=closed_fixed
EPISODE_TERMINAL=FIXED
CLASSIFICATION=IMPLEMENTATION_BUG
CHOSEN_ROUTE=ROUTE_A
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
CLOSURE_STATUS=CLOSED_FIXED_VERIFIED
CASE_STATUS=OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON=partial_residual
RESIDUAL_INTAKE_ITEMS=5, 6
HC_FINDING_004_STALE_TEST_DISPOSITION=closed_fixed
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
- do not reopen HC-001 (closed_fixed)
- do not reopen FINDING-003 (closed_false_positive)
- do not create FINDING-005 or FINDING-006 from residual intake items 5-6 in this hop
- do not rewrite results/FANIN.md
- do not git commit / push / deploy
