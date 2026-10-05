# Scenario Coverage Plan

CHANGE_ID: shop-wide-common-sales-collection
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-shop-wide-common-sales-20261005-close
LIFECYCLE_STATUS: DERIVED
SUPERSEDES: SCPV1-shop-wide-common-sales-20261005-repair

This is required-evidence planning only. It does not claim that any listed
test has been authored, executed, or passed.

## Lifecycle coverage

`design.md` Derived Lifecycle L1–L8:

- L1 Tick/window → S10
- L2 Discover A → S01, S01b, S01c
- L3 Resolve E → S02, S04, S04b, S04c, S04d, S04e
- L4 Partition → S03, S03b
- L5 Collect E+U regular refresh → S06, S06b, S06c, S07–S07f, S08, S08b
- L6 Last-attempt completeness → S11, S11b, S11c
- L7 Logs + Redis → S05, S05b, S10
- L8 Failure retain → S08, S08b

LIFECYCLE_COVERAGE:

- L1 → S10 — covered
- L2 → S01, S01b, S01c — covered
- L3 → S02, S04, S04b, S04c, S04d, S04e — covered
- L4 → S03, S03b — covered
- L5 → S06, S06b, S06c, S07–S07f, S08, S08b — covered
- L6 → S11, S11b, S11c — covered
- L7 → S05, S05b, S10 — covered
- L8 → S08, S08b — covered

No `MISSING_STEADY_STATE_RECONCILE_SCENARIO` gap planned (transition S05/S05b covers recompute).

## Architecture and evidence constraints

Architecture Decision References:

- `openspec/changes/shop-wide-common-sales-collection/decisions/shop-wide-common-sales-ownership/decision.md`

Ownership & Placement:

- **Single** `CoroutinesManager.update_common_sale_stat` coordinator (no second coroutine).
- Disjoint E/U routes via shared `CommonSaleStatUpdater`.
- `taskgroup_no_ad_supervisor` at `WBShop.run` task factory (18 registry members).
- ClickHouseCommonStatManager remains sole wb_common_stat writer.
- ProductsManager read-only for A; no campaign funnel duplicate.

Shared evidence rules:

- Scenario tests MUST reach coordinator (`update_common_sale_stat` body) or `WBShop.run` TaskGroup seam.
- WB API and CH may stub only after business partition/collect logic executes.
- 500/120/380 matrix tests MUST spy actual `get_sales_funnel_products_history` calls.
- CH integration MUST prove task-owned endpoint via `validate_destructive_clickhouse_endpoint` + `test_adv_bot_clickhouse` + `CH_TEST_OWNED_TABLES`; not run at planning close.
- Forbidden: mocking partition logic under test; patching writer to skip coverage proof; prod/shared CH; port 8124 alone as ownership proof.

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: shop-wide-common-sales-collection
SOURCE_SPEC_SHA: see plan.receipt.json INPUTS.SPEC_REVISION
PLAN_STATUS: ready

### S01 — Complete assortment pagination

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Complete pagination builds A
- TYPE: unit
- SCENARIO_SEAM: ShopAssortmentReader.paginate_all_nmids
- STUB_POLICY: WB Content API client returns 5 pages; assert |A|=500, no duplicates, pagination proof
- PAIRED_NEGATIVE: S01b partial variant

### S01b — Partial pagination fails closed

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Partial pagination fails closed
- TYPE: unit
- SCENARIO_SEAM: ShopAssortmentReader + coordinator tick
- ASSERT: PARTIAL_ASSORTMENT, legacy E route if E resolved, no invented U

### S01c — Terminal empty page after five full pages

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Terminal pagination boundary at exactly five full pages
- TYPE: unit
- SCENARIO_SEAM: ShopAssortmentReader.paginate_all_nmids
- STUB_POLICY: pages 1–5 full (100 each), page 6 empty cursor; |A|=500; terminal evidence recorded

### S02 — Legacy E and E∖A

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::E includes nmIDs absent from current A
- TYPE: unit
- SCENARIO_SEAM: coordinator E route input builder
- STUB_POLICY: ComplexAdv includes nmID 999 not in A

