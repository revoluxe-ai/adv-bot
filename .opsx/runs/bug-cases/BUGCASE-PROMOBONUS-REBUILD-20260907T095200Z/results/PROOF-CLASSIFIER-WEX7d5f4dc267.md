# PROOF-CLASSIFIER-WEX7d5f4dc267

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/7d5f4dc267
ORCHESTRATION_ID: ORCH/sup-promo-t05-d05
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: FINDING-002
COMPLETED_AT: 2026-09-07T12:23:19Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: CLAIM/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/2026-09-07T12:15:07Z

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

- Read input packet PKT/WEX/CLASSIFIER/7d5f4dc267/IN
- Read findings/FINDING-002.md, intakes/INTAKE-001.md, LEDGER.md (read-only except LEDGER ## ROUTE_STATE)
- Classified only FINDING-002 (INTAKE-001 HIGH item 2). Residual items 3-6 not started. ROOT-001 not reopened.
- Compared PromoStateService.refresh get_campaign_balance failure path to Redis freshness / overlay stale->M=1 contract
- Did not claim; did not materialize FINDING-003..006; did not write RED/tests; did not fix; did not commit
- Did not append results/ROUTE-TRACE.jsonl (same as prior CLASSIFIER hop WEX1117063723; orchestrator finalize owns WORKER_COMPLETED)
- Did not edit findings/FINDING-002.md, CASE.md, intakes/**, INDEX.md, handoffs/**, app/**, tests/**, team/CHECKPOINT.json, team/intents/**

## Evidence

- Reported site: `promo_state_service.py:127-201` — `get_campaign_balance` except keeps `pool_response=None`, then always `RedisPromoStateManager.set` with `pool_usable=shop_pool_usable` defaulting False
- Inner catch: lines 128-135 swallow WB failure; refresh continues as success. Outer `AutoBudgetService.refresh_promo_state` only preserves prior/conservative M=1 when the whole refresh raises
- `resolve_promo_availability(pool_response=None)` treats missing response as no cashback -> `pool_usable=false` (known empty), not unknown
- `RedisPromoStateManager.set` writes `updated_at=now`, so `CachedShopPromoState.is_stale` is false for `_STALE_AFTER` (15 min)
- Overlay contract: `fraction_from_cached_state` / `CachedShopPromoState` docstring: stale/miss -> Decimal("0") (conservative M=1). Fresh `pool_usable=false` is a false empty-pool snapshot, not that miss/stale path
- Runtime entrypoint: shop-runner `auto_budget_watchdog` -> `AutoBudgetService.refresh_promo_state` -> `PromoStateService.refresh`. Next tick `_build_pre_complex_adv` reads Redis via `fraction_from_cached_state`
- Observable boundary: Redis derived overlay cache write. No WB production mutation. Not Telegram rec-bid (ROOT-001)
- OpenSpec: no promo pool-failure / stale overlay contract in `openspec/specs` or `openspec/decisions/index.md`. Not SPEC_GAP: rebuild already encodes stale/miss -> M=1; this is a missed failure-path write, not a missing product decision

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc used for JSON/packet writes
- Artifacts written via Cursor Write tool (utf-8 path writes)
- Windows Shell JSON/JSONL write safety: complied (Write->path; encoding=utf-8)

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=FINDING-002
MISSION_COMPLETE: no
FINDING_TERMINAL: no
