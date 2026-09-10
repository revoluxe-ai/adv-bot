# PROOF-CLASSIFIER-WEX1117063723

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/1117063723
ORCHESTRATION_ID: ORCH/sup-promo-t04-d04
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: ROOT-001
COMPLETED_AT: 2026-09-07T10:24:30Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/ROOT-001/2026-09-07T10:12:02Z

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

- Read input packet PKT/WEX/CLASSIFIER/1117063723/IN
- Read findings/ROOT-001.md, intakes/INTAKE-001.md, LEDGER.md, CASE.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only ROOT-001 (INTAKE-001 HIGH item 1). Residual items 2-6 not started.
- Compared Telegram rec-bid call site to PlanFactProvider overlay contract and sibling snapshot path
- Did not claim; did not materialize FINDING-002..006; did not write RED/tests; did not fix; did not commit
- Did not append results/ROUTE-TRACE.jsonl (orchestrator finalize owns WORKER_COMPLETED)
- Did not edit findings/ROOT-001.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**

## Evidence

- Reported site: `auto_shelf_bid_control_view_provider.py:881` — `PlanFactProvider.get_effective_promo_plan(adv)` with AdvSetting only
- Provider contract: `PlanFactProvider.get_effective_promo_plan` / `get_effective_plan_data` resolve live f from `complex_adv.promo_fraction` or `fraction=`; else `adv.promo_fraction`; missing -> Decimal("0") -> same Plan as `get_plan_data`
- Canonical helper: `promo_overlay.overlay_for_adv(adv, fraction=fraction)` always passes fraction
- Sibling reachable path: `auto_shelf_bid_control_decision_snapshot_builder.py:110-112` already passes `complex_adv=complex_adv`
- Telegram entrypoint: `auto_shelf_bid_control_telegram_service.build_view` -> `AutoShelfBidControlViewProvider.build_view`
- Observable boundary: Telegram rec-bid presentation (target/max pay in plan_context). No WB/DB write asserted
- OpenSpec: no promo overlay / rec-bid contract in `openspec/specs` or active `openspec/changes`; accepted decisions index has no promo invariant. Not SPEC_GAP: rebuild already encodes the overlay API; this is a missed call site, not a missing product decision

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: complied (Write->path; encoding=utf-8)

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=ROOT-001
MISSION_COMPLETE: no
FINDING_TERMINAL: no
