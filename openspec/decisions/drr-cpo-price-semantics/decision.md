# Decision: drr-cpo-price-semantics

## Status

**Accepted** (Owner V1, 2026-10-09)

```text
PRICE_SEMANTICS_ACCEPTED = YES
PRICE_SEMANTICS_QUALIFIER = V1_ORDER_VALUE_BASIS
ORDER_VALUE_SEMANTICS_ACCEPTED = YES
```

This acceptance covers **only** order-value semantics in §3–§6. It does **not**
implement runtime code, adapters, or production actuation.

## Context

WB Sky must convert **configured target DRR policy** and **scope-specific observed
DRR** into **bounded campaign CPO proposals** for the V1 hierarchical headroom
controller (`hierarchical-ad-control-settings` Slice A at parent commit
`065509c111e96aff88255db479001b9c3da3a0d0`, present on branch ancestry).

Prior drafts incorrectly treated **catalog/list/current product price** as the
required economic authority for V1 campaign CPO. Owner correction: V1 campaign
control uses **factual attributed order value**, not `ProductPricingReader`.

Accepted foundations remain in force:

- `attribution-facts-contract` — DIRECT/LINKED facts, spend join, coverage gates
- `product-control-context` — `DrrProfile` policy percents, inheritance
- `product-pricing-and-cpo-ownership` — **catalog price × DRR** path for
  `ProductCpoResolver` (unchanged; still blocked without price adapter)
- `orders-or-sales-reports-read-identity` — identity of whole-shop order ledger reads
- `shop-wide-common-sales-ownership` — funnel collection; **not** V1 shop DRR denominator

## Decision

### 1. V1 campaign economic authority (order value, not catalog price)

V1 campaign DRR→CPO control **MUST NOT** require catalog/list/current product
price as canonical economic authority.

**Remove `EFFECTIVE_CONTROL_PRICE` from the required V1 campaign CPO control path.**

`ProductPricingReader` / `EffectiveProductPrice` **MAY** remain for:

- diagnostics;
- future cold-start assistance;
- future **price-based** product-control semantics (`ProductCpoResolver` path).

They are **NOT** required authority for V1 hierarchical **campaign** CPO control.

**Canonical V1 economic input:**

```text
EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB
  = DIRECT_ATTRIBUTED_ORDER_GMV_RUB / DIRECT_ATTRIBUTED_ORDERS
```

for the accepted observation window, subject to deterministic
freshness / sufficiency / completeness gates (§9).

### 2. Campaign actual DRR (V1)

```text
campaign_actual_drr
  = campaign_ad_spend_rub / DIRECT_ATTRIBUTED_ORDER_GMV_RUB
```

- **Numerator:** authoritative campaign-day ad spend (`full_adv_wb_stat` / same
  join rules as `attribution-facts-contract`).
- **Denominator:** sum of **DIRECT** `attributed_gmv_rub` only (promotion fullstats
  `sum_price` grain).
- **LINKED:** diagnostic / observable only; **MUST NOT** drive V1 CPO authority.
- **MUST NOT** combine DIRECT + LINKED for CPO authority until a future explicit
  deduplication / marginal-value decision.

Aligns with `DRR_FACT_DIRECT` when coverage is `COMPLETE` and reconciliation PASS.

### 3. Shop actual DRR (V1)

Shop actual DRR is **not** shop-attributed GMV and **not** reconstructed from
advertised campaigns.

```text
shop_actual_drr
  = total_shop_ad_spend_rub / whole_shop_order_gmv_rub
```

for the **same measurement window** as shop headroom evaluation.

**`whole_shop_order_gmv_rub` MUST** come from the canonical **whole-shop order
factual** source (`ORDERS_OR_SALES_REPORTS_READ` — statistics-api supplier orders
per `orders-or-sales-reports-read-identity`), aggregated at shop scope.

- Exclude cancelled orders where the canonical factual row exposes cancellation.
- **V1 MUST NOT** use buyout / net-margin / seller payout as denominator.
- **V1 MUST NOT** use `wb_common_stat` / sales-funnel `orders_sum` as the shop
  DRR denominator (card funnel ≠ whole-shop order ledger).

**Policy vs observed basis:** `DrrProfile` target/max **percent** MAY inherit from
shop to campaign (product-control inheritance). **Observed** DRR metrics remain
**scope-specific** (shop ORDER_GMV vs campaign DIRECT attributed GMV).

### 4. DRR policy → target CPO (V1)

```text
expected_attributed_order_value_rub
  = Σ DIRECT attributed_gmv_rub / Σ DIRECT attributed_orders

effective_target_drr_fraction
  = effective_target_drr_percent / 100

target_cpo_rub
  = expected_attributed_order_value_rub × effective_target_drr_fraction
```

- Quantize money at **0.01 RUB ROUND_HALF_UP** when mapping to actuation fields
  (consistent with `ProductCpoResolver` money quant).
