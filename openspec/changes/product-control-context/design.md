## Context

Inventory (accepted): `AdvSetting.nmids` is 1:N; `ComplexAdv` pairs Auto + optional
Search `AdvSetting`; `main_nmid = sorted(nmids)[0]` is runtime convention only;
`WBCard.nmid` is globally unique with optional `wb_cabinet_id`; shop assortment SoT
is Content API pagination (`shop-wide-common-sales-ownership`), not WBCard alone.

Owner correction: DRR→CPO MUST use **current/effective product price**, not
`wb_common_stat` historical `orders_sum`/derived revenue per order.

**Price evidence (repository):**

| Source | Location | Role today |
|--------|----------|------------|
| Content API `get_cards_list` / `WBCard.json` | `ProductsManager`, `CardFromWB` | Catalog metadata; **no** price accessor in runtime DTOs |
| Discounts & Prices API `POST /api/v2/list/goods/filter` | `scripts/a1_sale_price_snapshot.py` (read-only script) | Parses `sizes[].discountedPrice`; `SALE_PRICE_REFERENCE` = min discounted across sizes when multi-size |
| `wb_common_stat` | `CommonStat.orders_sum`, funnel history | Historical sales economics; used for cart→order, SKU GMV analytics |
| `AdvSetting.target_price_for_order` | Campaign settings | Configured **CPO rub**, not marketplace sale price |

**Conclusion:** No trustworthy **runtime** `ProductPricingReader` implementation exists
in `app/` today → `BLOCKED_BY_PRODUCT_PRICE_SOURCE` for DRR-derived CPO until Slice D
wires an accepted reader (candidate: Discounts & Prices API per script evidence; ADR
C remains **Proposed** with `EVIDENCE_GAP` for promo-effective semantics and staleness).

## Goals / Non-Goals

**Goals:**

- Domain vocabulary, ports, invariants, enrollment, binding model, resolver contracts.
- Strangler slices A–F with zero behavior change until Slice D + enrollment.
- `ProductControlContextV1` machine-readable shape for future AI.
- Future ChangeSet ops: `SET_SHOP_DRR_PROFILE`, `SET_PRODUCT_DRR_PROFILE`.

**Non-Goals:**

- PG migrations, shop-runner adapter, UI/Excel, MCP, category tier runtime,
  AutoShelf migration, attribution-facts.

## Architecture Decision References

- `openspec/changes/product-control-context/decisions/product-control-aggregate-ownership/decision.md` — Proposed
- `openspec/changes/product-control-context/decisions/campaign-product-binding-ownership/decision.md` — Proposed
- `openspec/changes/product-control-context/decisions/product-pricing-and-cpo-ownership/decision.md` — Proposed
- `openspec/decisions/shop-wide-common-sales-ownership/decision.md` — Accepted (assortment / `wb_common_stat` write)
- `openspec/decisions/strict-single-nmid-audit-evidence/decision.md` — Accepted (fail-closed evidence)

## Design Readiness

DURABLE_SOT_RESOLVED: partial (control anchor yes; current price SoT gap)
WRITE_AUTHORITY_RESOLVED: yes (no writes in this change)
RECOVERY_SEMANTICS_RESOLVED: yes (enrollment + legacy)
NORMATIVE_CONFLICTS: none
PRODUCT_ACCEPTANCE_REQUIRED: true
DESIGN_STATUS: READY

## Ownership & Placement

| Concern | Owner | Forbidden |
|---------|-------|-----------|
| Catalog identity | `WBCard` + Content API | Control fields on WBCard |
| Mutable DRR / enrollment | `ProductControlSettings`, `ShopControlSettings` (future PG) | AdvSetting new DRR columns without migration plan |
| Current price | `ProductPricingReader` impl (future `app/modules/product_control/`) | `wb_common_stat` as price input to CPO |
| Historical economics | `ProductSalesEconomicsReader` | Same reader as pricing |
| DRR→CPO math | `ProductCpoResolver` (pure) | Telegram, Excel, AI prompts, MCP, campaign handlers |
| Effective DRR tier | `EffectiveControlResolver` | Field-level cross-tier merge |
| Bindings projection | `CampaignProductBinding` projector (Slice B) | `main_nmid` as PRIMARY |
| Execution CPO (legacy) | `AdvSetting` until adapter | Silent override when BLOCKED |

