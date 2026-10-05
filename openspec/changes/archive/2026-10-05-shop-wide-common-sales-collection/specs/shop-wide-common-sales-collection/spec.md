# shop-wide-common-sales-collection

Shop-runner runtime collection of factual common-sales (funnel metrics) for all
current non-trash shop SKU, partitioned against legacy campaign-assigned nmIDs,
with honest coverage over a 7 MSK-day rolling window.

## ADDED Requirements

### Requirement: Shop-wide assortment universe

The system MUST define **A** as the set of nmIDs returned by paginating the
Content API product cards list for the shop, excluding trash cards (API default).
The system MUST NOT use AdvSetting, ComplexAdv sold IDs, or WBCard cabinet cache
as the all-shop assortment authority.

#### Scenario: Complete pagination builds A

- **GIVEN** Content API returns paginated non-trash cards totaling 500 unique nmIDs across 5 pages (limit 100, cursor advance until exhausted)
- **WHEN** the common-sales coordinator resolves assortment on a tick
- **THEN** **A** MUST contain exactly those 500 nmIDs
- **AND** MUST NOT include duplicate nmIDs
- **AND** MUST record pagination proof (page count / cursor completion)

#### Scenario: Partial pagination fails closed

- **GIVEN** Content API returns a null response before pagination completes
- **WHEN** the common-sales coordinator resolves assortment
- **THEN** the tick MUST NOT treat missing pages as empty assortment
- **AND** MUST set `coverage_status` to `PARTIAL_ASSORTMENT` or `FAILED`
- **AND** MUST NOT insert fabricated zero rows
- **AND** MUST continue legacy E collect route when E is resolved
- **AND** MUST NOT invent U beyond nmIDs from proven A pages

#### Scenario: Terminal pagination boundary at exactly five full pages

- **GIVEN** Content API returns exactly 500 unique nmIDs across 5 pages (limit 100, pages 1–5 each full)
- **AND** page 6 returns an empty cursor / zero cards (terminal boundary)
- **WHEN** the common-sales coordinator resolves assortment
- **THEN** **A** MUST contain exactly 500 nmIDs
- **AND** pagination proof MUST record 5 completed pages plus terminal empty page evidence
- **AND** MUST NOT treat the empty page 6 as pagination failure

### Requirement: Legacy assigned partition E

The system MUST define **E** on each tick as the sorted unique set of
`main_nmid` from a **single frozen** `only_bot_active=False` ComplexAdv snapshot.
**E** is assigned collect input for the legacy route and MUST NOT be interpreted
as the shop-wide success set.

#### Scenario: E includes nmIDs absent from current A

- **GIVEN** legacy assigned nmID 999 is in **E** but not in current **A**
- **WHEN** the common-sales coordinator runs on the same tick
- **THEN** nmID 999 MUST remain in legacy assigned collect input (E route)
- **AND** shop-wide full-shop coverage reporting MUST qualify completeness against current **A** only

#### Scenario: No campaigns yields empty E in coordinator path

- **GIVEN** the shop has no active AdvSetting rows
- **WHEN** the common-sales coordinator resolves **E** via `_resolve_legacy_assigned_nmids`
- **THEN** **E** MUST be empty
- **AND** **U** MUST equal **A**
- **AND** the coordinator MUST NOT propagate `NotFoundActiveAdvCompany` to `while_coroutine_decorator`

#### Scenario: TaskGroup survives no-campaign sibling coroutines

- **GIVEN** the shop has no active AdvSetting rows
- **AND** every TaskGroup coroutine in the exhaustive registry (design.md §No-Campaign TaskGroup Survival) that calls `get_complex_advs` or `get_pre_complex_advs` without local NotFound handling is wrapped at `WBShop.run` task factory via `taskgroup_no_ad_supervisor`
- **WHEN** `WBShop.run()` executes a full tick
- **THEN** the common-sales coordinator MUST complete its tick (U=A collect attempt)
- **AND** wrapped siblings (including `refresh_stats_freshness_cache`) MUST NOT propagate `StopShopUpdateException` with direct cause `NotFoundActiveAdvCompany` to the TaskGroup
- **AND** MUST NOT cancel unrelated required TaskGroup work for that tick