- This is the **accepted V1 economic target** for hierarchical campaign control.
- It is **NOT**: WB bid, CPC, CPM, catalog `price × DRR%`, or seller net-margin target.
- Controllers **MAY** derive `max_cpo_rub` as a bounded safety ceiling above
  `target_cpo_rub` (algorithm separate; not fixed in this ADR).

### 5. Shop headroom (V1) — units and sign

```text
configured_shop_target_drr_fraction = configured_shop_target_drr_percent / 100

allowed_shop_ad_spend_rub
  = whole_shop_order_gmv_rub × configured_shop_target_drr_fraction

shop_headroom_rub
  = allowed_shop_ad_spend_rub − actual_shop_ad_spend_rub
```

Interpretation (all amounts in **RUB**):

| Sign | Meaning |
|------|---------|
| `> 0` | Economic spend capacity exists under configured shop DRR |
| `= 0` | At target spend-ratio boundary |
| `< 0` | Shop exceeds configured spend ratio |

Headroom **does not** prescribe equal CPO increases across campaigns. Allocation /
ranking is a **separate** controller decision (`HeadroomAllocator` protocol in
`app/modules/ad_control_settings/domain/headroom.py`).

Compatible with `evaluate_shop_headroom_state` inputs (`allowed_spend_rub`,
`spend_rub`) when factual ports supply the quantities above.

### 6. Multi-nm / multi-size (V1)

V1 **MUST NOT** require catalog-price aggregation across sizes.

For one physical campaign `(shop_id, physical_adv_id)`:

```text
expected_attributed_order_value_rub
  = Σ DIRECT attributed_gmv_rub / Σ DIRECT attributed_orders
```

across all eligible nmids / orders in the accepted campaign window (weighted
factual order value). Product/nmid detail remains for diagnostics and future
allocation.

### 7. Canonical CPO terminology (V1)

| Term | Definition |
|------|------------|
| **OBSERVED_CPO_RUB** | `campaign_ad_spend_rub / DIRECT attributed_orders` (window aggregate) |
| **TARGET_CPO_RUB** | `expected_attributed_order_value_rub × effective_target_drr_fraction` |
| **MAX_CPO_RUB** | Controller / safety upper limit (bounded proposal; not bid) |
| **LEGACY_TARGET_PRICE_FOR_ORDER** | `AdvSetting.target_price_for_order` |
| **LEGACY_MAX_PRICE_FOR_ORDER** | `AdvSetting.max_price_for_order` |
| **BID / CPC / CPM** | Auction mechanics; **not** aliases for CPO |

Legacy plan fields and V3 `calc_pay_for_order` / CH point CPO remain **parallel**
runtime paths until explicit migration.

### 8. `ProductCpoResolver` compatibility (explicit dual authority)

| Path | Authority | V1 campaign headroom |
|------|-----------|----------------------|
| `ProductCpoResolver` | `effective_product_price_rub × DRR% / 100` | **Not required** |
| V1 order-value contract (this ADR) | `EXPECTED_ATTRIBUTED_ORDER_VALUE_RUB × DRR%` | **Required** for proposals |

- **ACCEPTED_EXISTING_FOUNDATION:** `ProductCpoResolver` math and
  `BLOCKED_BY_PRODUCT_PRICE_SOURCE` behavior **remain unchanged** in
  `product_control` (no silent rewrite in this ADR).
- **Forbidden:** treating `ProductCpoResolver` output as substitute for V1
  `TARGET_CPO_RUB` in hierarchical campaign control without an explicit future
  adapter/reconciliation decision.
- **Forbidden:** using `wb_common_stat` or `target_price_for_order` as
  `expected_attributed_order_value_rub`.

### 9. Fail-closed (V1 CPO proposal)

New bounded CPO proposals **MUST NOT** be emitted when any blocker applies:

| Blocker | Typical trigger |
|---------|-----------------|
| `DIRECT_ATTRIBUTION_MISSING` | No DIRECT facts in scope/window |
| `DIRECT_ATTRIBUTION_INSUFFICIENT` | DIRECT sums incomplete (missing ≠ 0) |
| `ATTRIBUTION_WINDOW_INCOMPLETE` | Coverage not `COMPLETE` or reconciliation fail |
| `ATTRIBUTION_FACT_STALE` | Observation / sufficiency stale per port policy |
| `ORDER_VALUE_UNAVAILABLE` | Zero DIRECT orders or undefined order value |
| `SHOP_ORDER_GMV_INCOMPLETE` | Whole-shop GMV window incomplete |
| `SHOP_SPEND_INCOMPLETE` | Shop spend numerator incomplete |
| `REVENUE_BASIS_UNSUPPORTED` | Buyout / net-margin / LINKED actuation requested |
| `CPO_INPUTS_INCOMPLETE` | Any required input absent |

