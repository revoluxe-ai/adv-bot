# product-control-context

Product-oriented control foundation: DRR profiles, enrollment, current-price-based
CPO derivation, campaign bindings, fail-closed multi-nmid semantics. Transport-independent.

## ADDED Requirements

### Requirement: Product control identity

The system SHALL treat **`(shop_id, nmid)`** as the canonical identity for mutable
product control settings and effective resolution context.

WBCard SHALL remain catalog/metadata authority and MUST NOT store mutable control fields.

#### Scenario: Catalog vs control separation

- **GIVEN** a `WBCard` row for `nmid` N in shop S
- **WHEN** product control settings are defined for `(S, N)`
- **THEN** settings MUST be stored outside WBCard (e.g. `ProductControlSettings`)
- **AND** WBCard MUST NOT be updated with DRR or enrollment fields

### Requirement: Shop and product settings keys

`ShopControlSettings` MUST be keyed by `shop_id`.

`ProductControlSettings` MUST be keyed by `(shop_id, nmid)`.

Tenancy MUST NOT rely on globally unique `nmid` alone.

#### Scenario: Same nmid different shops

- **GIVEN** two distinct `shop_id` values S1 and S2
- **WHEN** product control profiles are configured for the same marketplace `nmid` N
- **THEN** S1 and S2 MUST have independent `ProductControlSettings` rows

### Requirement: Shop rollout enrollment

Shop rollout SHALL use `ShopControlEnrollment`:

- `NOT_ENROLLED` — product-control plane inactive for the entire shop
- `ENROLLED` — shop rollout gate open; per-product `ProductControlMode` is evaluated
- `BLOCKED` — product-control blocked shop-wide

Default shop enrollment MUST be `NOT_ENROLLED`.

#### Scenario: Shop master gate blocks product override

- **GIVEN** shop S has `ShopControlEnrollment` `NOT_ENROLLED`
- **AND** product `(S, N)` has `ProductControlMode` `OVERRIDE_ENABLED` with a valid `DrrProfile`
- **WHEN** runtime resolves product-control outcome for `(S, N)`
- **THEN** outcome MUST be `LEGACY_NOT_ENROLLED`
- **AND** product-control path MUST NOT activate

#### Scenario: Shop blocked overrides all product modes

- **GIVEN** shop S has `ShopControlEnrollment` `BLOCKED`
- **AND** product `(S, N)` has `ProductControlMode` `OVERRIDE_ENABLED` with a valid `DrrProfile`
- **WHEN** runtime resolves product-control outcome
- **THEN** outcome MUST be `PRODUCT_CONTROL_BLOCKED`
- **AND** MUST NOT fall back to legacy campaign CPO

### Requirement: Product control mode

Per-product behavior SHALL use `ProductControlMode` distinct from shop enrollment:

- `INHERIT_SHOP` (default) — use shop `DrrProfile` when shop is `ENROLLED` and profile present; otherwise LEGACY tier
- `OVERRIDE_ENABLED` — use product `DrrProfile` atomically when present; MUST NOT silently behave as `INHERIT_SHOP`
- `BLOCKED` — `PRODUCT_CONTROL_BLOCKED` for `(S, N)` when shop rollout is active

The system MUST NOT use a product state named `NOT_ENROLLED` to mean inheritance.

#### Scenario: Override without profile is invalid at write time

- **GIVEN** shop S is `ENROLLED`
- **WHEN** a write sets `ProductControlMode` to `OVERRIDE_ENABLED` without a product `DrrProfile`
- **THEN** the write MUST fail closed (validation error)
- **AND** invalid configuration MUST NOT be persisted

#### Scenario: Invalid override read fail closed

- **GIVEN** shop S is `ENROLLED`
- **AND** corrupted persistence has `OVERRIDE_ENABLED` without product `DrrProfile`
- **WHEN** effective control is resolved at runtime
- **THEN** outcome MUST be configuration-invalid / `PRODUCT_CONTROL_BLOCKED`
- **AND** MUST NOT silently treat as `INHERIT_SHOP`

### Requirement: DrrProfile atomic inheritance

Configured control SHALL use atomic `DrrProfile` objects with
`target_drr_percent` and `max_drr_percent`.

Effective resolution SHALL inherit **whole profiles** across tiers:
PRODUCT (override) → CATEGORY (reserved) → SHOP → LEGACY.

The resolver MUST NOT combine fields from different tiers (e.g. SKU target + SHOP max).