### S03 — Partition 500/120/380 disjoint

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Standard partition 500 A, 120 E, 380 U
- TYPE: unit
- SCENARIO_SEAM: coordinator partition with fixture sets
- ASSERT: |U|=380, U∩E=∅, disjoint collect lists

### S03b — Single frozen E snapshot

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Single coordinator frozen snapshot
- TYPE: unit
- SCENARIO_SEAM: coordinator tick
- ASSERT: get_complex_advs called once; U=A−E from that snapshot

### S04 — No campaigns coordinator E empty

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::No campaigns yields empty E in coordinator path
- TYPE: unit
- SCENARIO_SEAM: `_resolve_legacy_assigned_nmids`
- ASSERT: E=∅, U=A, NotFound not propagated to decorator

### S04b — TaskGroup survives no-campaign siblings

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::TaskGroup survives no-campaign sibling coroutines
- TYPE: unit
- SCENARIO_SEAM: `WBShop.run()` TaskGroup with task-factory-wrapped mocks
- ASSERT: coordinator tick completes; sibling e.g. refresh_stats_freshness_cache NotFound does not cancel group

### S04c — Auth errors still cancel

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Auth errors still cancel shop
- TYPE: unit
- SCENARIO_SEAM: wrapped coroutine + WBShop.run
- ASSERT: ApiForbiddenError propagates; not swallowed by supervisor

### S04d — TaskGroup registry AST membership guard

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::TaskGroup registry AST membership guard
- TYPE: unit
- SCENARIO_SEAM: AST parse `wb_shop.py` WBShop.run create_task registrations
- ASSERT: set equals design.md exhaustive registry; supervisor subset = 18 loader paths; coordinator exempt

### S04e — Other StopShopUpdateException not swallowed

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Other StopShopUpdateException causes not swallowed
- TYPE: unit
- SCENARIO_SEAM: taskgroup_no_ad_supervisor wrapper
- ASSERT: StopShopUpdateException with non-NotFound cause propagates

### S05 — Ad transition non-ad to ad

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::SKU moves from non-ad to ad
- TYPE: unit
- SCENARIO_SEAM: two sequential coordinator ticks
- ASSERT: nmID moves U→E; no CH DELETE

### S05b — Ad transition ad to non-ad

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::SKU moves from ad to non-ad
- TYPE: unit
- SCENARIO_SEAM: two sequential coordinator ticks
- ASSERT: nmID moves E→U

### S06 — Full partition batch 20 actual collector calls

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Full partition uses batch 20 on E and U routes
- TYPE: unit
- SCENARIO_SEAM: CommonSaleStatUpdater.update_last_week_stats(nmids=...) and ComplexAdv path
- ASSERT: spy on get_sales_funnel_products_history; await_count = ceil(120/20)+ceil(380/20) for full E+U tick

### S06b — Regular refresh despite existing CH

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Regular refresh despite existing CH rows
- TYPE: unit
- SCENARIO_SEAM: coordinator tick with CH pre-populated mock
- ASSERT: collector still invoked for nmID

### S06c — U-route remainder batch boundary (25 nmIDs only)

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::U-route remainder batch boundary
- TYPE: unit
- SCENARIO_SEAM: U route only with 25-nmID fixture (not |U|=380 same tick)
- ASSERT: 2 collector calls (20+5)

### S07 — Missing date not zero

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::API returns no history for a date
- TYPE: unit
- SCENARIO_SEAM: DTO mapping + last-attempt evidence
- ASSERT: pair not returned-complete; no zero insert

### S07b — Unexpected nmid rejected

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Unexpected nmid rejected
- TYPE: unit
- SCENARIO_SEAM: returned-fact validator
- ASSERT: no insert for out-of-set nmid

### S07c — Out-of-window date rejected

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Out-of-window date rejected
- TYPE: unit
- SCENARIO_SEAM: returned-fact validator
- ASSERT: pair rejected; not returned-complete

### S07d — Conflicting duplicate rejected

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Conflicting duplicate key rejected
- TYPE: unit
- SCENARIO_SEAM: returned-fact validator
- ASSERT: neither row inserted; coverage not COMPLETE

