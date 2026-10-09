# Owner contract — hierarchical-ad-control-settings

## NOT_ENROLLED

`NOT_ENROLLED` => **FAIL CLOSED** for the new hierarchical controller. No implicit
hierarchical automation. Legacy only via explicit `LEGACY_PASSTHROUGH` control path.

## V1 scopes

Writable/configurable: **SHOP**, **CAMPAIGN**. **PRODUCT** architecturally compatible
via `ProductDrrPolicyAdapter` (no duplicated ProductControl persistence). Each feature
declares `supported_scopes`; unknown combinations fail closed.

## Campaign identity

Authority: `(shop_id, advert_id)`. `main_nmid` is not campaign authority.

## Configuration vs derived

Separate: configured policy, observed fact (`actual_drr`), derived control state
(`shop_effective_control_drr`, `campaign_effective_control_drr`). Derived not user settings.

## Live inheritance

Campaign INHERIT reads current shop policy without persisting shop values on campaign rows.

## Per-function controls (V1)

`DRR_POLICY`, `DYNAMIC_DRR_CONTROL`, `CPO_INCREASE_ON_HEADROOM`,
`CPO_DECREASE_ON_OVERSPEND`, `CPO_SAFETY_BOUNDS` — independent modes and parameters.

## Price semantics

`PRICE_SEMANTICS_ACCEPTED = NO`. Foundation allowed; CPO production actuation blocked.

## Stale / insufficient data

=> **NO NEW CONTROL ACTION**; deterministic reason codes.

## Headroom allocation

Foundation: `ShopHeadroomState`, eligibility, blockers, bounded proposal interface,
`HeadroomAllocator` protocol — **no accepted production ranking formula**.

## Persistence direction

Future: `(scope, feature_id, schema_version)` with typed domain payloads; JSONB storage
only as representation. **Not in Slice A.**

## Diagnostics

Mandatory future UI: Advertising Control + Diagnostics/Test using same resolver; no writes.
