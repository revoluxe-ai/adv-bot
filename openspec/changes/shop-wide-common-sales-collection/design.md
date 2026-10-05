## Context

**Current behavior (repository evidence):**

- `WBShop.run()` starts `CoroutinesManager.update_common_sale_stat(only_bot_active=False)` in TaskGroup (`wb_shop.py` L58–62). No other common-sales coroutine exists today.
- `update_common_sale_stat` loads ComplexAdv via `WBShopDataManager.get_complex_advs`; on success calls `CommonSaleStatUpdater.update_last_week_stats(advs)` chunking `main_nmid` by 20, calls `WBDataManager.get_sales_funnel_products_history`, inserts via `ClickHouseCommonStatManager` (`manager.py` L443–469, `common_sale_stat_updater.py` L27–57).
- `WBShopDataManager._get_advs` raises `NotFoundActiveAdvCompany` when no AdvSetting rows (`wb_shop_data_manager.py` L134–136) — **not** silent early return.
- `while_coroutine_decorator` catches `NotFoundActiveAdvCompany` and re-raises `StopShopUpdateException` (`while_coroutines_decorator.py` L156–158), which cancels the entire `asyncio.TaskGroup` in `WBShop.run()` (L58–95). `WBShop.run()` swallows the exception group but sibling coroutines are already cancelled for that tick.
- `run_process_func._run_shop_task` additionally catches `NotFoundActiveAdvCompany` and `StopShopUpdateException` at shop-process boundary (`run_process_func.py` L105–106, L123–124) — outer survival does **not** prevent in-tick TaskGroup sibling cancellation.
- Funnel stack: `AnalyticsManager.get_sales_funnel_products_history` → voronka adapter `@retry_decorator(60, 3)` → `raw_response_to_dto` → `CommonSaleStatRow`.
- CH writer: `INSERT INTO wb_common_stat (...) VALUES` with shared `version = time.time()` per batch.
- Read-latest pattern exists: `wb_common_stat_period_totals.py` and `clickhouse_manager.get_cart_to_order_ratio_from_common_items_stat` use `argMax(..., version) GROUP BY nmid, date`.
- Test seam: unit `test_common_sale_stat_updater.py`; integration `test_clickhouse_common_sale_stat_manager.py` (`@pytest.mark.destructive_local`, CH @ 127.0.0.1:8124); markers auto-assigned in root `conftest.py`.

**CH DDL evidence (read-only, no live credentials):**

- Migration `scripts/clickhouse_migrations/003_add_buyouts_sum_rub_to_wb_common_stat.sql`: `ALTER TABLE default_db.wb_common_stat ADD COLUMN buyouts_sum_rub Float64`.
- Test fixture DDL in `tests/support/destructive_ch_reset.py`: `ReplacingMergeTree(version) ORDER BY (nmid, date)` with columns `open_card, add_to_cart, orders, orders_sum, buy_outs, buyouts_sum_rub, version`.
- Live production DDL introspection: **BLOCKED** — no safe read-only prod CH path in this planning task without credentials; physical schema inferred from migration corpus + test fixture (sufficient for MVP — no DDL change planned). Release DDL confirmation remains an explicit non-production limitation.

**Sibling campaign boundary (reconciled):**

- Sibling change `shop-wide-campaign-data-collection` completed ownership reconciliation in
  `C:\Users\vkita\my_code\meta-repo\shop-wide-campaign-data-collection\openspec\changes\shop-wide-campaign-data-collection\COMMON_SALES_BOUNDARY_RECONCILIATION.md`
  (`TASK_ID: WB-SKY-COMMON-SALES-RECONCILE-20261005-0100-R2`, `CAMPAIGN_CHANGE_RECONCILED: YES`).
- Campaign change removed competing `wb_common_stat` write obligations; legacy `update_common_sale_stat` documented as existing route owned by this change.
- **CAMPAIGN_CHANGE_RECONCILED=YES** in this worktree via sibling receipt fingerprint (not inferred from absence).

## Goals / Non-Goals

**Goals:**