Planned module root (apply slices): `app/modules/product_control/` (domain + application ports).

### AutoShelfBidControlSettings reconciliation

- **Relation to product control:** `UNRELATED` capability (shelf bid experiments).
- **Pattern reference:** `REFERENCE` — precedent for nmid-keyed settings table.
- **Tenancy:** `FUTURE_MIGRATION` — today `unique(nmid)` without `shop_id`; product
  control MUST use `(shop_id, nmid)`; do not migrate in this change.

## Enrollment model

```text
ControlEnrollmentState: NOT_ENROLLED | ENROLLED | BLOCKED
```

- **Shop** `shop_control_enrollment` default `NOT_ENROLLED`.
- **Product** `product_control_enrollment` default `NOT_ENROLLED`.
- Shop `ENROLLED` enables shop-level `DrrProfile` for products that are not
  `BLOCKED` and have no product-level profile override.
- Product `ENROLLED` + profile enables SKU tier (overrides shop profile atomically).
- `BLOCKED` at product or shop records explicit deny / diagnostic (no silent legacy
  when product path was explicitly enabled — see spec).

## DrrProfile inheritance

Target precedence (full): **PRODUCT → CATEGORY → SHOP → LEGACY**

Initial resolver tiers: **PRODUCT → SHOP → LEGACY** (category slot reserved).

Atomic profile inheritance: if SKU has `DrrProfile` → use it; else if SHOP profile
→ use it; else LEGACY (campaign CPO fields via adapter, not DRR).

Invariant: `target_drr_percent` and `max_drr_percent` MUST both be present on a
stored profile; `max_drr_percent >= target_drr_percent` (validation).

## ProductCpoResolver — rounding

Align with existing money helpers (`promo_plan_multiplier.scale_number`):

- `target_cpo_rub`: `Decimal` multiply; **ROUND_HALF_UP** to **2** decimal places (rub).
- `max_cpo_rub`: **ROUND_HALF_UP** to **integer** rubles (matches `max_price_for_order: int`).

If `effective_product_price` is unknown/stale per pricing policy → no CPO; blocker
`BLOCKED_BY_PRODUCT_PRICE_SOURCE` (not zero).

## CampaignProductBinding

See decision `campaign-product-binding-ownership`. Projection sources (Slice B):

- `AdvSetting.nmids`, `adv_id`, `search_adv_id`, `wb_cabinet` → `shop_id`
- WB campaign meta when available (nm_settings cardinality)
- Membership role: `PRIMARY` only with explicit evidence; else `UNKNOWN`
- Multi-nmid without proven single control SKU → bindings exist but
  `product_control_status = AMBIGUOUS`

## ProductControlContextV1 (future export)

JSON-serializable document keyed `(shop_id, nmid, schema_version)`:

- `identity`, `category_refs`, `pricing_evidence`, `sales_economics_evidence`
- `effective_drr_profile`, `derived_cpo`, `bindings` (auto/search lists)
- `blockers[]`, `capabilities[]`, `attribution_refs[]` (opaque ids only)
- `enrollment`, `provenance` (price observed_at, profile version, resolver generation)

## Implementation slices

| Slice | Content | Behavior change |
|-------|---------|-----------------|
| A | Domain types, ports, pure resolvers, unit tests | No |
| B | Read-only binding projector | No |
| C | PG settings + repos | No (no adapter) |
| D | Enrolled shop DRR + price → CPO + campaign adapter | **Yes** |
| E | Product/SKU override | Yes (enrolled) |
| F | UI / Excel / ChangeSet / AI export | Yes (surface) |

**First behavior-changing slice:** **Slice D** (shop DRR path first).

## Review checklist

- [x] context-first decision lookup performed
- [x] relevant decisions cited
- [x] new decisions proposed
- [x] implementation layer matches decision (planned `product_control` module)