`PRICE_UNKNOWN` / `PRICE_STALE` **MUST NOT** block V1 **ORDER_VALUE** CPO when all
required order-value and shop facts are valid. They remain relevant to
**price-based** `ProductControl` / `ProductCpoResolver` paths only.

Map to hierarchical Slice A where applicable (`PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`
is superseded for V1 **order-value** proposals once implementation reads this ADR;
catalog-price actuation remains blocked until a separate price SoT decision).

### 10. Hierarchical settings compatibility (Slice A)

Repository truth: `app/modules/ad_control_settings/` exists on parent
`065509c` and on branch `cursor/drr-cpo-price-semantics-22ef`. Cloud sparse
checkouts **MUST NOT** be treated as absence of Slice A.

| Slice A artifact | Compatibility |
|------------------|---------------|
| `ConfiguredTargetDrr` / `ActualDrrObservation` | Policy vs observed split — **aligns** |
| `ShopHeadroomState` / `evaluate_shop_headroom_state` | **Aligns** when ports supply GMV/spend per §5 |
| `BoundedCpoProposal.proposed_max_cpo_rub` | V1 uses order-value `TARGET_CPO_RUB`; catalog price not required |
| `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` | Remains for catalog-price actuation; V1 order-value path enabled by this ADR |
| `HEADROOM_ALLOCATOR_NOT_ACCEPTED` | Unchanged — ranking algorithm still deferred |

### 11. Deferred semantics (explicit OUT OF V1)

- `BUYOUT_GMV` control
- Seller net revenue / net margin
- **LINKED** actuation (observation only)
- Catalog-price authority for campaign CPO
- Customer-paid / SPP / wallet price semantics for control
- Margin-based CPO
- DIRECT+LINKED combined authority without deduplication decision

## Applies to

- Future V1 hierarchical campaign CPO proposal pipeline (read adapters only in
  separate implementation changes)
- `app/modules/ad_control_settings/domain/` (headroom / DRR state contracts)
- `app/modules/attribution_facts/domain/derived_metrics.py` (observed metrics;
  no formula change required)
- Diagnostics / AI package (LINKED and `store_drr` families remain non-authoritative
  for V1 control unless spec-amended)

## Allowed

- V1 `TARGET_CPO_RUB` from DIRECT order value × effective target DRR%
- Shop headroom rub formula in §5
- `ProductPricingReader` for non–V1-campaign paths and diagnostics
- `ProductCpoResolver` unchanged for future price-based product control
- `DRR_FACT_LINKED` / `CPO_FACT_LINKED` for reporting only

## Forbidden

- Requiring catalog/list price for V1 campaign `TARGET_CPO_RUB`
- LINKED (or DIRECT+LINKED) denominators for V1 CPO authority
- Shop DRR denominator from campaign-attributed GMV or `wb_common_stat` funnel sum
- Buyout / net-margin bases in V1
- Silent equivalence between `ProductCpoResolver` output and V1 `TARGET_CPO_RUB`
- LLM or heuristic bypass of §9 blockers

## Examples

Good:

- COMPLETE DIRECT window → `expected_attributed_order_value_rub = 1200` → target DRR 10% → `target_cpo_rub = 120.00`
- Shop GMV 1_000_000 ₽, target DRR 8%, spend 90_000 ₽ → `allowed = 80_000`, `headroom = −10_000`

Bad:

- `TARGET_CPO_RUB = MIN(discountedPrice) × DRR%` for V1 campaign control
- Shop `shop_actual_drr` using sum of campaign `DRR_FACT_DIRECT` denominators
- Emitting CPO proposal when DIRECT orders = 0 without `ORDER_VALUE_UNAVAILABLE`

## Related specs

- `openspec/specs/attribution-facts-contract/spec.md`
- `openspec/specs/product-control-context/spec.md`

## Related decisions

- `openspec/decisions/product-pricing-and-cpo-ownership/decision.md` (catalog path;
  not V1 campaign authority)
- `openspec/decisions/product-control-aggregate-ownership/decision.md`
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
- `openspec/decisions/shop-wide-common-sales-ownership/decision.md`

## Related changes

- Parent baseline: `065509c` (`hierarchical-ad-control-settings` Slice A merged)
- Evidence branch: `cursor/drr-cpo-price-semantics-22ef`

## Review checklist

- [x] Context-first decisions cited
- [x] Owner V1 order-value semantics encoded (not catalog price)
- [x] `ProductCpoResolver` compatibility explicit (dual path)
- [x] Hierarchical Slice A assessed at canonical commit
- [x] `PRICE_SEMANTICS_ACCEPTED = YES` with qualifier `V1_ORDER_VALUE_BASIS`
- [x] No production code in this artifact

## Working notes (non-authoritative)

- Project store evidence scan:
  `internal/drr-cpo-price-semantics/evidence-report.md` (superseded for control
  semantics by this ADR §3–§9)