- Collect factual common-sales for all current non-trash shop SKU (A) minus legacy-assigned E, disjoint per tick, through **one** existing `update_common_sale_stat` coordinator coroutine.
- On **every regular tick** refresh **all** assigned E nmIDs and **all** discovered U nmIDs over the 7 MSK-day rolling window (CH read-latest is dedup/aggregation only — never a skip gate).
- Preserve legacy E semantics including E∖A; E absent from A retained on legacy route.
- Prove coverage from **current attempted collection** + proven assortment pagination; minimal Redis last-attempt evidence (no new facts table).
- Fail-closed on partial pagination / API null; retain old facts on failure.
- Required structured logs without secrets; counter semantics explicit (R5).
- Bounded no-ad TaskGroup survival at `WBShop.run()` level without global decorator weakening.

**Non-Goals:**

- History backfill beyond 7 MSK days.
- Fake daily history from period aggregates.
- Campaign discovery, `full_adv_wb_stat`, Store DRR numerator.
- New CH table, dirty AI Package exporter copy, `SHOP_PRODUCT_ORDERS_SALES`.
- AdvSetting mutations, bot_active changes, WB ad writes.
- Independent scripts / Job executor / second process / second common-sales coroutine.
- Giant coverage/read-model platform.

## Architecture Decision References

1. `openspec/changes/shop-wide-common-sales-collection/decisions/shop-wide-common-sales-ownership/decision.md` (accepted) — A/E/U partition, single coordinator ownership, forbidden sources.
2. `openspec/decisions/clickhouse-migration-lifecycle-ownership/decision.md` — CH migration gate cleared for shop-wide expansion (archived change).
3. Sibling `shop-wide-campaign-data-collection` / `COMMON_SALES_BOUNDARY_RECONCILIATION.md` — campaign `full_adv_wb_stat` ownership; **CAMPAIGN_CHANGE_RECONCILED=YES**.

Checklist:

- [x] context-first decision lookup performed (bounded fallback ≤3)
- [x] relevant decisions cited
- [x] new decision proposed (shop-wide-common-sales-ownership)
- [x] implementation layer matches decision (single existing coroutine coordinator)

## Ownership & Placement

| Layer | Role |
|-------|------|
| **`CoroutinesManager.update_common_sale_stat`** (existing coroutine — **becomes coordinator**) | Single tick owner: paginate A once; resolve one frozen ComplexAdv snapshot E once; derive U=A−E once; invoke shared updater on disjoint E and U (or dedup union with route attribution); emit logs; persist minimal Redis last-attempt evidence |
| **`CommonSaleStatUpdater`** (extend) | Shared collect+insert engine; add explicit `nmids` entry; keep ComplexAdv path for Redis adv_id timestamp side effects on E route |
| **`ShopAssortmentReader`** (new helper) | Paginated `ProductsManager.get_cards_list`, fail-explicit null/partial |
| **`ClickHouseCommonStatManager`** | Sole CH write adapter (unchanged) |
| **`taskgroup_no_ad_supervisor`** (new bounded seam at `WBShop.run` task factory) | Wraps each registered TaskGroup coroutine factory before `tg.create_task`; catches **only** `StopShopUpdateException` whose direct `__cause__` is `NotFoundActiveAdvCompany`, logs, bounded sleep+restart same factory; all other exceptions/auth/cancellation unchanged; `while_coroutine_decorator` global policy unchanged |

**Forbidden layers:**

- Second common-sales coroutine (`update_shop_wide_common_sale_stat` or parallel legacy funnel execution)
- AdvSetting/ComplexAdv as A authority
- WBCard cabinet cache as all-shop list
- Campaign funnel adapter duplicate
- Scripts / ARQ / Job executor entrypoints
- CH row existence as recollection skip gate
- UI / control-plane / transport

**Rationale:** One frozen routing coordinator inside the existing public coroutine preserves API/writer seams, eliminates duplicate E loads and U/E collect races, and matches sibling reconciliation (legacy route = this coroutine).

## Semantic Write Target

