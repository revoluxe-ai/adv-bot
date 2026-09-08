# PROOF-MATERIALIZER-WEX187e482f7f

WORKER_ID: MATERIALIZER
WORKER_EXECUTION_ID: WEX/MATERIALIZER/187e482f7f
ORCHESTRATION_ID: ORCH/sup-promo-t10-d10
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
COMPLETED_AT: 2026-09-07T19:08:00Z
MAPS_TO: /opsx-materialize-bug-queue mode=update
INVOCATION_MODE: CASE_RESUME

## Actions

- Read input packet PKT/WEX/MATERIALIZER/187e482f7f/IN
- Did not create a new CASE_ID; did not treat supervisor/mission text as a new RAW_REPORT
- Preserved intakes/INTAKE-001.md RAW_REPORT verbatim; RAW_INTAKE_HASH 637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794 copied from input
- Sequential max_active_findings=1: materialized only MEDIUM item 5 as FINDING-005
- Did not reopen ROOT-001 (closed_fixed); did not edit findings/ROOT-001.md
- Did not reopen FINDING-002 (closed_fixed); did not edit findings/FINDING-002.md
- Did not reopen HC-001 (closed_fixed / INTEGRATED); did not edit findings/HC-001.md
- Did not reopen FINDING-003 (closed_false_positive); did not edit findings/FINDING-003.md
- Did not reopen FINDING-004 (closed_fixed); did not edit findings/FINDING-004.md
- Did not reopen HC-FINDING-004-STALE-TEST (closed_fixed / INTEGRATED); did not edit findings/HC-FINDING-004-STALE-TEST.md
- Residual intake item 6 noted on INTAKE-001; FINDING-006 not created
- Duplicate search under .opsx/runs/bug-cases (bounded findings TITLE peek) -> EXISTING_CASE_LINKED (resume of this case); sibling HIGH6 FINDING-H2 and H2-FDENOM ROOT-001 are different CASE_ID / different_invariant (budget_after/wallet vs top-up unit), not an open same-root duplicate of item 5; closed findings on this or sibling cases not treated as open duplicates; no DUPLICATE_ROOT_REJECTED
- Wrote findings/FINDING-005.md in FINDING-004 available-style; updated CASE.md, LEDGER.md, intakes/INTAKE-001.md
- PRODUCTION_CLASSIFICATION left unclear; CLASSIFIER owns IMPLEMENTATION_BUG / SPEC_BUG; CLASSIFICATION / CHOSEN_ROUTE / EPISODE_TERMINAL not set
- CHAT_REQUIRED=true, STATUS=available, CLAIM_PRIORITY=3; CLAIM_TOKEN / OWNER_CHAT empty (not claimed)
- CASE remains OPEN_RESIDUAL_INTAKE; LEAVE_OPEN_REASON=partial_residual
- Did not classify; did not claim; did not write RED/tests; did not fix production; did not append results/ROUTE-TRACE.jsonl; did not write INDEX.md, family/**, app/**, tests/**, OpenSpec/**

## Duplicate search (bounded TITLE peek)

DUPLICATE_SEARCH_ROOT: .opsx/runs/bug-cases
ITEM_5_TITLE: campaign leftover fraction uses budget_after/total so M collapses
THIS_CASE_CLOSED: ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST (titles do not match item 5 as open)
SIBLING_HIGH6_FINDING-H2: TITLE "H2 campaign f denominator uses budget_after/wallet instead of top-up unit"; STATUS=promoted_to_root_case; RELATION_TO_ROOT=different_invariant; different CASE_ID; not open same-root of item 5
SIBLING_H2_FDENOM_ROOT-001: same H2 TITLE; different CASE_ID; different invariant; not open same-root of item 5
OTHER_PEEKS: FINDING-H3/H4/H5/H6, HIGH6 ROOT-001, BUFFEREDINPUTFILE, CAH-* : no open same-root match
DUPLICATE_OUTCOME: EXISTING_CASE_LINKED

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/packet writes (opsx-execution-preflight.md HEREDOC-SHELL-PAYLOAD-001)
- Artifacts written via Cursor Write tool (utf-8 path writes); output packet via Write-.py then run-by-path with encoding=utf-8 ensure_ascii=True
- Windows Shell JSON/JSONL write safety: complied (Write->path; encoding=utf-8; ensure_ascii=True for agent-authored JSON; ASCII -> not Unicode arrow in new JSON fields)
- git status/branch skipped (not required for materialize; opsx-execution-preflight command-class A)

## Outcome

STATUS: PASS
DUPLICATE_OUTCOME: EXISTING_CASE_LINKED
INTAKE_ID: INTAKE-001
FINDING_ID: FINDING-005
CREATE_ROOT_FINDING: false
INTAKE_SUFFICIENCY: SUFFICIENT_FOR_CLASSIFICATION
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z chat_label="SUP-PROMO-FIX-20260907"
residual_intake_items: [6]
