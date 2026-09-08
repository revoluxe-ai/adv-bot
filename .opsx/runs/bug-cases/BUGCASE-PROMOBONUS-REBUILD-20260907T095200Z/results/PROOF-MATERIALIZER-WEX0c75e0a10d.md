# PROOF-MATERIALIZER-WEX0c75e0a10d

WORKER_ID: MATERIALIZER
WORKER_EXECUTION_ID: WEX/MATERIALIZER/0c75e0a10d
ORCHESTRATION_ID: ORCH/sup-promo-t08-d08
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
COMPLETED_AT: 2026-09-07T16:27:44Z
MAPS_TO: /opsx-materialize-bug-queue mode=update
INVOCATION_MODE: CASE_RESUME

## Actions

- Read input packet PKT/WEX/MATERIALIZER/0c75e0a10d/IN
- Did not create a new CASE_ID; did not treat supervisor/mission text as a new RAW_REPORT
- Preserved intakes/INTAKE-001.md RAW_REPORT verbatim; RAW_INTAKE_HASH 637477c63f7498ef1f0f6201bd2408e6548154bac9cc32b85336c40032261794 copied from input
- Sequential max_active_findings=1: materialized only HIGH item 4 as FINDING-004
- Did not reopen ROOT-001 (closed_fixed); did not edit findings/ROOT-001.md
- Did not reopen FINDING-002 (closed_fixed); did not edit findings/FINDING-002.md
- Did not reopen HC-001 (closed_fixed / INTEGRATED); did not edit findings/HC-001.md
- Did not reopen FINDING-003 (closed_false_positive); did not edit findings/FINDING-003.md
- Residual intake items 5, 6 noted on INTAKE-001; FINDING-005 and FINDING-006 not created
- Duplicate search under .opsx/runs/bug-cases (bounded findings TITLE peek) -> EXISTING_CASE_LINKED (resume of this case); sibling HIGH6 FINDING-H6 FEFO pick_cashback is backlog/different_invariant on another CASE_ID, not an open same-root duplicate of item 4; closed findings on this or sibling cases not treated as open duplicates; no DUPLICATE_ROOT_REJECTED
- Wrote findings/FINDING-004.md; updated CASE.md, LEDGER.md, intakes/INTAKE-001.md
- PRODUCTION_CLASSIFICATION left unclear; CLASSIFIER owns IMPLEMENTATION_BUG / SPEC_BUG; CLASSIFICATION / CHOSEN_ROUTE / EPISODE_TERMINAL not set
- CHAT_REQUIRED=true, STATUS=available, CLAIM_PRIORITY=3; CLAIM_TOKEN / OWNER_CHAT empty (not claimed)
- CASE remains OPEN_RESIDUAL_INTAKE; LEAVE_OPEN_REASON=partial_residual
- Did not classify; did not claim; did not write RED/tests; did not fix production; did not append results/ROUTE-TRACE.jsonl; did not write INDEX.md, family/**, app/**, tests/**, OpenSpec/**

## Duplicate search (bounded TITLE peek)

DUPLICATE_SEARCH_ROOT: .opsx/runs/bug-cases
ITEM_4_TITLE: promo_accounting.py FEFO applies spend to expired tranches first, inflating live remaining
THIS_CASE_CLOSED: ROOT-001, FINDING-002, HC-001, FINDING-003 (titles do not match item 4 as open)
SIBLING_HIGH6_FINDING-H6: TITLE "H6 pick_cashback_for_topup prefers expired package over live FEFO"; STATUS=backlog; RELATION_TO_ROOT=different_invariant; different CASE_ID; not open same-root of item 4
OTHER_PEEKS: FINDING-H2/H3/H4/H5, HIGH6 ROOT-001, H2-FDENOM ROOT-001, BUFFEREDINPUTFILE, CAH-* : no open same-root match
DUPLICATE_OUTCOME: EXISTING_CASE_LINKED

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/packet writes (opsx-execution-preflight.md HEREDOC-SHELL-PAYLOAD-001)
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: complied (Write->path; encoding=utf-8; ensure_ascii=True for agent-authored JSON; ASCII -> not Unicode arrow in new JSON fields)
- git status/branch skipped (not required for materialize; opsx-execution-preflight command-class A)

## Outcome

STATUS: PASS
DUPLICATE_OUTCOME: EXISTING_CASE_LINKED
INTAKE_ID: INTAKE-001
FINDING_ID: FINDING-004
CREATE_ROOT_FINDING: false
INTAKE_SUFFICIENCY: SUFFICIENT_FOR_CLASSIFICATION
NEXT_ACTION: /opsx-claim-next-bug case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z chat_label="SUP-PROMO-FIX-20260907"
