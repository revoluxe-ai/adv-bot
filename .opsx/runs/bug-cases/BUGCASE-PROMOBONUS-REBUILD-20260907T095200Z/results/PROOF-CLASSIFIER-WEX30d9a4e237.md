# PROOF-CLASSIFIER-WEX30d9a4e237

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/30d9a4e237
ORCHESTRATION_ID: ORCH/sup-promo-t11-d11
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-006
COMPLETED_AT: 2026-09-07T20:42:00Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-006/2026-09-07T20:30:22Z

## Classification

CLASSIFICATION: FALSE_POSITIVE
CHOSEN_ROUTE: ROUTE_C
EXPECTED_NEXT_COMMAND: CLOSED_NO_IMPLEMENTATION
EXPECTED_EXECUTION_ROUTE: CLOSED_NO_IMPLEMENTATION
ACTUAL_NEXT_COMMAND: NOT_APPLICABLE
ACTUAL_EXECUTION_ROUTE: NOT_APPLICABLE
NEXT_COMMAND_RECONCILIATION: NOT_APPLICABLE
ROUTE_RECONCILIATION: NOT_APPLICABLE
CURRENT_ROUTE_STATE: CLOSED_NO_IMPLEMENTATION
OPENSPEC_UPDATE_REQUIRED: no

## Actions

- Read input packet PKT/WEX/CLASSIFIER/30d9a4e237/IN
- Read findings/FINDING-006.md, intakes/INTAKE-001.md item 6, LEDGER.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only FINDING-006 (INTAKE-001 MEDIUM item 6). Did not reopen ROOT-001, FINDING-002, HC-001, FINDING-003, FINDING-004, HC-FINDING-004-STALE-TEST, FINDING-005. Did not create FINDING-007.
- Compared WBAutoBudgetTopUp journal contract to load_success_tranches / campaign remaining SoT and bot write path
- Did not claim; did not write RED/tests; did not fix production; did not edit OpenSpec; did not commit
- Appended one results/ROUTE-TRACE.jsonl event via runtime/route_trace.py (EVENT_TYPE=classification_route_selection; SEQUENCE=97)
- Did not edit findings/FINDING-006.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**, OpenSpec

## Evidence

- Reported site: journal only bot WBAutoBudgetTopUp; manual WB promo deposits invisible
- WBAutoBudgetTopUp model docstring: journal of campaign budget top-ups by the bot (auto-budget). That is the table invariant, not a complete WB finance ledger
- Write path: AutoBudgetManager.service _create_topup_entry then wb_modifier.top_up_budget. No allowed-input write path journals seller-portal / manual deposits into WBAutoBudgetTopUp
- promo_accounting module: campaign remaining = FEFO on verified WBAutoBudgetTopUp allocation minus WBCampaignPromoSpend
- promo_ledger.load_success_tranches: only WBAutoBudgetTopUp status=success and promo_amount > 0. load_campaign_ledgers uses that verified set
- RedisPromoStateManager: derived cache; SoT is live WB + PG journals. Unused wallet promo remains visible via live WB cashbacks[] / pool_usable, not via the bot journal
- openspec/decisions/index.md has no promo-journal / manual-deposit SoT decision. Not SPEC_GAP: the rebuild already states verified bot allocation as campaign-remaining SoT
- Materializer EXPECTED_BEHAVIOR_CANDIDATE (journal should also record manual deposits) is a candidate only; it contradicts the rebuild journal contract
- Not ROOT-001 overlay, FINDING-002/HC-001 pool-failure, FINDING-003 leftover lookback, FINDING-004 FEFO, or FINDING-005 leftover fraction

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/Python/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: Write->path; encoding=utf-8; route-trace append via .cursor/pipeline/bug-team/runtime/route_trace.py after Write of a staging JSON file (ensure_ascii=True on the staging object); ASCII -> in machine string fields

## Outcome

STATUS: PASS
CLASSIFICATION: FALSE_POSITIVE
NEXT_ACTION: CLOSED_NO_IMPLEMENTATION
MISSION_COMPLETE: no
FINDING_TERMINAL: yes
FINDING_TERMINAL_KIND: CLOSED_FALSE_POSITIVE
