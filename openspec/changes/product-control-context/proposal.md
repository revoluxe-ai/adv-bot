## Why

WB Sky runtime is campaign-centric (`AdvSetting` / `ComplexAdv`), while Owner economics
and future AI control are product-centric (`nmid` within `shop_id`). Campaign-owned
`target_price_for_order` / `max_price_for_order` must remain execution compatibility
until a strangler product-control plane is introduced with explicit enrollment and
fail-closed ambiguity rules.

## What Changes

- ADDED: product-control domain foundation — `(shop_id, nmid)` control anchor,
  `DrrProfile`, enrollment, hierarchical effective control resolution
  (SKU → SHOP → LEGACY; CATEGORY deferred).
- ADDED: split pricing ports — `ProductPricingReader` (current/effective sale price)
  vs `ProductSalesEconomicsReader` (`wb_common_stat` historical facts).
- ADDED: `ProductCpoResolver` — single owner for DRR→CPO pure math (no transport
  duplication).
- ADDED: `CampaignProductBinding` read-model — Auto/Search legs, provenance, no
  `main_nmid` as PRIMARY SoT.
- ADDED: future `ProductControlContextV1` contract shape for AI Package/MCP (no
  transport in this change).
- ADDED: three proposed architecture decisions under `decisions/`.
- OUT OF SCOPE (this change): runtime code, PG migrations, category control runtime,
  ChangeSet Apply, attribution-facts, MCP, deploy.

## Capabilities

### New Capabilities

- `product-control-context`: domain contracts, enrollment, DRR profiles, CPO derivation
  policy, campaign↔product bindings, ambiguity blockers, strangler slices A–F.

### Modified Capabilities

- _(none — no canonical spec delta outside this change folder until archive)_

## Impact

- **Runtime**: none until Slice D (explicit Owner GO per slice).
- **Data**: new tables designed in spec; DDL deferred to Slice C.
- **Risk**: multi-nmid campaigns; missing current-price authority in `app/` today
  (`BLOCKED_BY_PRODUCT_PRICE_SOURCE` for DRR-derived CPO until pricing port is wired).
- **Dependencies**: references `shop-wide-common-sales-collection`,
  `campaign-settings-history` contract patterns, `strict-single-nmid-audit-evidence`
  fail-closed posture.