```text
TARGET_ENTITY_OR_LEG: wb_common_stat (nmid, date) factual rows for shop-wide U and legacy E
ALLOWED_ADAPTERS: ClickHouseCommonStatManager.insert via CommonSaleStatUpdater;
                  WBDataManager.get_sales_funnel_products_history (read WB API)
FORBIDDEN_ADAPTERS: full_adv_wb_stat writer; AdvSetting PG writes; WB advertising write APIs;
                    SHOP_PRODUCT_ORDERS_SALES; new common-facts table insert
```

## Derived Lifecycle

`LIFECYCLE_STATUS: DERIVED`

| Step | Description | Source |
|------|-------------|--------|
| L1 | Tick start — resolve shop_id, MSK today, 7-day inclusive window `[today-6, today]` | Owner contract |
| L2 | Discover A — paginate `get_cards_list` until exhausted; fail-explicit on null/partial; record pagination proof | Owner contract + ProductsManager |
| L3 | Resolve E — one frozen ComplexAdv snapshot `only_bot_active=False`; bounded NotFound → E=∅ inside coordinator only | Owner contract + wb_shop_data_manager |
| L4 | Partition U=A−E once; compute counter sets \|A\|, \|E\|, \|U\| | Owner contract |
| L5 | Collect **all** E nmIDs and **all** U nmIDs over window (regular recollection every tick); shared updater, batch 20, retry | Owner contract + existing updater |
| L6 | Evaluate completeness from **this tick's** API responses + assortment proof; persist Redis last-attempt evidence; CH argMax for read-latest only | Owner contract |
| L7 | Log counters + coverage_status; Redis A/E/U transition snapshot | Owner contract |
| L8 | On failure — no zero-fill; prior CH rows/freshness unchanged; mark partial scope honestly | Owner contract |

`OWNER_LIFECYCLE_ECHO`: steps L1–L8 above (durable in this design).

## Data Flow

```text
WBShop TaskGroup
  update_common_sale_stat(only_bot_active=False)  [SINGLE COORDINATOR — existing registration only]
    ├─ A ← ShopAssortmentReader.paginate (ProductsManager.get_cards_list, non-trash)
    ├─ E ← _resolve_legacy_assigned_nmids() | NotFoundActiveAdvCompany → ∅
    ├─ U ← A \ E  (computed once per tick)
    ├─ Collect route E: CommonSaleStatUpdater.update_last_week_stats(complex_advs=frozen_snapshot)
    │     OR explicit nmids=sorted(E) preserving adv Redis timestamp side effects
    ├─ Collect route U: CommonSaleStatUpdater.update_last_week_stats(nmids=sorted(U))
    │     (disjoint inputs — no nmID in both routes same tick)
    ├─ Completeness ← current API returned pairs + assortment pagination proof
    ├─ Redis last-attempt evidence (scope/window/partial reason)
    └─ ClickHouseCommonStatManager.insert → wb_common_stat (unchanged writer)

  Other TaskGroup coroutines (see exhaustive registry §No-Campaign TaskGroup Survival)
    └─ WBShop.run task factory → taskgroup_no_ad_supervisor(create_task wrapper)
         catches StopShopUpdateException ONLY when __cause__ is NotFoundActiveAdvCompany
         → bounded sleep + restart same coroutine factory (does NOT cancel TaskGroup siblings)
```

**No** `update_shop_wide_common_sale_stat` TaskGroup registration. **No** parallel legacy funnel coroutine.

**Window:** MSK `ZoneInfo("Europe/Moscow")`; `start = today - 6 days`, `end = today` (inclusive 7 calendar days). TODAY rows treated as provisional (may revise on later ticks via ReplacingMergeTree version).

**Regular recollection (R2):** Every tick MUST call the shared updater for **full** sorted E and **full** sorted U over `[start, end]`. CH pre-existence of 7 rows per nmID MUST NOT suppress refresh — late WB revisions and current-day provisional updates require re-fetch. `ShopWideCommonStatCoverageReader` / argMax queries are for downstream read-latest aggregation and post-tick diagnostics only.

**A discovery:** Reuse pagination loop pattern from `ProductsManager.get_card_by_nmid_via_full_list` (limit 100, cursor advance). Filter: default Content API (excludes trash per docstring L52–53). Deleted/trash cards: unsupported for re-add semantics — if nmID leaves A, stop targeting on later ticks; no CH delete. On `response is None` mid-pagination → tick failure, `coverage_status=PARTIAL_ASSORTMENT`, continue legacy E route if E resolved, mark partial shop scope, no invented U beyond proven A pages.

