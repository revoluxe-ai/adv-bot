# PROOF-CLASSIFIER-WEX2d43d59752

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/2d43d59752
ORCHESTRATION_ID: ORCH/sup-promo-t08-d08
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-004
COMPLETED_AT: 2026-09-07T16:56:00Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-004/2026-09-07T16:37:42Z

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

## Actions

- Read input packet PKT/WEX/CLASSIFIER/2d43d59752/IN
- Read findings/FINDING-004.md, intakes/INTAKE-001.md, LEDGER.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only FINDING-004 (INTAKE-001 HIGH item 4). Residual items 5-6 not started. ROOT-001 / FINDING-002 / HC-001 / FINDING-003 not reopened.
- Cited path app/modules/auto_budget_manager/promo_accounting.py is missing; bounded fallback resolved app/shared/domains/wb/utils/promo_accounting.py
- Compared apply_spend_fefo spend loop vs module docstring (FEFO on non-expired leftover)
- Did not claim; did not materialize FINDING-005/FINDING-006; did not write RED/tests; did not fix; did not commit
- Appended one results/ROUTE-TRACE.jsonl event via runtime/route_trace.py (EVENT_TYPE=classification_route_selection; SEQUENCE=57)
- Did not edit findings/FINDING-004.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**, OpenSpec

## Evidence

- Reported site: promo_accounting.py FEFO applies spend to expired tranches first, inflating live remaining
- Module docstring / apply_spend_fefo: spend is applied FEFO to non-expired leftover; expired leftover is not usable even if local leftover is still positive
- Implementation: _tranche_sort_key orders dated tranches by earliest expiry first (already-expired first). The spend loop then takes from leftovers without skipping is_expired. Remaining then skips expired leftover. Spend is therefore absorbed by unusable expired leftover and live remaining is inflated
- Example reconstructed from the existing unit vectors: expired 300 + live 200 + spend 50. Docstring-correct remaining is 150 (spend against live). Current remaining is 200 (spend against expired). Existing test_fefo_spend_and_expired_tranche_unusable asserts remaining==200 and therefore does not catch the inflation
- Production path: PromoStateService.refresh -> load_campaign_ledgers -> campaign_ledger_from_rows -> apply_spend_fefo. Observable boundary: Redis derived overlay (campaign remaining / usable / fraction). Inflated remaining delays AND-stop and overstates overlay fraction. No WB production mutation asserted
- OpenSpec openspec/decisions/index.md has no promo FEFO decision. Not SPEC_GAP: the rebuild module already states the non-expired spend contract
- Not item 5 (leftover fraction budget_after/total) or item 6 (manual deposits)

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: Write->path; encoding=utf-8; route-trace append via .cursor/pipeline/bug-team/runtime/route_trace.py after Write of a staging JSON file (ensure_ascii=True on the staging object)

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=FINDING-004
MISSION_COMPLETE: no
FINDING_TERMINAL: no
