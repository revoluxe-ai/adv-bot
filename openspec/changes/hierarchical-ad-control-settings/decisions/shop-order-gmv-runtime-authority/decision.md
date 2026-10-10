# Decision: shop-order-gmv-runtime-authority

## Status

Accepted (2026-10-10; change `hierarchical-ad-control-settings`, Task 4.1 blocker). Implementation: NO.

## Context

`openspec/decisions/shop-data-source-strategy/decision.md` left the generic shop product orders/sales source unassigned until a later specific decision.

`openspec/decisions/drr-cpo-price-semantics/decision.md` (Accepted 2026-10-09) resolves that family **only for V1 hierarchical shop DRR/CPO**: `whole_shop_order_gmv_rub` MUST come from `ORDERS_OR_SALES_REPORTS_READ` (statistics-api `GET /api/v1/supplier/orders`), per `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`.

That ADR does **not** name the monetary column, row grain, or runtime materialization. Evidence scripts disagree (`finishedPrice` first vs `totalPrice` → `priceWithDisc` → `finishedPrice`) and are not authority. Generated `OrdersItem` documents `totalPrice` (no discounts), `priceWithDisc` (seller discount including WB Club), `finishedPrice` (all discounts except WB Wallet). The model has no `quantity`. `srid` is the unique row id. `gNumber` is the buyer cart id. `date` is the order time (Moscow). `lastChangeDate` is the refresh/cursor time for `flag=0`. `isCancel` marks cancellation.

There is no production CH/PG table of supplier-order rows. `wb_common_stat` and campaign attribution are forbidden denominators.

## Decision

For V1 hierarchical `whole_shop_order_gmv_rub` only:

1. **Source:** `ORDERS_OR_SALES_REPORTS_READ` / `ReportsManager.get_supplier_orders`. Not funnel, not attribution, not buyout, not seller payout, not net margin.
2. **Monetary field:** `priceWithDisc` only. If a non-cancelled in-window row lacks `priceWithDisc`, the window fails closed. Do not substitute `totalPrice` or `finishedPrice`.
3. **Why this field:** seller-discounted order-line value including WB Club, excluding SPP and WB Wallet. `totalPrice` is pre-discount list value and inflates the DRR denominator. `finishedPrice` is SPP-inclusive and pre-wallet, which is the deferred customer-paid/SPP/wallet control basis in drr-cpo-price-semantics §11.
4. **Row grain:** one supplier-order API element = one order-line event.
5. **Order count:** one surviving row counts as one order-item. `gNumber` is cart grouping for diagnostics only, not the GMV grain.
6. **Quantity:** do not multiply. The generated contract has no quantity.
7. **Dedupe:** `srid` across cursor pages. Do not dedupe on `gNumber`.
8. **Cancellation:** exclude `isCancel=true`.
9. **Event date:** `date`, interpreted in Europe/Moscow. `lastChangeDate` is cursor/freshness only.
10. **Window completeness:** not proven by a non-empty body. Complete only when collection succeeded, cursor pagination ended naturally (empty tail or no next cursor), the run was not stopped by max pages, API budget, duplicate-page halt, or cursor stall, the first `dateFrom` is the requested window start, and the closed event window is comparable to the shop spend window. Filter included rows by MSK `date` inside that window.
11. **Freshness:** max observed `lastChangeDate` (and collect time) is a separate dimension. Freshness MUST NOT upgrade incomplete coverage to complete. Stale facts do not emit numeric shop DRR/headroom.
12. **Fail closed (no numeric shop DRR or headroom):** `SHOP_ORDER_GMV_INCOMPLETE`, `SHOP_ORDER_GMV_FIELD_ABSENT`, `SHOP_ORDER_GMV_STALE`, plus existing `REVENUE_BASIS_UNSUPPORTED` if a deferred or forbidden basis is requested.

## Task 4.1 V1 materialization

Task 4.1 V1 materialization is a **single** bounded live/read-through supplier-orders collection via `ReportsManager.get_supplier_orders`, **once per shop per evaluation window**, followed by shop-wide aggregation.

**Expected pipeline:**

1. one shop/window supplier-orders read
2. normalize / dedupe / filter (per Decision items 4–9)
3. whole-shop factual GMV aggregate (`whole_shop_order_gmv_rub`)
4. `ShopEconomicControlState`

**Hard invariant:** MUST NOT perform supplier-orders reads per campaign or per `nmID`.

Campaign economics continue to come from `AttributionFactsReader` and MUST NOT reuse supplier-order rows for campaign attribution.

The live read stays bounded by: API budget; pagination completeness; requested event window; explicit coverage; freshness; fail-closed reason codes.

If pagination or API budget cannot prove the requested window complete, emit `SHOP_ORDER_GMV_INCOMPLETE` and do not propose numeric shop DRR or headroom.

Implementation lifts multi-page read-through in the shop-runner read path (pagination out of scripts; not a single page). No new CH/PG table, no migration, and no durable supplier-order observation collector in Task 4.1. Durable supplier-order observation storage is deferred to a separate future change. `shop-wide-common-sales` / `wb_common_stat` remains forbidden as this denominator.

## Accepted row-grain evidence

Owner-accepted semantics (not pending):

| Key | Value |
|-----|-------|
| `ROW_GRAIN` | one API element = one order-line event |
| `ORDER_COUNT_SEMANTICS` | one surviving row = one order-item |
| `QUANTITY_SEMANTICS` | no multiplication |
| `DEDUPE_KEY` | `srid` |
| `CANCELLATION_RULE` | exclude `isCancel=true` |
| `EVENT_DATE_FIELD` | `date` |
| `CURSOR_FIELD` | `lastChangeDate` |

## Reconciliation

- shop-data-source-strategy remains the generic “source not yet assigned” rule for other shop product analytics.
- drr-cpo-price-semantics is the newer specific acceptance of the supplier-order family for this V1 control denominator.
- orders-or-sales-reports-read-identity is the transport identity (endpoint, cursor honesty). It does not choose `priceWithDisc`.
- This decision binds the column, grain, and read-completeness contract. It does not implement Task 4.1.

## Forbidden

- Fallback chains across price fields.
- Funnel `wb_common_stat` / `shop-wide-common-sales` / `orders_sum` as this denominator.
- Supplier-orders reads scoped per campaign or per `nmID` for shop GMV.
- Reusing supplier-order rows for campaign attribution (campaign economics stay on `AttributionFactsReader`).
- Campaign attribution sums as shop GMV.
- Durable supplier-order observation storage or a new CH/PG collector in Task 4.1.
- Treating `lastChangeDate` as the business order date.
- Treating a non-empty response as COMPLETE.
- Emitting numeric shop DRR or headroom when the GMV window is incomplete, the field is absent, or facts are stale.

## Related

- `openspec/decisions/shop-data-source-strategy/decision.md`
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
- `openspec/decisions/drr-cpo-price-semantics/decision.md`