Missing profile at a tier SHALL mean inherit to the next tier, not zero.

#### Scenario: Shop profile applies for INHERIT_SHOP

- **GIVEN** shop S is `ENROLLED` with shop `DrrProfile` P
- **AND** product `(S, N)` has `ProductControlMode` `INHERIT_SHOP`
- **AND** product has no `DrrProfile`
- **WHEN** effective control is resolved for `(S, N)`
- **THEN** effective profile MUST equal P

#### Scenario: Product profile overrides shop atomically

- **GIVEN** shop S is `ENROLLED` with shop profile P_shop
- **AND** product `(S, N)` has `ProductControlMode` `OVERRIDE_ENABLED` with profile P_sku
- **WHEN** effective control is resolved
- **THEN** effective profile MUST equal P_sku (not a merge with P_shop)

#### Scenario: Enrolled shop without any DRR profile uses LEGACY tier

- **GIVEN** shop S is `ENROLLED`
- **AND** product `(S, N)` has `ProductControlMode` `INHERIT_SHOP`
- **AND** shop has no `DrrProfile`
- **AND** product has no `DrrProfile`
- **WHEN** effective control is resolved for `(S, N)`
- **THEN** resolver MUST use LEGACY tier (campaign CPO fields)
- **AND** MUST NOT use zero DRR or `PRODUCT_CONTROL_BLOCKED` solely for missing profiles

### Requirement: Pricing vs sales economics ports

`ProductPricingReader` SHALL supply authoritative **current/effective** unit price
for control for `(shop_id, nmid)`.

`ProductSalesEconomicsReader` MAY supply historical orders/GMV/revenue-per-order from
`wb_common_stat` and related analytics sources.

`ProductSalesEconomicsReader` output MUST NOT be used as `effective_product_price` for
`ProductCpoResolver`.

#### Scenario: Common stat is not control price

- **GIVEN** historical `orders_sum` exists in `wb_common_stat` for `(nmid, date)`
- **AND** `ProductPricingReader` returns unavailable for `(S, nmid)`
- **WHEN** derived CPO is requested under active shop rollout with effective `DrrProfile`
- **THEN** system MUST NOT compute DRR-derived CPO from `orders_sum/orders`
- **AND** MUST emit `BLOCKED_BY_PRODUCT_PRICE_SOURCE`

### Requirement: ProductCpoResolver single owner and domain money

DRR→CPO calculation SHALL exist only in `ProductCpoResolver` (domain/application).

Formula when price and profile are available:

- `target_cpo_rub = effective_product_price × target_drr_percent / 100`
- `max_cpo_rub = effective_product_price × max_drr_percent / 100`

Canonical domain output MUST use money semantics at **0.01 RUB** precision:

- `target_cpo_rub`: ROUND_HALF_UP to 0.01 RUB
- `max_cpo_rub`: ROUND_HALF_UP to 0.01 RUB

Integer ruble `max_price_for_order` on `AdvSetting` is a legacy storage constraint.
`LegacyCampaignCpoAdapter` (Slice D) MUST perform deterministic ROUND_HALF_UP to
integer RUB when writing legacy fields.

Telegram, Excel, AI Package prompts, MCP, and campaign handlers MUST NOT embed
duplicate formulas.

Future JSON/API/MCP MUST expose canonical domain money values, not legacy int limits.

#### Scenario: Missing price blocks derived CPO

- **GIVEN** shop rollout active with effective `DrrProfile`
- **AND** pricing reader returns unavailable
- **WHEN** `ProductCpoResolver` is invoked
- **THEN** result MUST be blocked with `BLOCKED_BY_PRODUCT_PRICE_SOURCE`
- **AND** MUST NOT fabricate zero CPO

### Requirement: Zero default rollout behavior

Default shop enrollment MUST be `NOT_ENROLLED`.

Default product mode MUST be `INHERIT_SHOP`.

Deploying schema/code without shop `ENROLLED` MUST NOT alter campaign runtime economics.

#### Scenario: Zero enrollment zero change

- **GIVEN** no shop has `ShopControlEnrollment` `ENROLLED`
- **WHEN** shop-runner executes a tick
- **THEN** `target_price_for_order` / `max_price_for_order` behavior MUST match pre-change legacy

### Requirement: Legacy vs blocked outcomes

`LEGACY_NOT_ENROLLED` SHALL apply when shop rollout is `NOT_ENROLLED`, or when shop
is `ENROLLED` and LEGACY tier applies (no effective DRR profile after resolution).

