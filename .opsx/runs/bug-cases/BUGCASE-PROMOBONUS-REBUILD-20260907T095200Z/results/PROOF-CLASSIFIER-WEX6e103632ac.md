# PROOF-CLASSIFIER-WEX6e103632ac

WORKER_ID: CLASSIFIER
WORKER_EXECUTION_ID: WEX/CLASSIFIER/6e103632ac
ORCHESTRATION_ID: ORCH/sup-promo-t06-d06
CASE_ID: BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z
FINDING_ID: HC-001
PARENT_FINDING_ID: FINDING-002
RELATION: SAME_INVARIANT_FINDING
COMPLETED_AT: 2026-09-07T13:54:30Z
MAPS_TO: /opsx-classify-bug
OWNER_CHAT: SUP-PROMO-FIX-20260907
CLAIM_TOKEN: none (max_active_findings=1; FINDING-002 remains claimed GREEN_CONFIRMED)

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

## Actions

- Read input packet PKT/WEX/CLASSIFIER/6e103632ac/IN
- Read findings/HC-001.md (canonical), LEDGER.md, GREEN-FINDING-002.md, RED-FINDING-002.md, family/INVARIANT.md
- Classified only HC-001 (FINDING-002 family branch). Did not reclassify FINDING-002. Did not reopen ROOT-001. Residual intake items 3-6 not started. FINDING-003..006 not allocated.
- Verified in current worktree: PromoStateService.refresh sets pool_fetch_ok=True on non-raising None from get_campaign_balance, then RedisPromoStateManager.set pool_usable=false
- Frozen RED/GREEN node covers only side_effect=RuntimeError; Exception skip is GREEN_CONFIRMED; None path still writes
- Did not claim HC-001 (no dedicated token; FINDING-002 holds the single active claim). Did not write RED/tests/fix. Did not edit findings/**, family/**, CASE.md, INDEX.md, app/**, tests/**
- Appended ROUTE-TRACE.jsonl events 29 (classify-bug) and 30 (classification_route_selection)
- Updated LEDGER.md ## ROUTE_STATE only

## Evidence (verified, not rubber-stamped)

- `promo_state_service.py:143-147`: `pool_fetch_ok = False` then `pool_response = await get_campaign_balance()` then `pool_fetch_ok = True` with no truthiness check. Non-raising `None` is treated as a successful fetch.
- `promo_state_service.py:148-153` / `176-182`: Exception leaves `pool_fetch_ok=False` and returns without Redis set (FINDING-002 GREEN). `None` does not enter this gate.
- `finance/adapter.py:68-81`: `FinanceAdapter.get_campaign_balance` logs unexpected parsed type and `return None` (no raise). Production-reachable fetch failure distinct from Exception.
- `promo_accounting.py:252-265`: `resolve_promo_availability(pool_response=None)` never picks cashback; `pool_usable_from_pick(None)` yields `pool_usable=false` (known-empty, not unknown).
- `redis_promo_state_manager.py:115-116`: `set` always stamps `updated_at=now`, so `CachedShopPromoState.is_stale` is false inside the freshness window.
- Overlay contract: `CachedShopPromoState` docstring "Stale -> conservative M=1"; `fraction_from_cached_state` stale/miss -> Decimal("0"). Fresh false-empty snapshot bypasses miss/stale and is forbidden on fetch failure (PLAIN_LANGUAGE_INVARIANT).
- Frozen test `test_refresh_does_not_set_fresh_false_empty_pool_when_balance_fetch_fails` uses `AsyncMock(side_effect=RuntimeError(...))` only. GREEN-FINDING-002 confirms Exception skip. Does not cover None return.
- Runtime entrypoint: shop-runner `auto_budget_watchdog` -> `AutoBudgetService.refresh_promo_state` -> `PromoStateService.refresh`. Outer catch in `service.py:624-635` only preserves prior/M=1 when the whole refresh raises; inner None path is a successful lying write.
- OpenSpec `openspec/decisions/index.md`: no promo pool-failure / false-empty overlay decision. Not SPEC_GAP: rebuild overlay/cache API already encodes miss/stale -> M=1. Same invariant as FINDING-002; missed failure-mode wiring.

## Why not other labels

- SPEC_BUG: overlay contract is correct; code violates it on None.
- SPEC_GAP: product invariant already stated in overlay/cache API and family PLAIN_LANGUAGE_INVARIANT ("on get_campaign_balance failure").
- FALSE_POSITIVE: current worktree still writes Redis on None; frozen RED does not cover this path.
- OUT_OF_SCOPE: HUNT_SCOPE explicitly includes None return without Exception; same writer and `shop-promo-state` key. Not ROOT-001 Telegram overlay. Not intake 3-6.
- INSUFFICIENT_EVIDENCE: in-repo, deterministic, same function and key.

## Claim note

No dedicated CLAIM_TOKEN for HC-001. `CHAT_REQUIRED=true` but `max_active_findings=1` and FINDING-002 remains claimed GREEN_CONFIRMED. Classify does not block solely for missing HC-001 claim. Next hop is `/opsx-test` RED (no GO, no invented claim_token).

## Write safety

- Shell payload I/O (anti-heredoc): no bash heredoc for JSON/packet writes
- Artifacts via Cursor Write tool (utf-8) plus route_trace helper append
- Windows Shell JSON/JSONL write safety: complied (Write->path; route_trace.append_event)

## Outcome

STATUS: PASS
CLASSIFICATION: IMPLEMENTATION_BUG
NEXT_ACTION: /opsx-test case=BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z finding=HC-001
MISSION_COMPLETE: no
FINDING_TERMINAL: no
