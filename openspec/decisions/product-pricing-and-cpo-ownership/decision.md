# Decision: product-pricing-and-cpo-ownership

## Status

Accepted (EVIDENCE_GAP: runtime current-price SoT)

## Context

DRR→CPO requires **current/effective product price**. Foundation delivered port
separation and pure `ProductCpoResolver` only. No production pricing adapter exists.

## Decision

1. **ProductPricingReader** — Sole port for `effective_product_price` in control.
   Runtime DRR-derived CPO remains blocked until adapter + Owner price semantics.
2. **ProductSalesEconomicsReader** — Historical analytics only; MUST NOT feed
   `ProductCpoResolver`.
3. **ProductCpoResolver** — Single pure owner of DRR→CPO math at 0.01 RUB
   ROUND_HALF_UP; fail closed on missing/non-positive price.
4. **LegacyCampaignCpoAdapter** — Future runtime only; maps canonical money to
   `AdvSetting` legacy int fields.
5. **No formula duplication** in Telegram, Excel, AI, MCP, campaign handlers.

### EVIDENCE_GAP (unchanged — `PRICE_SEMANTICS_ACCEPTED = NO`)

Concrete WB API field, multi-size aggregation, promo/SPP/Wallet semantics, and
staleness policy are **not** accepted. Script `a1_sale_price_snapshot.py` is
candidate evidence only.

## Applies to

- `app/modules/product_control/domain/product_cpo_resolver.py`
- `app/modules/product_control/application/ports/pricing.py`
- Future runtime change `product-control-shop-drr-runtime` (concept)

## Forbidden

- Using `wb_common_stat` orders_sum/orders as control price.
- Fabricating zero CPO when price is missing.

## Related specs

- `openspec/specs/product-control-context/spec.md`
