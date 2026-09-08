FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: ROOT-001
SOURCE_INTAKE_ID: INTAKE-001
PARENT_FINDING_ID:
TITLE: Telegram rec-bid uses get_effective_promo_plan without promo_fraction/ComplexAdv
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
RELATION_TO_ROOT: root
STATUS: closed_fixed
CHAT_REQUIRED: true
CLAIM_PRIORITY: 3
PACKET_PATH: findings/ROOT-001.md
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/2026-09-07T10:12:02Z
CLAIMED_AT: 2026-09-07T10:12:02Z
COMPLETED_AT: 2026-09-07T11:52:00Z
PACKET_PURPOSE: adjudication
INVARIANT: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/PROMO-OVERLAY-REC-BID
ORIGINAL_FINDING: auto_shelf_bid_control_view_provider.py:881 — Telegram rec-bid uses get_effective_promo_plan(adv) without promo_fraction/ComplexAdv
EVIDENCE: INTAKE-001 HIGH item 1; RED-ROOT-001.md; FIX-ROOT-001.md; GREEN-ROOT-001.md GREEN_CONFIRMED; hunt CLEAR; FAMILY-FANIN.md READY_FOR_FAMILY_CLOSURE; LEARNING_DECISION COMPLETE EXISTING_POLICY_COMPLIANCE_FAILURE RESOLVED_NO_PROMOTE.
RUNTIME_PATH: app/modules/shop_runner/service_manager/services/auto_shelf_bid_control_manager/auto_shelf_bid_control_view_provider.py
CAUSAL_BOUNDARY: Telegram rec-bid view path calling get_effective_promo_plan without fraction=/complex_adv=; live promo_fraction in Redis overlay. Fixed by passing fraction=live_fraction.
WRITE_BOUNDARY: Candidate read/compute of effective promo plan for Telegram rec-bid presentation; no production write asserted.
SOURCE_SNAPSHOT: intakes/INTAKE-001.md item 1; team/packets/WEX_MATERIALIZER_1090d9ac64.in.json
DISPOSITION: CLOSED_FIXED_VERIFIED
CREATED_AT: 2026-09-07T10:04:52Z
LAST_ACTIVITY_AT: 2026-09-07T11:52:00Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-ROOT-001.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-ROOT-001.md
GREEN_EVIDENCE_PATH: results/GREEN-ROOT-001.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-ROOT-001.md
TEST_ID: tests/unit/test_auto_shelf_bid_control_view_provider.py::test_build_view_rec_bid_plan_context_uses_promo_overlay_when_fraction_positive
TEST_CONTENT_SHA256: 7b8cf8861d66e61c8eb46e1a75c283684b44dbcda54f82530654ef3b3c848aae
FANIN_PATH: results/FAMILY-FANIN.md
HUMAN_SUMMARY_PATH: results/HUMAN_SUMMARY.md
CLOSURE_EVIDENCE_PATH: results/OWNER-CLOSURE-ROOT-001.md
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

NEXT_COMMAND (finding closed_fixed; CASE residual_intake items 2-6):
/opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

MODE: READ_ONLY

## Terminal closure

FINDING_STATUS=closed_fixed
EPISODE_TERMINAL=FIXED
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
CLOSURE_STATUS=CLOSED_FIXED_VERIFIED
CASE_STATUS=OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON=partial_residual
RESIDUAL_INTAKE_ITEMS=2, 3, 4, 5, 6
LEARNING_STATUS=COMPLETE
WORKTREE_STATUS=UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW
COMMIT_CREATED=NO
USER_ACTION_REQUIRED=REVIEW_DIFF_AND_DECIDE_COMMIT
MISSION_COMPLETE=no

FORBIDDEN:
- do not edit production files
- do not use GO
- do not claim a second finding
- do not open other chats
- do not promote without /opsx-materialize-bug-queue mode=promote
- do not emit bare /opsx-fix-bug without case=/finding=/claim_token=
- do not classify (CLASSIFIER owns PRODUCTION_CLASSIFICATION beyond unclear)
- do not create FINDING-002..006 from residual intake items 2-6 in this hop