**E resolution (bounded no-campaign seam — coordinator body):** `_resolve_legacy_assigned_nmids()` wraps `get_complex_advs(only_bot_active=False, load_extras=False)`:
- Success → `E = {adv.main_nmid}` sorted unique; retain frozen ComplexAdv list for legacy Redis timestamp path.
- `NotFoundActiveAdvCompany` → log info, `E = ∅` (**only inside coordinator**; decorator unchanged globally).

**Collect routing:** Two disjoint updater invocations (preferred) or one dedup union with per-nmID route attribution `{E|U}` logged. Same batch size 20, same adapter, same retry. Mid-batch WB failure: retain prior CH facts for failed nmIDs; increment `failed_count`; do not zero-fill missing dates.

**Missing/null vs observed zero:** API null/omitted date → not counted as returned complete pair; never insert zero row. Observed numeric zero from API → valid metric if all required fields present and finite.

**Returned-fact validation (R4 — reject invalid/conflicting):** Before CH insert, normalize and validate every `(nmid, date)` from **this tick's** API responses against the frozen tick context (shop_id, attempted nmID set, MSK window `[start, end]`):

| Condition | Action |
|-----------|--------|
| nmid ∉ attempted E∪U for this tick | REJECT pair; log; do not insert; count toward partial |
| date outside `[start, end]` MSK | REJECT pair |
| required metrics missing, null, NaN, or non-finite | REJECT pair (not zero-fill) |
| identical duplicate `(nmid, date, metrics)` in same response batch | deduplicate deterministically (stable sort by source index; keep first) |
| conflicting duplicate `(nmid, date)` with differing metrics | REJECT conflicting set for that key; mark partial; MUST NOT arbitrarily pick newest |
| cross-shop row (shop_id mismatch) | REJECT; never insert |

Partial success: per-nmID collect outcome — successful nmIDs insert validated rows; failed/rejected nmIDs retain prior CH facts; `failed_count` and last-attempt evidence reflect honest partial. Per-source validation: each `get_sales_funnel_products_history` request MUST carry the exact nmID batch and window bounds used; responses validated against that request identity before aggregation.

**Last-attempt STARTED state:** Redis last-attempt evidence MUST transition to `attempt_status=STARTED` with window/scope fields **before** any WB funnel API await for the tick. On cancellation, timeout, or mid-tick failure, readers MUST NOT treat a prior `COMPLETE` record as current — consult in-flight STARTED or terminal partial/failed state. MUST NOT emit `COMPLETE` or increment success counters when CH insert failed for that nmID batch.

**Duplicate-version read:** Consumers use argMax latest per `(nmid, date)`; never sum versions.

## Logging Contract

Structured INFO log per tick:

```text
shop_wide_common_sale_stat tick shop_id=%s all_shop_nmids_count=%d existing_covered_count=%d uncovered_count=%d updated_count=%d failed_count=%d coverage_status=%s
```

Optional diagnostic fields (same log line or DEBUG): `expected_pair_count`, `returned_pair_count`, `missing_pair_count`, `assortment_pages`.

**Counter semantics (R5):**

| Field | Definition |
|-------|------------|
| `all_shop_nmids_count` | \|A\| — current non-trash assortment SKU count |
| `existing_covered_count` | \|E\| — legacy assigned SKU count (NOT nmid×date pairs) |
| `uncovered_count` | \|U\| — shop-wide collect SKU count (NOT nmid×date pairs) |
| `updated_count` | nmIDs whose collect attempt succeeded this tick (E∪U routes) |
| `failed_count` | nmIDs whose collect attempt failed this tick |
| `coverage_status` | Derived from **this tick** assortment proof + API completeness (see below) |

`coverage_status` enum: `COMPLETE`, `PARTIAL_ASSORTMENT`, `PARTIAL_API`, `PARTIAL_CH`, `FAILED`.

Completeness MUST NOT be inferred from pre-existing CH rows or Redis hash presence alone.

