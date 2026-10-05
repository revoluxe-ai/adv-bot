# Shop-wide common-sales collection ownership

Status: accepted

Accepted: 2026-10-05 (evidence closure WB-SKY-COMMON-SALES-EVIDENCE-CLOSE-20261005-0250)  
Basis: Owner GO upload `20261004-215744` + independent planning PASS
`WB-SKY-COMMON-SALES-PLAN-FINAL-REVIEW-20261005-0135`. Identity and decision text
preserved; no scope expansion beyond reviewed Owner Contract and planning artifacts.

## Context

Shop-runner already writes campaign-scoped common-sales via `CommonSaleStatUpdater`
→ `WBDataManager.get_sales_funnel_products_history` → `ClickHouseCommonStatManager`
into `default_db.wb_common_stat` (ReplacingMergeTree keyed by `(nmid, date)`).

Sibling campaign change completed boundary reconciliation
(`COMMON_SALES_BOUNDARY_RECONCILIATION.md`, `CAMPAIGN_CHANGE_RECONCILED=YES`):
campaign owns discovery/inventory/`full_adv_wb_stat`; this change owns shop-wide
`(nmid, date)` expansion via the **existing** `update_common_sale_stat` coroutine.

Evidence (current code):

- Legacy collect entry: `CoroutinesManager.update_common_sale_stat` →
  `get_complex_advs(only_bot_active=False)` → `CommonSaleStatUpdater`.
- All-shop assortment authority MUST NOT be AdvSetting, sold IDs, or WBCard
  cabinet cache (WBCard loader lacks cabinet FK).
- Content API `ProductsManager.get_cards_list` excludes trash cards by API
  contract (documented in manager docstring).
- `NotFoundActiveAdvCompany` in `_get_advs` (`wb_shop_data_manager.py` L134–136)
  propagates to `while_coroutine_decorator` → `StopShopUpdateException`
  (`while_coroutines_decorator.py` L156–158), cancelling TaskGroup siblings.

## Decision

1. **Single coordinator** — expand the **existing**
   `CoroutinesManager.update_common_sale_stat` coroutine (same public signature,
   same WBShop TaskGroup registration) to orchestrate shop-wide collection.
   **No** second common-sales coroutine (`update_shop_wide_common_sale_stat`).
2. **One frozen snapshot per tick** — paginate A once; load ComplexAdv snapshot E
   once; derive U=A−E once; invoke shared updater on disjoint E and U routes
   (or dedup union with route attribution).
3. **Regular recollection** — every tick refresh **all** E and **all** U nmIDs over
   the 7 MSK-day window. CH argMax read-latest is aggregation/dedup only — never
   a skip gate for recollection.
4. **Legacy E semantics preserved** — E includes nmIDs absent from current A;
   E route retains Redis adv timestamp side effects; writer unchanged.
5. **Campaign sibling** retains exclusive ownership of campaign
   discovery/inventory and `full_adv_wb_stat` writes (`CAMPAIGN_CHANGE_RECONCILED=YES`).
6. **No-ad TaskGroup survival** — exhaustive `WBShop.run` TaskGroup registry
   (design.md §No-Campaign TaskGroup Survival); `taskgroup_no_ad_supervisor` at
   WBShop task factory wraps 18 loader-path coroutines; catches only
   `StopShopUpdateException` with direct cause `NotFoundActiveAdvCompany`;
   coordinator uses `_resolve_legacy_assigned_nmids` (NotFound → E=∅, exempt).
   Global `while_coroutine_decorator` policy unchanged. AST/membership guard required.
7. **Coverage evidence** — completeness from current tick API attempt +
   assortment pagination proof; minimal Redis last-attempt record. CH pre-existence
   alone MUST NOT imply current completeness.
8. **Counter semantics** — `existing_covered_count=|E|`, `uncovered_count=|U|`
   (SKU counts); pair diagnostics optional and separate.

