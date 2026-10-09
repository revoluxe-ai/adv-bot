# Decision: product-pricing-and-cpo-ownership

## Status

Accepted (EVIDENCE_GAP: runtime **catalog/current** product price SoT for the
price-based product control path)

## Context

Product-oriented control needs a **price-based** DRR→CPO path: effective catalog
(or current) unit price × `DrrProfile` percents. Foundation delivered port
separation and pure `ProductCpoResolver` for that path only. No production
pricing adapter exists.

**V1 hierarchical campaign** economic targets (`TARGET_CPO_RUB` from DIRECT
attributed order value × effective target DRR) are **not** owned here. Authority:
`openspec/decisions/drr-cpo-price-semantics/decision.md`
(`PRICE_SEMANTICS_ACCEPTED = YES`, `PRICE_SEMANTICS_QUALIFIER = V1_ORDER_VALUE_BASIS`).

Readers MUST NOT treat this decision as universal DRR→CPO ownership.

## Decision

### Path A — Price-based product control (this decision)

1. **ProductPricingReader** — Sole port for `effective_product_price` on this path.
   Runtime price-based DRR-derived CPO remains blocked until adapter +
   **catalog/current price** semantics are accepted.
2. **ProductSalesEconomicsReader** — Historical analytics only; MUST NOT feed
   `ProductCpoResolver`.
3. **ProductCpoResolver** — Single pure owner of **price-based** DRR→CPO math
   (`effective_product_price_rub × DrrProfile% / 100`) at 0.01 RUB ROUND_HALF_UP;
   fail closed on missing/non-positive price. **Not** authority for V1
   hierarchical campaign `TARGET_CPO_RUB`.
4. **LegacyCampaignCpoAdapter** — Future runtime only; maps canonical money to
   `AdvSetting` legacy int fields (when explicitly wired; not V1 order-value path).
5. **No formula duplication** in Telegram, Excel, AI, MCP, campaign handlers for
   the price-based path.

### Path B — V1 hierarchical campaign control (separate ADR)

```text
DIRECT attributed order value × effective target DRR → TARGET_CPO_RUB
```

Authority: `openspec/decisions/drr-cpo-price-semantics/decision.md`.

`ProductPricingReader`, `EffectiveProductPrice`, and `ProductCpoResolver` MUST NOT
substitute for Path B. Legacy `AdvSetting` / V3 runtime remains separate legacy
behavior pending migration.

### Catalog price semantics (scoped evidence gap)

```text
CATALOG_PRICE_SEMANTICS_ACCEPTED = NO
```

Concrete WB API field, multi-size aggregation, promo/SPP/Wallet semantics, and
staleness policy for **catalog/current product price** are **not** accepted.
Script `a1_sale_price_snapshot.py` is candidate evidence only.

**Do not** read this as revoking order-value acceptance:

```text
PRICE_SEMANTICS_ACCEPTED = YES
PRICE_SEMANTICS_QUALIFIER = V1_ORDER_VALUE_BASIS
```

(defined only in `drr-cpo-price-semantics` for Path B).

## Applies to

- `app/modules/product_control/domain/product_cpo_resolver.py`
- `app/modules/product_control/application/ports/pricing.py`
- Future runtime change for **price-based** product control (concept)

## Forbidden

- Using `wb_common_stat` orders_sum/orders as control price on Path A.
- Fabricating zero CPO when price is missing on Path A.
- Treating `ProductCpoResolver` as authority for V1 hierarchical campaign
  `TARGET_CPO_RUB` (Path B).
- Unqualified `PRICE_SEMANTICS_ACCEPTED = NO` without scoping to catalog price
  (use `CATALOG_PRICE_SEMANTICS_ACCEPTED = NO` for Path A gaps).

## Related specs

- `openspec/specs/product-control-context/spec.md`

## Related decisions

- `openspec/decisions/drr-cpo-price-semantics/decision.md` — V1 order-value
  campaign semantics (Path B)