#### Scenario: Auth errors still cancel shop

- **GIVEN** a task-factory-wrapped coroutine receives `ApiForbiddenError` (token/auth)
- **WHEN** `WBShop.run()` executes
- **THEN** the error MUST NOT be swallowed by the no-ad supervisor
- **AND** shop update MUST fail/cancel per existing policy

#### Scenario: Other StopShopUpdateException causes not swallowed

- **GIVEN** a wrapped coroutine raises `StopShopUpdateException` whose direct `__cause__` is **not** `NotFoundActiveAdvCompany`
- **WHEN** `WBShop.run()` executes
- **THEN** the exception MUST propagate unchanged
- **AND** MUST NOT be converted to bounded retry

#### Scenario: TaskGroup registry AST membership guard

- **GIVEN** `WBShop.run()` TaskGroup registration at `wb_shop.py` L58–89
- **WHEN** the registry guard test runs
- **THEN** the set of registered `CoroutinesManager` coroutine names MUST equal the exhaustive registry in design.md
- **AND** the supervisor-required subset MUST equal coroutines with loader path and no local NotFound handling (18 members at HEAD `62c8d48…`)
- **AND** `update_common_sale_stat` MUST be exempt (coordinator local seam only)

### Requirement: Disjoint partition U

The system MUST compute **U = A − E** exactly once per tick from the same frozen A and E.
**U** and **E** MUST be disjoint.
The coordinator MUST collect via separate disjoint updater invocations (or dedup union with route attribution).
There MUST NOT be two parallel coroutines independently reloading E.

#### Scenario: Standard partition 500 A, 120 E, 380 U

- **GIVEN** |A|=500, |E|=120, and E⊆A
- **WHEN** partitions are computed once per tick
- **THEN** |U| MUST be 380
- **AND** U∩E MUST be empty
- **AND** collect plans MUST NOT duplicate any nmID within the same tick

#### Scenario: Single coordinator frozen snapshot

- **GIVEN** ComplexAdv snapshot would change if reloaded mid-tick
- **WHEN** the coordinator resolves E and derives U
- **THEN** exactly one ComplexAdv load MUST occur per tick
- **AND** U MUST be derived as A minus that single E snapshot

### Requirement: Ad membership transitions

Non-ad→ad and ad→non-ad moves MUST be recomputed each tick from current **A**
and frozen **E**.
Historical `wb_common_stat` rows MUST NOT be deleted because of membership
transitions.

#### Scenario: SKU moves from non-ad to ad

- **GIVEN** nmID was in **U** on tick T and moves into **E** on tick T+1
- **WHEN** tick T+1 runs
- **THEN** shop-wide collect input MUST exclude that nmID from U route
- **AND** legacy assigned input MUST include it in E route
- **AND** prior CH rows for that nmID MUST remain queryable

#### Scenario: SKU moves from ad to non-ad

- **GIVEN** nmID was in **E** on tick T and is not in frozen **E** on tick T+1 but remains in **A**
- **WHEN** tick T+1 runs
- **THEN** nmID MUST appear in **U** collect route
- **AND** prior CH rows MUST remain queryable

### Requirement: Rolling 7 MSK-day window with regular recollection

The system MUST collect on **every regular tick** for **all** nmIDs in **E** and **U**
over the inclusive MSK calendar window `[today−6, today]` (7 days).
Pre-existing CH rows MUST NOT suppress refresh.
**TODAY** MUST be treated as provisional (may be superseded by later version).

#### Scenario: Window includes today

- **GIVEN** MSK today is 2026-10-05
- **WHEN** the coordinator computes the collect window
- **THEN** expected dates MUST be 2026-09-29 through 2026-10-05 inclusive

#### Scenario: Regular refresh despite existing CH rows

- **GIVEN** nmID in **U** already has 7 `(nmid, date)` rows in CH from prior ticks
- **WHEN** a regular coordinator tick runs
- **THEN** the shared updater MUST still fetch and insert fresh rows for that nmID over the window
- **AND** CH read-latest (argMax) MUST NOT be used as a reason to skip recollection

