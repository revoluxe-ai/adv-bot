# Decision: campaign-product-binding-ownership

## Status

Accepted

## Context

`AdvSetting.nmids` is 1:N; `ComplexAdv` exposes `main_nmid = sorted(nmids)[0]` used
widely for analytics and legacy collectors. Owner forbids using that convention as
authoritative control ownership. Slice B delivered read-only
`CampaignProductBindingProjector` with separate Auto/Search physical legs.

## Decision

1. **Cardinality** — Campaign complex MAY contain multiple nmIDs; product MAY bind to
   multiple physical `adv_id` legs.
2. **Binding model** — `CampaignProductBinding` is the transport-independent contract.
3. **main_nmid** — Runtime convenience only; **MUST NOT** establish PRIMARY control
   product or DRR scope (Slice B tests enforce UNKNOWN for multi-nmid).
4. **PRIMARY** — Only with explicit evidence (`PG_NMIDS` single unique nmid on leg).
5. **Multi-nmid** — `resolve_control_product_for_complex` fails closed without
   authoritative control nmid.
6. **Auto/Search** — Search physical `adv_id` from paired `search_adv.adv_id`, not
   `search_adv_id` linkage field.

## Applies to

- `app/modules/product_control/application/projection/` (delivered)
- Future shop-runner adapter (separate change)

## Forbidden

- Inferring PRIMARY from `main_nmid`, `nmids[0]`, or price heuristics.
- Merging Auto and Search into one binding without `leg_role`.

## Related specs

- `openspec/specs/product-control-context/spec.md`