## Applies to

- `app/modules/shop_runner/**` — coordinator body in `update_common_sale_stat`,
  `taskgroup_no_ad_supervisor` in `WBShop.run`, returned-fact validator
- `app/core/mp/wb/api/domain_managers/products/products_manager.py` (read)
- `app/modules/shop_runner/service_manager/services/common_sale_stat_updater/**`
- CH table `default_db.wb_common_stat` (existing DDL only)

## Allowed

- Paginated Content API reads for A with fail-explicit null/partial handling.
- Bounded seam: `_resolve_legacy_assigned_nmids` catches `NotFoundActiveAdvCompany`
  only inside coordinator → E=∅.
- Bounded seam: `taskgroup_no_ad_supervisor` at `WBShop.run` task factory on
  registry-listed loader-path coroutines — NotFound-caused StopShopUpdateException
  → bounded sleep+restart same factory; no TaskGroup sibling cancel.
- Returned-fact validation before CH insert; `attempt_status=STARTED` before funnel API.
- Extend `CommonSaleStatUpdater.update_last_week_stats` with explicit
  `nmids: list[int]` while preserving ComplexAdv-based E route.
- Redis keys for last-attempt evidence and transition hashes; TTL ≥ 2× tick interval.
- Read-only CH argMax queries for downstream aggregation (not recollection gating).

## Forbidden

- Second common-sales coroutine or parallel legacy funnel executor.
- AdvSetting / ComplexAdv / sold IDs / WBCard cache as all-shop assortment SoT.
- New `wb_common_stat`-like table or repurposing `SHOP_PRODUCT_ORDERS_SALES`.
- Deleting historical CH rows on ad↔non-ad transitions.
- Writing zero for missing/partial API/CH gaps.
- Skipping recollection because CH rows already exist.
- Second collector process or campaign funnel duplicate route.
- AdvSetting create, `bot_active` mutation, WB advertising writes.
- Global weakening of `while_coroutine_decorator` NotFound handling.
- Claiming full Store DRR or unblocking numerator (`BLOCKED_BY_CAMPAIGN_COVERAGE`).

## Examples

- Shop |A|=500, |E|=120, |U|=380: single coordinator tick calls updater for 120 E
  nmIDs and 380 U nmIDs (disjoint); union of writes has no duplicate nmID same tick.
- nmID in E but not in A: E route still attempts collect; full-shop qualification
  uses current A only.
- No campaigns: E=∅ via coordinator seam; U=A; supervised siblings do not cancel
  TaskGroup; coordinator completes U collect.
- Every tick: all E and U nmIDs re-fetched over 7 MSK days even if CH already has rows.

## Related specs

- `openspec/changes/shop-wide-common-sales-collection/specs/shop-wide-common-sales-collection/spec.md`

## Related changes

- Sibling reconciled: `shop-wide-campaign-data-collection` /
  `COMMON_SALES_BOUNDARY_RECONCILIATION.md` (`CAMPAIGN_CHANGE_RECONCILED=YES`).
- Prerequisite satisfied: archived `clickhouse-migrations-control-plane`
  unblocked shop-wide CH expansion.

## Review checklist

- [ ] Single coordinator inside existing `update_common_sale_stat` (no second coroutine)
- [ ] One frozen A/E/U partition per tick
- [ ] Regular full E+U recollection every tick
- [ ] Legacy assigned input preserved including E∖A
- [ ] Exhaustive TaskGroup registry + task factory supervisor (18 members); coordinator E=∅ seam exempt; auth/other-stop preserved; AST guard
- [ ] Invalid/conflicting fact rejection; STARTED before API; no false COMPLETE on CH failure
- [ ] CH DDL unchanged; writer path reused
- [ ] Last-attempt Redis evidence; CH argMax not used as skip gate
- [ ] Counter semantics |E|/|U| SKU counts
- [ ] Logs include required counters without secrets
