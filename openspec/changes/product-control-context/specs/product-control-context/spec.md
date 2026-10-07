# product-control-context

Product-oriented control foundation: DRR profiles, enrollment, current-price-based
CPO derivation, campaign bindings, fail-closed multi-nmid semantics. Transport-independent.

## Requirements

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

### Requirement: DrrProfile atomic inheritance

Configured control SHALL use atomic `DrrProfile` objects with
`target_drr_percent` and `max_drr_percent`.

Effective resolution SHALL inherit **whole profiles** across tiers:
PRODUCT → SHOP → LEGACY (CATEGORY reserved).

The resolver MUST NOT combine fields from different tiers (e.g. SKU target + SHOP max).

Missing profile at a tier SHALL mean inherit to the next tier, not zero.

#### Scenario: Shop profile applies without SKU override

- **GIVEN** shop S is `ENROLLED` with shop `DrrProfile` P
- **AND** product `(S, N)` has no product-level `DrrProfile`
- **WHEN** effective control is resolved for `(S, N)`
- **THEN** effective profile MUST equal P

#### Scenario: SKU profile overrides shop

- **GIVEN** shop profile P_shop and product profile P_sku for `(S, N)`
- **WHEN** effective control is resolved
- **THEN** effective profile MUST equal P_sku (not a merge with P_shop)

#### Scenario: NULL means inherit

- **GIVEN** product `(S, N)` has no product `DrrProfile`
- **AND** shop has no shop `DrrProfile`
- **WHEN** effective control is resolved for non-enrolled legacy scope
- **THEN** resolver MUST use LEGACY tier (campaign CPO fields)

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
- **WHEN** derived CPO is requested for enrolled product control
- **THEN** system MUST NOT compute DRR-derived CPO from `orders_sum/orders`
- **AND** MUST emit `BLOCKED_BY_PRODUCT_PRICE_SOURCE`

### Requirement: ProductCpoResolver single owner

DRR→CPO calculation SHALL exist only in `ProductCpoResolver` (domain/application).

Formula when price and profile are available:

- `target_cpo_rub = effective_product_price × target_drr_percent / 100`
- `max_cpo_rub = effective_product_price × max_drr_percent / 100`

Rounding:

- `target_cpo_rub`: round half-up to 0.01 RUB
- `max_cpo_rub`: round half-up to integer RUB

Telegram, Excel, AI Package prompts, MCP, and campaign handlers MUST NOT embed
duplicate formulas.

#### Scenario: Missing price blocks derived CPO

- **GIVEN** enrolled product control and effective `DrrProfile`
- **AND** pricing reader returns unavailable
- **WHEN** `ProductCpoResolver` is invoked
- **THEN** result MUST be blocked with `BLOCKED_BY_PRODUCT_PRICE_SOURCE`
- **AND** MUST NOT fabricate zero CPO

### Requirement: Enrollment and zero default behavior

Default enrollment for shop and product MUST be `NOT_ENROLLED`.

Deploying schema/code without enrollment MUST NOT alter campaign runtime economics.

#### Scenario: Zero enrollment zero change

- **GIVEN** no shop or product rows with `ENROLLED`
- **WHEN** shop-runner executes a tick
- **THEN** `target_price_for_order` / `max_price_for_order` behavior MUST match pre-change legacy

### Requirement: Legacy vs blocked outcomes

`LEGACY_NOT_ENROLLED` SHALL apply when product control is not enrolled or no
effective DRR profile applies.

`PRODUCT_CONTROL_BLOCKED` SHALL apply when product control is explicitly enabled
and a safety rule prevents derivation (ambiguous multi-nm, missing price, explicit BLOCKED).

Blocked outcomes MUST NOT silently fall back to legacy campaign CPO.

#### Scenario: Explicit enroll with ambiguous multi-nm

- **GIVEN** shop or product control `ENROLLED`
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
- **AND** enrollment and price available
- **WHEN** resolving control product for the complex
- **THEN** control product MUST be `(shop_id, N)`

#### Scenario: Multi-nmid without authority

- **GIVEN** `nmids` = [N1, N2] on one complex
- **WHEN** product-derived CPO is requested under enrollment
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

### Requirement: ProductControlContextV1

The system SHALL define `ProductControlContextV1` documenting identity, category refs,
pricing and sales economics evidence, effective DRR, derived CPO, bindings, blockers,
capabilities, attribution references (opaque), and provenance.

This change MUST NOT implement AI Package or MCP export.