### Requirement: Missing and partial never zero

Missing, null, or partial API/CH data MUST NOT be written or reported as numeric
zero.
Observed numeric zero from API with complete finite metrics is valid.
A complete `(nmid, date)` response MUST be proven from **this tick's** API attempt before counting as returned.

#### Scenario: API returns no history for a date

- **GIVEN** WB funnel API omits a date for an otherwise valid nmID
- **WHEN** coverage is evaluated for this tick
- **THEN** that `(nmid, date)` MUST NOT be marked returned-complete
- **AND** MUST NOT insert a zero-filled row

#### Scenario: Failure retains old facts

- **GIVEN** `wb_common_stat` already has versioned rows for nmID 42
- **WHEN** a collect tick fails before successful insert for nmID 42
- **THEN** prior rows for nmID 42 MUST remain unchanged
- **AND** freshness truth MUST NOT claim success

#### Scenario: Mid-batch WB failure

- **GIVEN** a batch of 20 nmIDs where 15 succeed and 5 fail
- **WHEN** the tick completes
- **THEN** successful nmIDs MUST have new rows inserted
- **AND** failed nmIDs MUST retain prior CH facts
- **AND** `failed_count` MUST reflect failed nmIDs

### Requirement: Reject invalid and conflicting returned facts

The coordinator MUST validate every `(nmid, date)` fact from **this tick's** WB
funnel responses against the frozen tick context (shop_id, attempted E∪U nmID set,
MSK window `[today−6, today]`) **before** CH insert.

The system MUST:

- REJECT pairs whose nmid was not in the attempted collect set for this tick
- REJECT pairs whose date falls outside the MSK window
- REJECT pairs with missing, null, NaN, or non-finite required metrics (never zero-fill)
- Deduplicate **identical** duplicate `(nmid, date, metrics)` deterministically (stable source order; keep first)
- REJECT **conflicting** duplicate `(nmid, date)` rows with differing metrics — MUST NOT arbitrarily pick newest
- NEVER insert cross-shop rows or invented-zero rows

Partial success MUST be per nmID: validated pairs for successful nmIDs insert;
rejected/failed nmIDs retain prior CH facts; counters and last-attempt evidence
reflect honest partial state.

Each `get_sales_funnel_products_history` call MUST validate responses against
that request's exact nmID batch and window bounds (per-source request identity).

#### Scenario: Unexpected nmid rejected

- **GIVEN** funnel API returns metrics for nmID 999999 not in attempted E∪U for this tick
- **WHEN** the coordinator validates the response
- **THEN** pairs for nmID 999999 MUST be rejected
- **AND** MUST NOT insert rows for nmID 999999

#### Scenario: Out-of-window date rejected

- **GIVEN** MSK window is 2026-09-29 through 2026-10-05
- **AND** API returns a row for nmID 42 with date 2026-09-28
- **WHEN** validation runs
- **THEN** that pair MUST be rejected
- **AND** MUST NOT be counted as returned-complete

#### Scenario: Conflicting duplicate key rejected

- **GIVEN** the same tick returns two rows for `(nmid=42, date=2026-10-01)` with differing `orders` values
- **WHEN** validation runs
- **THEN** both conflicting rows MUST be rejected for insert
- **AND** `coverage_status` MUST NOT be `COMPLETE`
- **AND** prior CH rows for that key MUST remain unchanged

#### Scenario: Identical duplicate deduplicated

- **GIVEN** the same tick returns two byte-identical rows for `(nmid=42, date=2026-10-01)`
- **WHEN** validation runs
- **THEN** exactly one row MUST be inserted for that key
- **AND** deduplication MUST be deterministic (stable source order)

#### Scenario: Non-finite required metric rejected

- **GIVEN** API returns `orders=NaN` for an otherwise valid `(nmid, date)` in window
- **WHEN** validation runs
- **THEN** that pair MUST be rejected
- **AND** MUST NOT insert a zero-filled substitute row

### Requirement: Shared collector reuse