## Last-Attempt Coverage Evidence (minimal, R4)

Redis key `shop_wide_common_sales:last_attempt:{shop_id}` (JSON, TTL ≥ 2× tick):

```json
{
  "attempt_status": "STARTED|COMPLETE|PARTIAL|FAILED",
  "window_start": "YYYY-MM-DD",
  "window_end": "YYYY-MM-DD",
  "a_count": 500,
  "e_count": 120,
  "u_count": 380,
  "assortment_complete": true,
  "assortment_pages": 5,
  "expected_pair_count": 3500,
  "returned_pair_count": 3480,
  "missing_pair_count": 20,
  "rejected_pair_count": 0,
  "partial_reason": null,
  "tick_ts": "ISO-8601"
}
```

`attempt_status=STARTED` MUST be written before the first funnel API call of the tick. Terminal states (`COMPLETE`, `PARTIAL`, `FAILED`) written only after tick evaluation; never upgrade to `COMPLETE` when CH insert failed or validation rejected pairs.

- `expected_pair_count` = \|A\| × 7 MSK dates (qualification scope for full-shop honesty).
- `returned_pair_count` = `(nmid, date)` pairs with complete finite metrics from **this tick's** API responses for attempted nmIDs.
- `missing_pair_count` = expected − returned (honest partial).
- Transition snapshot key `shop_wide_common_sales:transition:{shop_id}` retains sorted A/E/U hashes for ad↔non-ad logging (no CH delete).

Readers MUST NOT present stale preexisting CH rows as current complete after API/assortment failure — consult last-attempt evidence + freshness truth.

## No-Campaign TaskGroup Survival (R3)

**Problem (code-grounded):** Any TaskGroup coroutine whose body lets `NotFoundActiveAdvCompany` reach `while_coroutine_decorator` is converted to `StopShopUpdateException` (L156–158) which **propagates out of the decorated coroutine** (not swallowed by inner `except StopShopUpdateException: break`), cancelling **all** sibling coroutines for that tick — including the common-sales coordinator even if it uses a local E=∅ seam.

**Rejected:** Global change to `while_coroutine_decorator` NotFound handling (weakens all coroutines). Coordinator-only local catch (insufficient — siblings still cancel group). Per-body edits on every `CoroutinesManager` method (high churn; registry drift risk).

**Normative criterion:** Every coroutine registered in `WBShop.run()` TaskGroup (`wb_shop.py` L58–89) MUST be classified in the registry below. Any member whose execution path calls `WBShopDataManager.get_complex_advs` or `get_pre_complex_advs` (transitive via `_get_advs`) **without** local `NotFoundActiveAdvCompany` handling MUST be wrapped at the **WBShop task factory** before `tg.create_task`. Members with no loader path or with coordinator-local seam are exempt.

**Solution — minimal `taskgroup_no_ad_supervisor` at WBShop task factory:**

1. `WBShop.run()` wraps eligible `tg.create_task(...)` factories through `taskgroup_no_ad_supervisor(coro_factory)` — one seam, no per-method body edits.
2. Wrapper `await`s the decorated coroutine until it exits; on `StopShopUpdateException`, inspect **direct** `__cause__`:
   - `NotFoundActiveAdvCompany` → log info, `await asyncio.sleep(SHOP_RUNNER_NO_ADV_RETRY_SEC)` (bounded, env-default 300s), restart **same** coroutine factory (bounded retry counter optional; default unbounded sleep loop matches decorator semantics).
   - any other cause → re-raise unchanged (preserves auth cancel and other stop semantics).
3. `_API_FORBIDDEN_ERRORS` and non-NotFound exceptions propagate unchanged through the decorated coroutine to TaskGroup.
4. **Coordinator path:** `update_common_sale_stat` uses `_resolve_legacy_assigned_nmids` (NotFound → E=∅ inside coordinator body) — **exempt** from task factory wrapper (local handling prevents NotFound reaching decorator).
5. **Registry drift guard:** unit test AST/membership binds `WBShop.run` `create_task` registrations to registry set; fail on add/remove without registry update.

