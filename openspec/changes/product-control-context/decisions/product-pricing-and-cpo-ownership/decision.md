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
3. **ProductCpoResolver** — Single pure owner of DRR→CPO math and **canonical domain
   money** at 0.01 RUB (ROUND_HALF_UP for both target and max).
4. **LegacyCampaignCpoAdapter** (Slice D) — Converts canonical `max_cpo_rub` to
   `AdvSetting.max_price_for_order` int via ROUND_HALF_UP; legacy int is not a domain
   invariant.
5. **No duplication** — Formula forbidden in Telegram, Excel, AI prompts, MCP, campaign
   handlers. Future JSON/API/MCP expose canonical 0.01 RUB values.
6. **Stale/unknown price** — Fail closed; no fabricated CPO; no silent fallback to
   historical average order value.
7. **Price source subdecision** — Concrete marketplace price field and multi-size
   aggregation remain **EVIDENCE_GAP** (script evidence is not accepted SoT).

### EVIDENCE_GAP (acceptance for runtime Slice D)

| Field | Current repository state |
|-------|-------------------------|
| CURRENT_PRICE_SOURCE | Candidate: WB Discounts & Prices `list/goods/filter` (script only); Content API cards in app **without** price DTO |
| CURRENT_PRICE_FIELD | Script explores `sizes[].discountedPrice` — **not** accepted canonical semantics |
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
