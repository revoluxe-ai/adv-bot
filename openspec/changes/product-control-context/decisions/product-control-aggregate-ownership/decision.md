# Decision: product-control-aggregate-ownership

## Status

Proposed

## Context

Campaign `AdvSetting` rows currently own economic inputs (`target_price_for_order`,
`max_price_for_order`) suitable for execution but not for long-term product-oriented
control. WBCard exists as catalog cache with global `nmid` uniqueness. Owner requires
`(shop_id, nmid)` as control anchor without turning WBCard into a settings bag.

## Decision

1. **Catalog authority** — `WBCard` (+ Content API ingestion) owns product identity and
   cached WB metadata only.
2. **Mutable product control** — `ProductControlSettings` keyed `(shop_id, nmid)` owns
   product-level DRR profiles, product enrollment, and future product control fields.
3. **Shop defaults** — `ShopControlSettings` keyed `shop_id` owns shop-level DRR
   profile and shop enrollment.
4. **Execution boundary** — `AdvSetting` / `ComplexAdv` remain campaign execution
   entities (bids, keywords, legs, legacy CPO until adapter + enrollment).
5. **Category** — `CategoryControlSettings` deferred; precedence slot documented only.

## Applies to

- `app/modules/product_control/**` (planned)
- Future UI/Excel/ChangeSet writers for DRR profiles
- AI `ProductControlContextV1` readers

## Allowed

- Read WBCard for catalog/category references in control context export.
- Project campaign bindings without storing control economics on WBCard.

## Forbidden

- Adding DRR, enrollment, or derived CPO columns to `WBCard` for convenience.
- Using global `nmid` uniqueness as tenancy for shop-scoped control settings.
- Making `AdvSetting` the canonical owner of DRR targets post-migration (new writes).

## Examples

Good: `ProductControlSettings(shop_id, nmid).drr_profile` updated via domain service.

Bad: `WBCard.json["target_drr"]` mutated by shop-runner tick.

## Related specs

- `openspec/changes/product-control-context/specs/product-control-context/spec.md`

## Related changes

- `product-control-context`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed
- [x] implementation layer matches decision
