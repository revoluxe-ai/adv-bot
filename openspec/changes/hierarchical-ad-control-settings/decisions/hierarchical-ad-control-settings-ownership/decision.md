# Decision: hierarchical-ad-control-settings-ownership

## Status

Proposed (change `hierarchical-ad-control-settings`)

## Context

Product control foundation owns `(shop_id, nmid)` DrrProfile resolution.
Campaign settings contract owns AdvSetting field classification. Owner approved
hierarchical per-function automation with SHOP + CAMPAIGN configuration and
PRODUCT compatibility via adapter only.

## Decision

1. **Automation feature registry and hierarchical resolver** belong to
   `app/modules/ad_control_settings/` (pure domain in Slice A).
2. **Product DrrProfile semantics** remain in `app/modules/product_control/`;
   ad control MUST use `ProductDrrPolicyAdapter`, not duplicate persistence.
3. **Campaign identity** for hierarchical control is `(shop_id, advert_id)`.
4. **Configured policy** is persisted separately from **derived** DRR/headroom state
   (derived recomputable; persistence in future slice).
5. **NOT_ENROLLED** => hierarchical fail closed; **LEGACY_PASSTHROUGH** explicit only.

## Applies to

- `app/modules/ad_control_settings/**`
- Future persistence, UI, ChangeSet ops (separate slices)

## Forbidden

- Global single automation enable flag replacing per-feature modes.
- Copying shop configured values into campaign rows as inheritance authority.
- CPO production actuation in foundation while `PRICE_SEMANTICS_ACCEPTED = NO`.
- Production headroom ranking formula in foundation slice.

## Related specs

- `openspec/changes/hierarchical-ad-control-settings/specs/hierarchical-ad-control-settings/spec.md`
- `openspec/specs/product-control-context/spec.md`
