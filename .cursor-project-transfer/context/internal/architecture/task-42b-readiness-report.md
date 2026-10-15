---
cursor:
  subagentId: "bc-67d4fbe8-cec9-58ce-8d2e-648423dff71f"
---

# Task 4.2B readiness report (read-only, no code)

Stage: `0691bf4574473164c18b4a471fb5bbb5e64258ad` (merge PR #479). 4.2A (PR #477) is an ancestor. Tasks: 4.1 `[x]`, 4.2 `[ ]` (stays open).

## 4.1 ports on stage

`app/modules/ad_control_settings/runtime/`:
- `ports.py`: `SupplierOrdersPagePort`, `ShopAdvIdPort`, `ShopSpendPort`, `AttributionQueryPort`, `ResolverContextSource` (protocol only, no implementation).
- `providers.py`: `HistoryThenInventoryAdvIds` (CH `campaign_settings_history` / `shop_campaign_inventory`), `FullAdvShopSpend` (CH `full_adv_wb_stat`), `ReportsManagerOrdersAdapter` (WB statistics-api supplier orders, read).
- `supplier_orders_collect.py` (up to 200 pages / API budget 200), `shop_order_gmv.py`, `shop_factual.py`, `campaign_order_value.py`, `money.py`.
- `evaluation.py`: `evaluate_shop_window(ShopEvaluationRequest, orders=, spend=, attribution=) -> ShopEvaluationResult(reports, gmv, shop, supplier_order_collections, reason_codes)`.
- Integration: `app/modules/shop_runner/hierarchical_ad_control_diagnostics.py::run_enabled_shop_diagnostics`, called hourly from `shop_runner/service_manager/manager.py`, gated by `HIERARCHICAL_AD_CONTROL_DIAGNOSTICS_ENABLED` (default off, commented in `env.sample`). Window: last 7 closed Moscow days. Enrolled iff shop `DRR_POLICY` is ENABLED with payload (a local predicate, not a stored enrollment).

## Critical finding

The result of `run_enabled_shop_diagnostics` is only logged (`_log`) and discarded. Nothing persists it, and nothing in `app/` reads it. A Telegram handler therefore has no source for economic facts today. Calling `evaluate_shop_window` from a handler would run up to 200 WB API pages plus CH reads per tap. That violates the packet rule "No WB API on list or diagnostics read".

## Available vs missing (AdControlDiagnosticsBuilder / ReportV1 / runtime)

Available in `AdControlDiagnosticsReportV1` (from runtime, in memory only):
- configured target DRR; shop `actual_drr` (percent, `measurement_window_id`, `data_sufficiency`; `attribution_lag_days` is always None);
- `shop_effective_control_drr`, `campaign_effective_control_drr`;
- `shop_headroom` (from `allowed_spend_rub` and `spend_rub`);
- `campaign_observed_drr` (DIRECT spend / DIRECT GMV, separate from shop);
- `proposed_cpo` (order-value target CPO, decision `DIAGNOSTIC_ORDER_VALUE_TARGET_CPO` or `NO_PROPOSAL_ORDER_VALUE_BLOCKED`);
- blockers, reason codes, provenance, decision.
- Shop level on `ShopEvaluationResult`: `gmv` (status, whole_shop_order_gmv, window, pages), `shop` (actual DRR, allowed, spend, headroom, GMV, sufficiency, reasons).

Still missing:
1. No persisted or serialized snapshot, and no read port for the UI (blocking).
2. DIRECT GMV, DIRECT orders and expected order value are computed in `CampaignOrderValue` and then dropped; they are not on the report or the result.
3. `CampaignHeadroomEligibility` is still not on the report (builder merges its reasons and drops the struct).
4. No `collected_at` or freshness timestamp on the report or result.
5. `current_max_cpo_rub` is never supplied (always None).
6. The result carries no per-campaign sufficiency beyond `campaign_observed_drr` presence. `dry_run_diff_available` is always False.
7. Enrollment: no stored enrollment. UI 4.2A hardcodes `NOT_ENROLLED`, while runtime treats the shop as enrolled when `DRR_POLICY` is enabled. They disagree, so UI effective policy can show blocked while runtime computes values.
8. `product_drr` is not passed in either path.
9. "actionable" still has no domain symbol.
10. Pre-existing: runtime does N+1 `load_campaign_slots` per campaign (hourly, acceptable). Campaigns come from history-first, then inventory.

## Proposed minimal 4.2B slice (needs GO)

Goal: show last runtime diagnostics, labeled with age, with no live WB/CH calls and no writes to PG authority or WB.

- 4.2B-0, runtime/domain additive exposure, no new formulas:
  - add `CampaignEconomicsRow` (advert_id, direct_gmv, direct_orders, expected_order_value, target_cpo, campaign_actual_drr, reason codes) and `collected_at` + `window` to `ShopEvaluationResult`, from values already computed;
  - add optional `campaign_headroom_eligibility: ... | None = None` to the report, set by the builder from the same call it already makes.
  - Touches 4.1 modules: needs your explicit OK.
- 4.2B-1, snapshot channel (decision needed):
  - versioned JSON DTO `AdControlDiagnosticsSnapshotV1` (Decimal as string, schema_version, collected_at, window, enrolled flag, shop block, campaign rows);
  - written by the shop-runner hook, read by UI through a small `SnapshotReader` port.
  - Recommended store: Redis with TTL ~3h (derived cache, no migration, no authority data, tick is hourly). Alternatives: PG table (migration) or CH table.
  - UI treats a missing or expired snapshot as "diagnostics unavailable", never as zero or OK.
- 4.2B-2, UI read-only on 4.2A surface:
  - shop screen: actual DRR, allowed/spend/headroom, window, sufficiency, snapshot age, status, blockers and reasons, provenance;
  - campaign detail: DIRECT GMV/orders, expected order value, target CPO proposal (labelled diagnostic), campaign DRR labelled DIRECT, eligibility, reasons;
  - list rows: status chip only (no sort or filter);
  - replace hardcoded `NOT_ENROLLED` with the shared enrollment predicate extracted from the runtime hook, or the snapshot flag (decision).
  - Relax the 4.2A banned-symbol scan to allow read-only domain DTO types and keep `apply_*`, `ApplyAuthority`, `wb_manager`, `clear_campaign_feature` and WB clients banned.
- Out of 4.2B: allocator (4.3), Apply, bulk ops, blocked-first sort or filters, live evaluation from handlers.
- Tests: snapshot codec round-trip, missing/expired/stale snapshot fail-closed, each field maps to its source (no UI arithmetic), enrollment predicate parity, no WB/CH/apply calls from UI (scan), existing 4.2A tests, pyright-strict.
- Execution: composer-2.5 for codec, formatters, tests. I do the domain/runtime exposure and review myself.

## Decisions needed for GO

1. Snapshot store: Redis TTL (recommended) vs PG vs CH.
2. OK to edit 4.1 runtime/shop_runner hook and add one optional report field.
3. Enrollment source: shared predicate (recommended) vs snapshot flag.
4. Keep scope to shop screen + campaign detail + list chip, with sort and filter deferred.
