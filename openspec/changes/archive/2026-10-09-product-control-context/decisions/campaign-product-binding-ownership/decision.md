# Decision: campaign-product-binding-ownership

## Status

Proposed

## Context

`AdvSetting.nmids` is 1:N; `ComplexAdv` exposes `main_nmid = sorted(nmids)[0]` used
widely for analytics and legacy collectors. Owner forbids using that convention as
authoritative control ownership. One product may map to many campaign legs (Auto +
Search); one complex may map to many products.

## Decision

1. **Cardinality** — Campaign complex MAY contain multiple nmIDs; product MAY bind to
   multiple physical `adv_id` legs. No assumption campaign == product.
2. **Binding model** — `CampaignProductBinding` is the transport-independent contract
   for shop_id, physical_adv_id, logical adv_setting_id, leg_role (AUTO|SEARCH), nmid,
   membership role/evidence, effective window, provenance.
3. **main_nmid** — Runtime convenience only; **MUST NOT** establish PRIMARY control
   product or DRR scope.
4. **PRIMARY** — Assigned only with explicit evidence (e.g. single-member complex,
   WB nm_settings role when defined in projector policy). Otherwise `UNKNOWN`.
5. **Multi-nmid V1 CPO** — Product-derived CPO MUST fail closed with
   `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS` unless a single control `(shop_id, nmid)` is
   proven for that execution scope.
6. **Auto/Search** — Physical legs MUST remain distinct in bindings and adapters.

## Applies to

- `CampaignProductBinding` projector (Slice B)
- Shop-runner campaign adapter (Slice D+)
- AI Package binding sections in `ProductControlContextV1`

## Allowed

- Multiple bindings per `(shop_id, nmid)` across complexes and legs.
- Read-only projection from PG + WB metadata without new binding table in Slice B.

## Forbidden

- Inferring PRIMARY from `main_nmid`, `nmids[0]`, or lowest/highest price.
- Averaging economics across nmIDs in one complex.
- Merging Auto and Search `adv_id` into one binding row without `leg_role`.

## Examples

Good: complex with `nmids=[A,B]` → bindings for A and B with roles UNKNOWN → adapter BLOCKED.

Bad: `main_nmid=A` → apply shop DRR to entire complex spend.

## Related specs

- `openspec/changes/product-control-context/specs/product-control-context/spec.md`

## Related changes

- `product-control-context`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed
- [x] implementation layer matches decision
