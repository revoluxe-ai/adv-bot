# PROOF-CLASSIFIER-WEX74b4e60c9d

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/74b4e60c9d
ORCHESTRATION_ID: ORCH/sup-promo-t10-d10
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-005
COMPLETED_AT: 2026-09-07T19:30:00Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/2026-09-07T19:14:25Z

## Classification

CLASSIFICATION: IMPLEMENTATION_BUG
CHOSEN_ROUTE: ROUTE_A
EXPECTED_NEXT_COMMAND: /opsx-fix-bug
EXPECTED_EXECUTION_ROUTE: /opsx-fix-bug
ACTUAL_NEXT_COMMAND: PENDING
ACTUAL_EXECUTION_ROUTE: PENDING
NEXT_COMMAND_RECONCILIATION: PENDING
ROUTE_RECONCILIATION: PENDING
CURRENT_ROUTE_STATE: AWAITING_FIX_BUG
OPENSPEC_UPDATE_REQUIRED: no

## Actions

- Read input packet PKT/WEX/CLASSIFIER/74b4e60c9d/IN
- Read findings/FINDING-005.md, intakes/INTAKE-001.md item 5, LEDGER.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only FINDING-005 (INTAKE-001 MEDIUM item 5). Residual item 6 not started. ROOT-001 / FINDING-002 / HC-001 / FINDING-003 / FINDING-004 / HC-FINDING-004-STALE-TEST not reopened.
- Compared campaign leftover fraction in campaign_ledger_from_rows / apply_spend_fefo reference_budget vs pool mix (promo_fraction_from_amounts 200/1000 and pool_usable_from_pick topup_amount)
- Did not claim; did not materialize FINDING-006; did not write RED/tests; did not fix; did not commit
- Appended one results/ROUTE-TRACE.jsonl event via runtime/route_trace.py (EVENT_TYPE=classification_route_selection; SEQUENCE=83)
- Did not edit findings/FINDING-005.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**, OpenSpec

## Evidence

- Reported site: campaign leftover fraction uses budget_after/total so M collapses
- campaign_ledger_from_rows sets budget = campaign_budget_total if provided else apply_spend_fefo reference_budget. reference_budget is overwritten to int(budget_after) for each leftover row that has budget_after, else tranche.amount. fraction = promo_fraction_from_amounts(promo_amount=remaining, total_amount=budget)
- Same-module pool contract: pool_usable_from_pick uses cashback_sum / topup_amount. promo_fraction_from_amounts documents 200/1000 -> 0.2. promo_multiplier is M = 1/(1-f), so a collapsed f drives M toward 1
- Collapse: leftover remaining 200 over top-up unit amount 1000 is f=0.2 / M=1.25. The same leftover over budget_after 12000 is f=0.0167 / M~1.017. campaign_budget_total as current campaign wallet is the same wrong total class
- Existing test_campaign_ledger_fraction_uses_remaining_not_ceiling asserts remaining/1000=0.2 with campaign_budget_total=amount=budget_after=1000. It does not distinguish top-up unit from budget_after/wallet and is not a counterproof
- Production path: load_campaign_ledgers -> campaign_ledger_from_rows. Observable boundary: campaign_fraction into resolve_promo_availability then overlay M. No WB production mutation asserted
- openspec/decisions/index.md has no leftover-fraction / budget_after decision. Not SPEC_GAP: the rebuild already states the mix formula on the pool path and in promo_fraction_from_amounts
- CASE.md notes sibling H2 (budget_after/wallet vs top-up unit) on a different CASE_ID / different_invariant. This hop classifies only this case item 5 and does not reopen or route to that sibling
- Not item 6 (manual deposits)

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: Write->path; encoding=utf-8; route-trace append via .cursor/pipeline/bug-team/runtime/route_trace.py after Write of a staging JSON file (ensure_ascii=True on the staging object)

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
NEXT_ACTION: /opsx-fix-bug case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z intake=INTAKE-001 finding=FINDING-005 claim_token=CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-005/2026-09-07T19:14:25Z
MISSION_COMPLETE: no
FINDING_TERMINAL: no