`PRODUCT_CONTROL_BLOCKED` SHALL apply when shop is `BLOCKED`, product mode is
`BLOCKED`, configuration is invalid, or a safety rule prevents derivation (ambiguous
multi-nm, missing/stale price under active rollout with effective DRR).

Blocked outcomes MUST NOT silently fall back to legacy campaign CPO.

#### Scenario: Explicit rollout with ambiguous multi-nm

- **GIVEN** shop `ENROLLED` and effective DRR profile for the control scope
- **AND** campaign complex lists multiple nmIDs without proven single control SKU
- **WHEN** adapter requests product-derived CPO for that complex
- **THEN** outcome MUST be `PRODUCT_CONTROL_BLOCKED` with `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`
- **AND** MUST NOT use `main_nmid` or `nmids[0]` for economics

### Requirement: CampaignProductBinding

Bindings SHALL be modeled as `CampaignProductBinding` with at least:
`shop_id`, `physical_adv_id`, `adv_setting_id` (logical), `leg_role` (AUTO|SEARCH),
`nmid`, membership evidence, optional `effective_from`/`effective_to`.

PRIMARY membership MUST NOT be derived from `ComplexAdv.main_nmid` or sorted nmids.

#### Scenario: Auto and Search legs separate

- **GIVEN** a `ComplexAdv` with auto `adv_id` A and search `adv_id` B
- **WHEN** bindings are projected for `nmid` N
- **THEN** there MUST be distinct bindings for leg AUTO and leg SEARCH when both exist

#### Scenario: One product multiple complexes

- **GIVEN** `nmid` N appears in two bot-active complexes in shop S
- **WHEN** bindings are listed for `(S, N)`
- **THEN** multiple bindings MUST be returned (one per physical leg association)

### Requirement: Multi-nmid fail-closed

For V1 product-derived CPO, a campaign complex with `len(nmids) != 1` WITHOUT
authoritative single control-product mapping MUST fail closed.

Forbidden heuristics: `nmids[0]`, min/max/average price, combining DRR profiles,
copying economics from `main_nmid`.

#### Scenario: Single-nmid campaign safe resolve

- **GIVEN** exactly one `nmid` N on auto `AdvSetting`
- **AND** shop rollout active with effective DRR and price available
- **WHEN** resolving control product for the complex
- **THEN** control product MUST be `(shop_id, N)`

#### Scenario: Multi-nmid without authority

- **GIVEN** `nmids` = [N1, N2] on one complex
- **WHEN** product-derived CPO is requested under active shop rollout
- **THEN** MUST return `PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS`

### Requirement: DrrProfile invariants

Stored `DrrProfile` MUST include both percent fields.

Validation MUST enforce `max_drr_percent >= target_drr_percent`.

#### Scenario: Invalid profile rejected

- **GIVEN** a profile with `target_drr_percent` > `max_drr_percent`
- **WHEN** persisting or applying settings
- **THEN** operation MUST fail closed (validation error)

### Requirement: Future ChangeSet operations

Future mutations SHALL include atomic profile operations:

- `SET_SHOP_DRR_PROFILE`
- `SET_PRODUCT_DRR_PROFILE`
- (future) `SET_CATEGORY_DRR_PROFILE`

Independent partial target/max writes MUST NOT bypass profile invariants when
both values are required together.

#### Scenario: Atomic shop DRR profile mutation

- **GIVEN** a future ChangeSet with `SET_SHOP_DRR_PROFILE` carrying a full `DrrProfile`
- **WHEN** validation runs before Apply (future slice)
- **THEN** both `target_drr_percent` and `max_drr_percent` MUST be present atomically
- **AND** partial target-only or max-only writes MUST be rejected

### Requirement: ProductControlContextV1

The system SHALL define `ProductControlContextV1` documenting identity, category refs,
pricing and sales economics evidence, effective DRR, derived CPO (canonical money),
bindings, blockers, capabilities, attribution references (opaque), shop enrollment,
product control mode, and provenance.

This change MUST NOT implement AI Package or MCP export.

#### Scenario: Context exposes enrollment and mode separately

- **GIVEN** shop S is `ENROLLED` and product `(S, N)` has `ProductControlMode` `INHERIT_SHOP`
- **WHEN** `ProductControlContextV1` is assembled (future export)
- **THEN** payload MUST include distinct `shop_control_enrollment` and `product_control_mode` fields
- **AND** derived CPO values MUST use canonical 0.01 RUB money semantics when present
