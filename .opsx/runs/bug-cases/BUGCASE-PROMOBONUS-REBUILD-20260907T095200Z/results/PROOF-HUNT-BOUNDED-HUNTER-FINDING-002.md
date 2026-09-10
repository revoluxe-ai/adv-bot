# Bounded hunt proof — PROMO-POOL-FAIL-NO-FALSE-EMPTY

```text
WORKER_EXECUTION_ID: WEX/BOUNDED_HUNTER/9b10ba8467
FINDING_ID: FINDING-002
INVARIANT_ID: INV/BUGCASE-PROMOBONUS-REBUILD-20260907T095200Z/FINDING-002/PROMO-POOL-FAIL-NO-FALSE-EMPTY
HUNT_RESULT: CANDIDATES_FOUND
CANDIDATE_COUNT: 1
```

TOPIC_INTENT: PRODUCT_BRIEF
SOURCE_RESOLUTION: DIRECT (input packet, findings/FINDING-002.md, scoped auto_budget_manager + get_campaign_balance writers)
EXECUTION_PREFLIGHT: git status SKIP_IF (not required for hunt decision); Pass 1 rg bounded to app/ get_campaign_balance / RedisPromoStateManager / pool_usable

## Result

HUNT_RESULT: CANDIDATES_FOUND. One same-invariant sibling remains after the FINDING-002 Exception skip.

FINDING-002 Exception path is fixed and was not re-emitted. ROOT-001 was not reopened. Intake items 3-6 were not started.

## Hunt bound

Find only same-invariant sites that on WB campaign-balance/pool fetch failure still persist a fresh derived empty-pool cache (pool_usable=false / equivalent known-empty) instead of miss/stale. Do not hunt ROOT-001 Telegram rec-bid overlay. Do not treat intake items 3-6 as same-invariant unless they literally write a fresh false-empty pool on balance-fetch failure. Do not fix, test, classify, or close candidates.

## KNOWN_ROOT_RESULT (FINDING-002)

```text
ROOT_FINDING_ID: FINDING-002
STATUS: not_reproduced_on_inspected_snapshot
SNAPSHOT: current worktree PromoStateService.refresh (post-fix)
LOC_LINK: app/modules/auto_budget_manager/promo_state_service.py:176
MATCHED_EFFECT: Exception on get_campaign_balance no longer Redis-sets pool_usable=false
MATCHED_CAUSAL_PATH: except Exception -> pool_fetch_ok remains False -> return
MATCHED_WRITE_BOUNDARY: RedisPromoStateManager.set skipped
EVIDENCE: lines 144-182 skip Redis set; GREEN node passed Exception-only RED
ACTION: do not emit FINDING-002 as a candidate
```

## NEW_FINDINGS

### 1. HC-001 [same_invariant_different_path] None return still Redis-sets false-empty pool

```text
FINDING_ID: HC-001
File: app/modules/auto_budget_manager/promo_state_service.py
LOC_LINK: app/modules/auto_budget_manager/promo_state_service.py:147
Function: PromoStateService.refresh
Boundary: RedisPromoStateManager.set shop-promo-state
RELATION_TO_ROOT_CANDIDATE: SAME_INVARIANT_FINDING
CONFIDENCE: high
ADJUDICATION_REQUIRED: true
CHILD_CHAT_RECOMMENDED: true
```

Evidence:

