FINDING_PACKET

CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-FINDING-004-STALE-TEST
SOURCE_HUNT_ID: HC-FINDING-004-STALE-TEST
PARENT_FINDING_ID: FINDING-004
TITLE: stale test asserts remaining==200 after expired leftover absorbs spend
STATUS: closed_fixed
BRANCH_STATUS: INTEGRATED
RELATION_TO_INVARIANT: SAME_INVARIANT_FINDING
RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING
BLOCKS_FAMILY_CLOSURE: false
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
BUG_FAMILY_ID: BFAM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED
PRODUCTION_CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
CONFIDENCE: high
AFFECTED_COMPONENT: tests.unit.wb.utils.test_promo_accounting.test_fefo_spend_and_expired_tranche_unusable
LOC_LINK: tests/unit/wb/utils/test_promo_accounting.py:67
PACKET_PATH: findings/HC-FINDING-004-STALE-TEST.md
PACKET_PURPOSE: family-fanout-materialize
CHAT_REQUIRED: true
CLAIM_PRIORITY:
CLAIM_TOKEN:
CLAIMED_AT:
COMPLETED_AT: 2026-09-07T18:54:00Z
CREATED_AT: 2026-09-07T17:36:28Z
LAST_ACTIVITY_AT: 2026-09-07T18:54:00Z
BLOCKER:
RESULT_PATH: results/OWNER-CLOSURE-FINDING-004.md
EPISODE_TERMINAL: FIXED
RED_EVIDENCE_PATH: results/RED-HC-FINDING-004-STALE-TEST.md
GREEN_EVIDENCE_PATH: results/GREEN-HC-FINDING-004-STALE-TEST.md
OWNER_GO_RECEIPT_PATH:
FIX_EVIDENCE_PATH: results/FIX-HC-FINDING-004-STALE-TEST.md
TEST_ID: tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable
TEST_CONTENT_SHA256: 233084e637cfaa1f4c3ac5bea151f5f1cb8a377f6f30b286ac19f2bba9f50c53
FANIN_PATH: results/FANIN.md
HUNT_CANDIDATE: true
HUNT_CANDIDATE_STATUS_WAS: open_candidate
HUNT_CANDIDATE_STATUS_AT_FANIN: materialized
DISPOSITION: closed_fixed
NEXT_WORKER:
NEXT_ACTION: /opsx-bug-team case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z

MODE: READ_ONLY

FIX_ANNOTATION:
FIX_STATUS: APPLIED
FIX_EVIDENCE_PATH: results/FIX-HC-FINDING-004-STALE-TEST.md
ACTUAL_EXECUTION_ROUTE: /opsx-fix-bug
COMMIT_CREATED: NO
MISSION_COMPLETE: no
CHANGED_PATH: tests/unit/wb/utils/test_promo_accounting.py
BEHAVIOR: sibling assertion remaining==200 -> remaining==150 on expired 300 + live 200 + spend 50. Production apply_spend_fefo unchanged this sibling hop.
GREEN_AUTHORITY: GREEN_VERIFIER GREEN_CONFIRMED (results/GREEN-HC-FINDING-004-STALE-TEST.md)
BRANCH_STATUS: INTEGRATED
NOT_FALSE_POSITIVE: true
NOT_OUT_OF_SCOPE: true
NOT_OPEN_CANDIDATE: true

INVARIANT:
PLAIN_LANGUAGE: apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150.
ORIGINAL_FINDING: FINDING-004 production spend loop now skips is_expired. This sibling was the frozen test that still asserted remaining==200 on the same fixture.

EVIDENCE: findings/HC-FINDING-004-STALE-TEST.md; tests/unit/wb/utils/test_promo_accounting.py; results/GREEN-FINDING-004.md adjacent fail assert 150 == 200; results/RED-FINDING-004.md bug-encoding note; results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-004.md; results/GREEN-HC-FINDING-004-STALE-TEST.md.

RUNTIME_PATH: unit test only. Production apply_spend_fefo already skips expired leftover.

CAUSAL_BOUNDARY: Stale assertion remaining==200 encoded the pre-fix inflation. After FINDING-004 skip-expired, apply_spend_fefo returns 150. Not a second production spend loop.

WRITE_BOUNDARY: tests/unit/wb/utils/test_promo_accounting.py assertion only.

SOURCE_SNAPSHOT: findings/HC-FINDING-004-STALE-TEST.md (open_candidate then materialized); team/packets/WEX_BOUNDED_HUNTER_4e8665d743.out.json; results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-004.md

DISPOSITION: closed_fixed SAME_INVARIANT_FINDING of INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/FEFO-SPEND-SKIP-EXPIRED. Family CLOSED_FIXED_VERIFIED. BRANCH_STATUS=INTEGRATED. BLOCKS_FAMILY_CLOSURE=false (terminated). Not open_candidate. Not FALSE_POSITIVE. Not OUT_OF_SCOPE.

RELATION_RATIONALE:
Hunter claimed SAME_INVARIANT_FINDING; that claim is not authority. Independent classification by RELATION_CLASSIFIER:

1. Family PLAIN_LANGUAGE_INVARIANT forbids applying spend to expired leftover before live leftover. Required remaining on expired 300 + live 200 + spend 50 is 150. FORBIDDEN_BEHAVIOR is remaining inflated to 200.
2. tests/unit/wb/utils/test_promo_accounting.py::test_fefo_spend_and_expired_tranche_unusable builds that exact fixture and asserted remaining==200.
3. FINDING-004 frozen GREEN node test_fefo_spend_hits_live_leftover_not_expired uses the same inputs and asserts remaining==150.
4. After INTEGRATED, sibling assertion is remaining==150. Production hash unchanged.
5. Not NEW_ROOT_CAUSE (same invariant / same function / same fixture). Not FALSE_POSITIVE (adjacent fail was real). Not OUT_OF_SCOPE.

## Terminal closure

FINDING_STATUS=closed_fixed
EPISODE_TERMINAL=FIXED
FAMILY_STATUS=CLOSED_FIXED_VERIFIED
CASE_STATUS=OPEN_RESIDUAL_INTAKE
LEAVE_OPEN_REASON=partial_residual
RESIDUAL_INTAKE_ITEMS=5, 6
MISSION_COMPLETE=no
COMMIT_CREATED=NO
OPEN_SAME_INVARIANT_CANDIDATES=NONE
HARD_BLOCK_READY=PASS
BRANCH_STATUS=INTEGRATED
STATUS=closed_fixed (not open_candidate)

FORBIDDEN:
- do not edit production files
- do not reopen ROOT-001
- do not reopen FINDING-002
- do not reopen HC-001
- do not reopen FINDING-003
- do not allocate FINDING-005 / FINDING-006
- do not start intake items 5-6
- do not rewrite results/FANIN.md
- do not git commit / push / deploy
- do not overwrite family/closed/ROOT-001/**
- do not overwrite family/closed/FINDING-002/**