Shop-wide and legacy routes MUST share the same funnel adapter, batch size 20,
retry/limit behavior, DTO normalization, and ClickHouse writer within the **single**
`update_common_sale_stat` coordinator.
The updater MUST accept explicit nmID lists for U route collection.

#### Scenario: Full partition uses batch 20 on E and U routes

- **GIVEN** a tick with |A|=500, |E|=120, |U|=380 (disjoint partition)
- **WHEN** collection runs on full sorted E and full sorted U
- **THEN** the WB API MUST be called via `get_sales_funnel_products_history` in batches of 20 (and remainder) for each route
- **AND** total await count MUST reflect ceil(120/20)+ceil(380/20) collector calls
- **AND** MUST use the same adapter entrypoint as legacy collection
- **AND** tests MUST mock/spy the actual collector method (not partition logic under test)

#### Scenario: U-route remainder batch boundary

- **GIVEN** U route collect input is exactly 25 nmIDs (subset test fixture — not simultaneous with |U|=380 on same tick)
- **WHEN** collection runs on U route only
- **THEN** collector MUST be invoked twice (20 + 5 remainder)
- **AND** both batches MUST use the shared adapter entrypoint

### Requirement: Single shop-runner coordinator coroutine

Exactly **one** common-sales coordinator MUST run inside the existing
`CoroutinesManager.update_common_sale_stat` coroutine registered in WBShop TaskGroup.
A second common-sales coroutine MUST NOT be registered.
Independent scripts, Job executor processes, or parallel legacy funnel executors MUST NOT
perform shop-wide common-sales collection.

#### Scenario: No second coroutine registration

- **GIVEN** shop-runner is the production entrypoint
- **WHEN** shop-wide common-sales collection is scheduled
- **THEN** it MUST be implemented inside existing `update_common_sale_stat` only
- **AND** `WBShop.run()` MUST NOT register `update_shop_wide_common_sale_stat` or equivalent parallel coroutine

### Requirement: Required tick logging with explicit counter semantics

Each coordinator tick MUST emit structured logs containing, without secrets:
`shop_id`, `all_shop_nmids_count`, `existing_covered_count`, `uncovered_count`,
`updated_count`, `failed_count`, `coverage_status`.

Counter definitions:
- `all_shop_nmids_count` = |A|
- `existing_covered_count` = |E| (SKU count, NOT nmid×date pairs)
- `uncovered_count` = |U| (SKU count, NOT nmid×date pairs)
- `updated_count` / `failed_count` = nmID-level collect outcomes this tick

Optional diagnostics: `expected_pair_count`, `returned_pair_count`, `missing_pair_count`.

#### Scenario: Successful tick log fields

- **GIVEN** a tick with |A|=500, |E|=120, |U|=380, 495 nmIDs updated, 5 failed
- **WHEN** logging emits
- **THEN** log MUST include all required field names
- **AND** `all_shop_nmids_count` MUST be 500
- **AND** `existing_covered_count` MUST be 120
- **AND** `uncovered_count` MUST be 380
- **AND** `coverage_status` MUST reflect COMPLETE or honest partial state from this tick's attempt

### Requirement: Latest-per-key read semantics

Downstream read-latest aggregation MUST use per `(nmid, date)` latest version
(argMax semantics).
Raw version sums MUST NOT be used.
Row count or pre-existing CH rows alone MUST NOT imply current-tick completeness.

#### Scenario: ReplacingMergeTree duplicate versions

- **GIVEN** two versions exist for the same `(nmid, date)`
- **WHEN** coverage is read for aggregation
- **THEN** the higher version row MUST be used
- **AND** metrics MUST NOT be summed across versions

### Requirement: Last-attempt coverage evidence

The system MUST persist minimal durable last-attempt evidence (Redis allowed)
recording scope, window, assortment proof, expected/returned/missing/rejected pair
counts, `attempt_status`, and partial reason from **this tick's** collection attempt.
Readers MUST NOT present stale preexisting CH rows as current complete after API/assortment failure.