### Exhaustive TaskGroup registry (HEAD `62c8d48…`, code evidence)

| # | TaskGroup coroutine | `wb_shop.py` | Loader call site | Local NotFound handling | Missing-ad TaskGroup cancel risk | Supervisor required |
|---|---------------------|--------------|------------------|-------------------------|----------------------------------|---------------------|
| — | `_alive_worker_run` | L59 | none | n/a | **no** | **no** |
| 1 | `update_advs_data_from_wb_to_pg` | L60 | none (`data_manager.update_advs_data_from_wb_to_pg`) | n/a | **no** | **no** |
| 2 | `update_cards_data_from_wb_to_pg` | L61 | none (`ShopDataUpdater.update_cards_data`) | n/a | **no** | **no** |
| 3 | `update_common_sale_stat` | L62 | `get_complex_advs` → replaced by `_resolve_legacy_assigned_nmids` in coordinator | **yes** (coordinator seam: NotFound→E=∅) | **no** (after coordinator refactor) | **no** (local seam) |
| 4 | `update_full_adv_stat` | L63 | `manager.py` L481–484 `get_complex_advs` | **no** | **yes** | **yes** |
| 5 | `update_clusters_adv_stats_today` | L64 | `manager.py` L1027–1030 | **no** | **yes** | **yes** |
| 6 | `update_clusters_adv_stats_history` | L65–67 | `manager.py` L1110–1113 | **no** | **yes** | **yes** |
| 7 | `refresh_stats_freshness_cache` | L68 | `manager.py` L350–353 `get_complex_advs` | **no** | **yes** | **yes** |
| 8 | `adv_settings_auto_update` | L69 | `manager.py` L532–535 | **no** | **yes** | **yes** |
| 9 | `update_minus_phrases_in_advs` | L70 | `manager.py` L786–789 | **no** | **yes** | **yes** |
| 10 | `update_cluster_bids` | L71 | `manager.py` L1129–1132 | **no** | **yes** | **yes** |
| 11 | `cache_current_cluster_bids` | L72 | `manager.py` L1201–1204 | **no** | **yes** | **yes** |
| 12 | `preload_min_bids_cache_miss` | L73 | `manager.py` L1247–1250 | **no** | **yes** | **yes** |
| 13 | `preload_min_bids_cache_old` | L74 | `manager.py` L1308–1311 | **no** | **yes** | **yes** |
| 14 | `handle_stats_stale_emergency` | L75 | `manager.py` L1338–1341 | **no** | **yes** | **yes** |
| 15 | `update_plan_fact_stats` | L76 | `manager.py` L1520–1524 `get_pre_complex_advs` → `_get_advs` (`wb_shop_data_manager.py` L411, L134–136) | **no** | **yes** | **yes** |
| 16 | `auto_budget_watchdog` | L80 | `manager.py` L837 | **no** | **yes** | **yes** |
| 17 | `update_top_key_in_advs` | L81 | none (early return L631) | n/a | **no** | **no** |
| 18 | `update_common_bid_in_search_adv` | L82 | `manager.py` L1635–1638 | **no** | **yes** | **yes** |
| 19 | `increment_fact_data_stats` | L83 | `manager.py` L1693–1696 | **no** | **yes** | **yes** |
| 20 | `auto_shelf_bid_increment_stats` | L84 | `manager.py` L1728–1731 | **no** | **yes** | **yes** |
| 21 | `auto_shelf_bid_control` | L85 | `manager.py` L1762 | **no** | **yes** | **yes** |
| 22 | `white_list_tail_trimmer` | L86 | none (early return L797) | n/a | **no** | **no** |
| 23 | `auto_reset_bid_for_auto_adv` | L87 | `manager.py` L1582–1585 | **no** | **yes** | **yes** |
| 24 | `update_individual_keyword_target_places` | L88 | none (early return L803) | n/a | **no** | **no** |
| 25 | `change_adv_strategy` | L89 | `manager.py` L1813–1816 | **no** | **yes** | **yes** |

**Summary:** 25 `CoroutinesManager` registrations + `_alive_worker_run`. **18 require** task factory wrapper; **1 exempt** (coordinator local seam); **6 no loader path** (no wrapper). `refresh_stats_freshness_cache` is a canonical high-risk sibling (same TaskGroup, unsupervised today).

