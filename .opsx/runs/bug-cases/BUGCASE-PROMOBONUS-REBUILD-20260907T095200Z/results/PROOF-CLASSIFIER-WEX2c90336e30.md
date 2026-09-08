# PROOF-CLASSIFIER-WEX2c90336e30

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/2c90336e30
ORCHESTRATION_ID: ORCH/sup-promo-t09-d09
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-FINDING-004-STALE-TEST
PARENT_FINDING_ID: FINDING-004
RELATION: SAME_INVARIANT_FINDING
BRANCH_ID: BR/HC-FINDING-004-STALE-TEST/b4dedb0c
COMPLETED_AT: 2026-09-07T18:10:45Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: none (max_active_findings=1; FINDING-004 remains claimed GREEN_CONFIRMED)

## Classification

CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
EXPECTED_NEXT_COMMAND: /opsx-test
EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
ACTUAL_NEXT_COMMAND: PENDING
ACTUAL_EXECUTION_ROUTE: PENDING
NEXT_COMMAND_RECONCILIATION: PENDING
ROUTE_RECONCILIATION: PENDING
CURRENT_ROUTE_STATE: AWAITING_RED
OPENSPEC_UPDATE_REQUIRED: no
MISSION_COMPLETE: no
FINDING_TERMINAL: no
GO_TOKEN: FORBIDDEN

## Actions

- Read input packet PKT/WEX/CLASSIFIER/2c90336e30/IN
- Read findings/HC-FINDING-004-STALE-TEST.md (canonical), findings/FINDING-004.md, family/INVARIANT.md, family/FAMILY.json, family/BRANCHES.jsonl
- Read results/GREEN-FINDING-004.md, results/RED-FINDING-004.md, results/PROOF-HUNT-BOUNDED-HUNTER-FINDING-004.md
- Classified only HC-FINDING-004-STALE-TEST. Did not reclassify FINDING-004. Did not reopen ROOT-001 / FINDING-002 / HC-001 / FINDING-003. Residual intake items 5-6 not started.
- Verified in current worktree: apply_spend_fefo skips is_expired at promo_accounting.py:188-189; remaining filter skips expired at 199-203. Production spend loop already GREEN_CONFIRMED remaining==150.
- Sibling test_fefo_spend_and_expired_tranche_unusable line 67 still asserts remaining==200 on the same expired 300 + live 200 + spend 50 fixture.
- GREEN-FINDING-004 adjacent file run: sibling FAILED assert 150==200 at line 67. Frozen FINDING-004 node PASSED. TEST_CONTENT_SHA256 cd926666fd7fcd2f958440220a58e1a6ff621fb8b839b518133ee0084ffc67b2 MATCH.
- Did not claim this branch (no dedicated token; FINDING-004 holds the single active claim). Did not write RED/tests/fix. Did not edit findings/**, family/**, CASE.md, INDEX.md, app/**, tests/**
- Appended ONE ROUTE-TRACE.jsonl event 68 (classify-bug with route-selection fields; worker bound ONE event)
- Updated LEDGER.md ## ROUTE_STATE only

## Evidence (verified, not rubber-stamped)

- Family PLAIN_LANGUAGE_INVARIANT: apply_spend_fefo must not apply spend to expired leftover before live leftover; expired 300 + live 200 + spend 50 must yield remaining 150. FORBIDDEN_BEHAVIOR is remaining inflated to 200.
- tests/unit/wb/utils/test_promo_accounting.py:40-68 builds that exact fixture and asserts remaining==200 at line 67.
- Frozen GREEN node test_fefo_spend_hits_live_leftover_not_expired (lines 71-105) uses the same inputs and asserts remaining==150.
- app/shared/domains/wb/utils/promo_accounting.py apply_spend_fefo: spend loop `if is_expired(...): continue` (188-189); remaining sum also skips expired (199-203). Docstring already states spend applies only to non-expired leftover.
- campaign_ledger_from_rows / load_campaign_ledgers only call the fixed helper. Not a second production spend loop.
- results/GREEN-FINDING-004.md: adjacent pytest of the file failed 1 (sibling 150==200); frozen node PASS; STATUS GREEN_CONFIRMED.
- results/RED-FINDING-004.md already recorded the sibling as bug-encoding and did not reuse it as the passing expectation.
- openspec/decisions/index.md: no FEFO / apply_spend_fefo / expired-leftover decision. Not SPEC_GAP: FINDING-004 GREEN and family invariant already require remaining==150. Residual is the stale assertion, not a missing product contract.

## Why not other labels

- SPEC_BUG: the required remaining==150 contract is correct; the sibling test still encodes the pre-fix inflation.
- SPEC_GAP: OpenSpec is silent, but the observable contract is already GREEN in production and stated in family INVARIANT. Updating OpenSpec would not be required before fixing the stale test.
- FALSE_POSITIVE: adjacent fail is real (150==200). The assertion still encodes FORBIDDEN remaining==200 and BLOCKS_FAMILY_CLOSURE.
- OUT_OF_SCOPE: SAME_INVARIANT_FINDING; same writer apply_spend_fefo; same fixture; named in INVARIANT KNOWN_READERS / HUNT_SCOPE.
- INSUFFICIENT_EVIDENCE: in-repo, deterministic, frozen SHA MATCH, adjacent fail recorded.

## Claim note

No dedicated CLAIM_TOKEN for HC-FINDING-004-STALE-TEST. CHAT_REQUIRED=true but max_active_findings=1 and FINDING-004 remains claimed GREEN_CONFIRMED. Classify does not block solely for missing HC claim (mirror WEX/CLASSIFIER/6e103632ac). Next hop is /opsx-test RED (no GO, no invented claim_token).

## Allowed fix (later executor; not this hop)

ALLOWED_FIX_FILES: tests/unit/wb/utils/test_promo_accounting.py
FORBIDDEN: FINDING-004 production promo_accounting.py; intake items 5-6; closed ROOT-001 / FINDING-002 / HC-001 / FINDING-003

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc for JSON/packet writes
- Artifacts via Cursor Write tool (utf-8) plus route_trace helper append
- Windows Shell JSON/JSONL write safety: complied (Write->path; route_trace.append_event)
- Machine string fields use ASCII -> not unicode arrow

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=HC-FINDING-004-STALE-TEST
MISSION_COMPLETE: no
FINDING_TERMINAL: no