The system MUST write `attempt_status=STARTED` with window and scope fields **before**
the first WB funnel API await of the tick. Cancellation, timeout, or mid-tick failure
MUST NOT leave a prior `COMPLETE` record falsely current. The system MUST NOT set
`attempt_status=COMPLETE` or claim success when CH insert failed for attempted nmIDs.

#### Scenario: STARTED before API prevents false COMPLETE

- **GIVEN** a prior tick left last-attempt evidence with `attempt_status=COMPLETE`
- **WHEN** a new tick begins and writes `attempt_status=STARTED` before the first funnel API call
- **AND** the tick is cancelled or times out before terminal evaluation
- **THEN** readers MUST NOT treat the prior `COMPLETE` as current-tick success
- **AND** in-flight evidence MUST reflect non-complete state (STARTED or terminal partial/failed)

#### Scenario: Failed CH insert prevents false success

- **GIVEN** API validation succeeds for nmID 42
- **WHEN** ClickHouse insert raises for nmID 42's batch
- **THEN** last-attempt evidence MUST NOT record `attempt_status=COMPLETE`
- **AND** `failed_count` MUST include nmID 42
- **AND** prior CH rows for nmID 42 MUST remain unchanged

#### Scenario: Partial API marks incomplete honestly

- **GIVEN** assortment pagination completes for |A|=500
- **AND** API returns incomplete date coverage for 20 expected pairs
- **WHEN** the tick finishes
- **THEN** Redis last-attempt evidence MUST record `missing_pair_count` > 0 and partial reason
- **AND** `coverage_status` MUST NOT be `COMPLETE`
- **AND** prior CH rows MUST remain but MUST NOT alone prove current completeness

### Requirement: Campaign and DRR boundary

This capability MUST NOT collect campaign advertising stats or open an
independent campaign funnel route.
Store DRR numerator MUST remain `BLOCKED_BY_CAMPAIGN_COVERAGE`.
Campaign boundary reconciliation with sibling change is **COMPLETE**
(`CAMPAIGN_CHANGE_RECONCILED=YES`).

#### Scenario: No full_adv_wb_stat writes

- **GIVEN** common-sales coordinator runs
- **WHEN** collection completes
- **THEN** no writes to campaign full advertising stat tables occur from this capability

### Requirement: Forbidden mutations

The system MUST NOT create AdvSetting rows, mutate `bot_active`, or perform WB
advertising write actions as part of shop-wide common-sales collection.

#### Scenario: Read-only WB side effects

- **GIVEN** shop-wide collection runs
- **WHEN** WB API calls are made
- **THEN** only read-only funnel/history and Content card list endpoints are used

### Requirement: History backfill deferred

Collecting factual history older than the 7 MSK-day rolling window is out of
scope.
The system MUST NOT fabricate daily history from period aggregates.

#### Scenario: No backfill beyond window

- **GIVEN** a date older than today−6 MSK
- **WHEN** runtime MVP runs
- **THEN** the coordinator MUST NOT target that date for collection

### Requirement: Isolated integration testing

Integration tests for CH write/read MUST run only against proven **task-owned**
dedicated local scratch ClickHouse fixtures. Ownership proof requires:
`validate_destructive_clickhouse_endpoint` (`tests/support/destructive_clickhouse.py`)
before client creation; database `test_adv_bot_clickhouse`; table `wb_common_stat`
listed in `CH_TEST_OWNED_TABLES` (`destructive_ch_reset.py`); opt-in
`ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1`; `@pytest.mark.destructive_local`.
Fixed localhost:8124 alone is **not** sufficient ownership proof.
Tests MUST NOT use shared or production CH resources. Destructive tests MUST NOT
run during planning-only close.

#### Scenario: Task-owned scratch CH endpoint proven

- **GIVEN** integration test for coverage read/write roundtrip
- **WHEN** the test module is authored (not executed at planning close)
- **THEN** it MUST call `validate_destructive_clickhouse_endpoint` before `get_async_client`
- **AND** MUST target `test_adv_bot_clickhouse.wb_common_stat` via test-owned DDL
- **AND** MUST use `@pytest.mark.destructive_local`
- **AND** MUST NOT connect to `default_db`, production, or shared CH endpoints