**Proof requirements:**

- **S04b:** `WBShop.run()` TaskGroup — coordinator completes while wrapped sibling gets NotFound → bounded restart, **no** TaskGroup-wide cancel.
- **S04c:** `ApiForbiddenError` from wrapped coroutine still propagates/cancels.
- **S04d:** AST/membership test — `WBShop.run` `create_task` set equals registry; supervisor set equals {rows with supervisor=yes}.
- **S04e:** Non-NotFound `StopShopUpdateException` (other cause) still propagates — not swallowed by wrapper.

**Ads appear later:** Wrapped coroutines restart same factory after bounded sleep; when `get_complex_advs` succeeds, normal decorator loop resumes — no silent permanent termination.

## Ad Membership Transitions (R6)

Both directions each tick:

- **non-ad→ad:** nmID ∈ U on T, ∈ E on T+1 → collect route switches U→E; prior CH rows retained.
- **ad→non-ad:** nmID ∈ E on T, ∈ U on T+1 → collect route switches E→U; prior CH rows retained.

Recomputed from current A and frozen E snapshot only; no historical CH delete. Cursor loop / page bound: paginate until empty cursor; no silent cap. If assortment fails mid-pagination: legacy E route still runs, `coverage_status=PARTIAL_ASSORTMENT`, U scope only for proven A pages.

## Numerator / DRR Status

`NUMERATOR_STATUS=BLOCKED_BY_CAMPAIGN_COVERAGE` — this change does not implement campaign-side collector or Store DRR denominator. Existing `load_campaign_orders_per_cart_7d` / V3 paths unchanged.

## Validation Plan

| Gate | Command |
|------|---------|
| Unit (coordinator partition, regular recollection, pagination fail) | `poetry run pytest -m unit tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py -v` |
| Unit (TaskGroup no-ad survival — WBShop.run seam) | same file — `test_taskgroup_survives_no_campaign_*`, `test_taskgroup_registry_ast_binding` |
| Unit (invalid/conflicting fact rejection) | same file — `test_reject_*`, `test_started_before_api_*` |
| Unit (legacy updater regression) | `poetry run pytest -m unit tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py -v` |
| Integration (CH writer + argMax read) | `poetry run pytest -m "integration and destructive_local" tests/integration/test_shop_wide_common_sale_stat_coverage.py -v` |
| Strict types (post-apply) | `poetry run pyright-strict` (targeted modules) |
| Planning whitespace | `git diff --check` |
| OpenSpec | `openspec validate --change shop-wide-common-sales-collection --strict` |

Integration tests MUST use proven **task-owned** dedicated local scratch CH only: call `validate_destructive_clickhouse_endpoint` (`tests/support/destructive_clickhouse.py`) before client creation; database `test_adv_bot_clickhouse` (not `default_db`); table `wb_common_stat` in `CH_TEST_OWNED_TABLES` (`destructive_ch_reset.py`); opt-in `ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1`; `@pytest.mark.destructive_local`. Fixed port 8124 alone is **not** ownership proof — endpoint validation + test DB + owned table DDL required. No shared/prod resources; no live production inspection; destructive tests not run at planning close.

## Performance Considerations

- |A|≈500 → ~5 Content API pages (limit 100) + ~38 funnel batches for full U (380 nmIDs) + ~6 for E (120) per tick.
- Regular full refresh every 5 min tick — acceptable per Owner; shared rate limiter unchanged.
- Coordinator timeout: inherits `while_coroutine_decorator` 30 min cap.

## Rollback

- Revert coordinator body inside `update_common_sale_stat` to legacy E-only behavior.
- Remove `taskgroup_no_ad_supervisor` wrapper from `WBShop.run` task factory.
- CH data append-only — no migration rollback needed.

## DESIGN_STATUS

`DESIGN_STATUS: READY_FOR_REVIEW`
`NORMATIVE_MODALITY_PRESERVED: yes`
`PLANNING_REPAIR: WB-SKY-COMMON-SALES-PLAN-CLOSE-20261005-0130`
