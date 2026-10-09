# Decision: product-control-aggregate-ownership

## Status

Accepted

## Context

Campaign `AdvSetting` rows currently own economic inputs (`target_price_for_order`,
`max_price_for_order`) suitable for execution but not for long-term product-oriented
control. WBCard exists as catalog cache with global `nmid` uniqueness. Owner requires
`(shop_id, nmid)` as control anchor without turning WBCard into a settings bag.

Archived change `product-control-context` implemented domain foundation (Slices A–B)
only. **PG persistence is a separate future OpenSpec change.**

## Decision

1. **Catalog authority** — `WBCard` (+ Content API ingestion) owns product identity and
   cached WB metadata only.
2. **Mutable product control (future persistence)** — `ProductControlSettings` keyed
   `(shop_id, nmid)` will own `ProductControlMode`, product-level `DrrProfile` when
   override is enabled, and future product control fields. **Not implemented in
   foundation archive.**
3. **Shop defaults (future persistence)** — `ShopControlSettings` keyed `shop_id` will
   own shop-level DRR profile and `ShopControlEnrollment`. Shop enrollment is the
   **master rollout gate**; product modes cannot bypass `NOT_ENROLLED` or `BLOCKED`.
4. **Execution boundary** — `AdvSetting` / `ComplexAdv` remain campaign execution
   entities until a future runtime adapter + enrollment.
5. **Category** — `CategoryControlSettings` deferred; precedence slot documented only.

## Applies to

- `app/modules/product_control/**` (foundation delivered)
- Future persistence, UI/Excel/ChangeSet writers, AI export (separate changes)

## Allowed

- Read WBCard for catalog/category references in future control context export.
- Project campaign bindings without storing control economics on WBCard (Slice B).

## Forbidden

- Adding DRR, enrollment, or derived CPO columns to `WBCard` for convenience.
- Using global `nmid` uniqueness as tenancy for shop-scoped control settings.
- Making `AdvSetting` the canonical owner of DRR targets post-migration (new writes).

## Related specs

- `openspec/specs/product-control-context/spec.md`

## Related changes

- Archived: `openspec/changes/archive/2026-10-09-product-control-context/`
