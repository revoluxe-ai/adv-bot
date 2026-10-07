# Decision: product-pricing-and-cpo-ownership

## Status

Proposed (EVIDENCE_GAP: runtime current-price SoT)

## Context

Owner DRR→CPO rule requires **current/effective product price**. Repository has
historical funnel stats in `wb_common_stat` and campaign-configured CPO on
`AdvSetting`, but no `app/` module that authoritative reads marketplace sale price
for control. Read-only script `scripts/a1_sale_price_snapshot.py` documents Discounts
& Prices API `discountedPrice` parsing — not production runtime.

## Decision

1. **ProductPricingReader** — Sole entry for `effective_product_price` used by control.
   Until implemented and accepted, DRR-derived CPO in runtime is
   **`BLOCKED_BY_PRODUCT_PRICE_SOURCE`** (domain foundation still allowed).
2. **ProductSalesEconomicsReader** — Historical orders/GMV/revenue-per-order; MAY use
   `wb_common_stat`. MUST NOT feed `ProductCpoResolver`.
3. **ProductCpoResolver** — Single pure owner of DRR→CPO:
   - `target_cpo_rub = effective_product_price × target_drr_percent / 100`
   - `max_cpo_rub = effective_product_price × max_drr_percent / 100`
   - Rounding: target → 0.01 RUB half-up; max → integer RUB half-up (align
     `max_price_for_order` int).
4. **No duplication** — Formula forbidden in Telegram, Excel, AI prompts, MCP, campaign
   handlers.
5. **Stale/unknown price** — Fail closed; no fabricated CPO; no silent fallback to
   historical average order value.

### EVIDENCE_GAP (acceptance for runtime Slice D)

| Field | Current repository state |
|-------|-------------------------|
| CURRENT_PRICE_SOURCE | Candidate: WB Discounts & Prices `list/goods/filter` (script only); Content API cards in app **without** price DTO |
| CURRENT_PRICE_FIELD | Script uses `sizes[].discountedPrice`; `SALE_PRICE_REFERENCE = min(discountedPrice)` across sizes when multi-size |
| PRICE_SCOPE | Per `(shop_id, nmid)` via seller API credentials for cabinet |
| PRICE_UPDATE_FREQUENCY | Not defined in runtime; script is on-demand |
| PROMO_DISCOUNT_SEMANTICS | `discountedPrice` vs `clubDiscountedPrice` — script collects club but **does not** use as reference |
| STALE_PRICE_BEHAVIOR | **Undefined in app/** — resolver MUST treat missing/stale per explicit policy in Slice D design |

## Applies to

- `ProductCpoResolver`, `ProductPricingReader` implementations
- Shop-runner enrolled adapter (Slice D)
- AI `ProductControlContextV1.pricing_evidence`

## Allowed

- Implement pricing reader wrapping existing `app/core/mp/wb/api` client after Owner
  confirms effective price definition (incl. multi-size aggregation).

## Forbidden

- Using `orders_sum / orders` from `wb_common_stat` as control price.
- Duplicating CPO formula outside `ProductCpoResolver`.
- Defaulting missing price to `0` or legacy `target_price_for_order`.

## Examples

Good: enrolled SKU, price OK → resolver returns derived CPO → adapter writes runtime view.

Bad: no price → adapter copies yesterday's `orders_sum/orders` into CPO.

## Related specs

- `openspec/changes/product-control-context/specs/product-control-context/spec.md`

## Related changes

- `product-control-context`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed
- [x] implementation layer matches decision