### S07e — Identical duplicate deduplicated

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Identical duplicate deduplicated
- TYPE: unit
- SCENARIO_SEAM: returned-fact validator
- ASSERT: exactly one insert; stable order

### S07f — Non-finite metric rejected

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Non-finite required metric rejected
- TYPE: unit
- SCENARIO_SEAM: returned-fact validator
- ASSERT: no zero-fill substitute

### S08 — Failure retains facts

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Failure retains old facts
- TYPE: unit
- SCENARIO_SEAM: coordinator tick with insert exception
- ASSERT: failed_count>0; prior rows untouched

### S08b — Mid-batch partial failure

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Mid-batch WB failure
- TYPE: unit
- SCENARIO_SEAM: coordinator batch collect
- ASSERT: partial success; failed_count=5 for 5 failures

### S09 — argMax latest dedup

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::ReplacingMergeTree duplicate versions
- TYPE: unit + integration
- SCENARIO_SEAM: argMax read helper / integration roundtrip
- ASSERT: higher version wins; no cross-version sum

### S10 — Required tick log counter semantics

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Successful tick log fields
- TYPE: unit
- SCENARIO_SEAM: coordinator successful tick
- ASSERT: all_shop_nmids_count=500, existing_covered_count=120, uncovered_count=380

### S11 — Last-attempt Redis evidence

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Partial API marks incomplete honestly
- TYPE: unit
- SCENARIO_SEAM: coordinator tick + Redis writer
- ASSERT: missing_pair_count>0; coverage_status≠COMPLETE

### S11b — STARTED before API

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::STARTED before API prevents false COMPLETE
- TYPE: unit
- SCENARIO_SEAM: coordinator tick + Redis writer timing
- ASSERT: STARTED before first funnel await; cancel/timeout does not leave prior COMPLETE current

### S11c — Failed CH insert no false success

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Failed CH insert prevents false success
- TYPE: unit
- SCENARIO_SEAM: coordinator tick with insert exception after validation
- ASSERT: attempt_status≠COMPLETE; failed_count includes nmID

### S12 — CH write/read integration (task-owned scratch only)

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Task-owned scratch CH endpoint proven
- TYPE: integration (`destructive_local`)
- SCENARIO_SEAM: validate_destructive_clickhouse_endpoint + ClickHouseCommonStatManager.insert + argMax read
- FIXTURE: test_adv_bot_clickhouse.wb_common_stat via destructive_ch_reset DDL; ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
- NOTE: authored only; not executed at planning close

### S13 — No AdvSetting mutation

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::Read-only WB side effects
- TYPE: unit
- SCENARIO_SEAM: full coordinator tick
- ASSERT: no AdvSetting create/update; no bot_active writes

### S14 — No full_adv_wb_stat

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::No full_adv_wb_stat writes
- TYPE: unit
- SCENARIO_SEAM: coordinator tick
- ASSERT: full_wb_adv_stat.insert not called

### S15 — No second coroutine

- SCENARIO_ID: specs/shop-wide-common-sales-collection/spec.md::No second coroutine registration
- TYPE: unit
- SCENARIO_SEAM: WBShop.run task registration inspection
- ASSERT: exactly one common-sales coroutine; no update_shop_wide_common_sale_stat

### Legacy regression

- EXISTING: tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py
- POLICY: MUST remain passing after updater extension (ComplexAdv path unchanged)

## Test commands (planning reference)

```powershell
poetry run pytest -m unit tests/modules/shop_runner/service_manager/test_shop_wide_common_sale_stat_coordinator.py -v
poetry run pytest -m unit tests/modules/shop_runner/service_manager/test_common_sale_stat_updater.py -v
poetry run pytest -m "integration and destructive_local" tests/integration/test_shop_wide_common_sale_stat_coverage.py -v
```

## OPEN_QUESTIONS

None — Owner decisions fixed for MVP scope; planning repair P-001/P-002 closed in WB-SKY-COMMON-SALES-PLAN-CLOSE-20261005-0130.
