# Owner Contract: product-control-context

## Owner intent

Introduce a **product-oriented control foundation** for WB Sky without rewriting the
campaign runtime. Canonical control identity is **`(shop_id, nmid)`**. WBCard remains
catalog/metadata authority only. Campaigns remain execution entities.

DRR-based control MUST use **current/effective product price**, not historical
`wb_common_stat` revenue/order aggregates, as implicit price authority.

## Required semantics

- **Control anchor**: `(shop_id, nmid)` for mutable product control; `shop_id` alone
  for shop defaults.
- **WBCard**: catalog identity, WB card JSON cache, category reference — **MUST NOT**
  accumulate mutable control fields (DRR, enrollment, derived CPO).
- **Pricing split**:
  - `ProductPricingReader` — authoritative **current/effective** unit price for control.
  - `ProductSalesEconomicsReader` — historical orders/GMV/revenue-per-order for
    analytics/capacity; `wb_common_stat` allowed here only.
- **DRR profile**: atomic `DrrProfile { target_drr_percent, max_drr_percent }`;
  inheritance replaces **whole profile** at each tier (SKU → CATEGORY → SHOP → LEGACY);
  **no** field-level mix (e.g. SKU target + SHOP max) unless future Owner decision.
- **NULL / missing profile** at a tier means **inherit**; MUST NOT mean zero.
- **DRR→CPO** (when price available):
  - `target_cpo_rub = effective_product_price × target_drr_percent / 100`
  - `max_cpo_rub = effective_product_price × max_drr_percent / 100`
  - Single domain owner (`ProductCpoResolver`); forbidden in Telegram/Excel/AI/MCP/handlers.
- **Campaign bindings**: `CampaignProductBinding` transport-independent; PRIMARY MUST NOT
  be inferred from `ComplexAdv.main_nmid` or `sorted(nmids)[0]`.
- **Multi-nmid fail-closed**: V1 product-derived CPO MUST NOT run when a campaign complex
  has multiple nmIDs without authoritative single control-product mapping; emit blocker
  (e.g. `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`).
- **Enrollment**: default `NOT_ENROLLED`; deploying foundation alone MUST NOT change
  runtime behavior. `ENROLLED` enables product-control path; `BLOCKED` is explicit
  safety/diagnostic state.
- **Legacy**: `AdvSetting.target_price_for_order` / `max_price_for_order` remain
  authority for `LEGACY_NOT_ENROLLED` and when no effective DRR profile applies.
- **Blocked vs legacy**: when product control is **explicitly enabled** and a safety
  condition fires (ambiguous multi-nm, missing price), MUST **NOT** silently fall back
  to legacy (`PRODUCT_CONTROL_BLOCKED` ≠ `LEGACY_NOT_ENROLLED`).
- **Category**: precedence `PRODUCT > CATEGORY > SHOP` documented; **no** category
  runtime in this change (`WBCategory` name-local ID not durable taxonomy SoT).

## Out of scope

- Attribution-facts implementation, decision-experiment-memory, ChangeSet Apply Authority.
- Shop-wide campaign collection changes, campaign-settings-history implementation.
- MCP transport, production deploy, AutoShelfBidControlSettings migration.
- Runtime code, Alembic/DDL, shop-runner adapter (later slices).

## Owner acceptance

1. OpenSpec package + three decisions exist and pass planning gates.
2. Scenario plan covers enrollment, inheritance, multi-nm fail-closed, price gap, and
   Auto/Search leg separation.
3. Slice A–F documented; first behavior-changing slice identified as Slice D.
4. Current product price authority documented with honest `BLOCKED_BY_PRODUCT_PRICE_SOURCE`
   for runtime DRR→CPO until `ProductPricingReader` is implemented against an accepted
   WB price source.