- `pool_fetch_ok = True` is set on any non-raising return, including `None` (line 147).
- `FinanceAdapter.get_campaign_balance` returns `None` on unexpected parsed type (LOC_LINK: `app/core/mp/wb/api/adapter/promotion_client/finance/adapter.py:80`).
- `resolve_promo_availability(pool_response=None)` yields `pool_usable=false` (LOC_LINK: `app/shared/domains/wb/utils/promo_accounting.py:261`).
- `RedisPromoStateManager.set` stamps `updated_at=now` (LOC_LINK: `app/modules/auto_budget_manager/promo_state_service.py:219`).
- Overlay: `fraction_from_cached_state` uses miss/stale -> Decimal(0) conservative M=1; a fresh false-empty snapshot is not stale (LOC_LINK: `app/shared/domains/wb/utils/promo_overlay.py:21`).
- Production entry: `auto_budget_watchdog` -> `refresh_promo_state` (LOC_LINK: `app/modules/shop_runner/service_manager/manager.py:838`).
- Frozen RED only asserts Exception (`side_effect=RuntimeError`); None return is uncovered.

Difference from FINDING-002: Exception gate is now an early return; None is a different causal gate in the same function and write boundary.

## Pass 1 scan (cheap)

`get_campaign_balance` production callers:

| Site | Redis derived pool write on failure? | Classification |
|------|--------------------------------------|----------------|
| `promo_state_service.py` Exception | No (FINDING-002 fix) | duplicate_root / fixed; not a candidate |
| `promo_state_service.py` None return | Yes: RedisPromoStateManager.set pool_usable=false | HC-001 SAME_INVARIANT_FINDING |
| `auto_budget_manager/service.py:340` ensure_budget | No: early BALANCE_NOT_GET; success writes shop-balance-snapshot | out of invariant (different Redis key) |
| `auto_budget_manager/service.py:1058` common-budget ensure | Same as above | out of invariant |
| `auto_adv_active_control_service.py:892` `_cabinet_has_positive_balance` | No Redis shop-promo-state write; exception -> ok_wb=False | out of invariant |

`RedisPromoStateManager.set` production writers: only `PromoStateService.refresh`. Readers: `wb_shop_data_manager._load_cached_promo_state`, `auto_shelf_bid_control_view_provider` (get only).

## Classified out of hunt bound (not candidates)

- ROOT-001 Telegram rec-bid `get_effective_promo_plan` (different closed family).
- Intake 3 `promo_ledger.py` 90-day lookback: no balance-fetch -> Redis false-empty write.
- Intake 4 `promo_accounting.py` FEFO: accounting, not Redis pool snapshot on fetch failure.
- Intake 5 leftover fraction budget_after/total: not this write boundary.
- Intake 6 journal only bot WBAutoBudgetTopUp: not this write boundary.
- Successful WB payload with genuinely empty cashback writing `pool_usable=false`: true empty, not fetch failure.
- Empty `advert_ids` still writing shop `pool_usable=false` after a successful fetch: different invariant; CREATE_SEPARATE_ROOT_CANDIDATE not started.

## HUNT_EFFECTIVENESS

HIGH_WITHIN_DECLARED_SCOPE: enumerated production `get_campaign_balance` callers and the sole `RedisPromoStateManager.set` writer; FINDING-002 Exception skip reconfirmed; one sibling None-return gate remains.

## HUNT_FALSE_NEGATIVE_RISK

BOUNDED_TO_REDIS_DERIVED_POOL: hunt matches fresh `shop-promo-state` `pool_usable=false` writes on balance-fetch failure. True-empty successful WB payloads, `shop-balance-snapshot`, ledger/FEFO/leftover/journal, and Telegram rec-bid overlay were classified out. HTTP paths that raise remain FINDING-002 (fixed, not re-emitted). No Pass-3 deep expansion (`deep` absent).

## FANOUT_INPUT (preview only; FAN_IN not started)

```text
ROOT_FINDING_ID: FINDING-002
INVARIANT: On get_campaign_balance failure, do not redis.set a fresh pool_usable=false snapshot; miss/stale -> conservative M=1.
NEW_FINDING_IDS: HC-001
CHILD_CHAT_CANDIDATES: HC-001
ITEMS_NOT_REQUIRING_CHAT: FINDING-002 (fixed), ROOT-001, intake 3-6
PREREQ: durable materialize before claim; do not emit GO; do not emit bare /opsx-fix-bug
```
