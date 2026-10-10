# product-control-context Specification

## Purpose

Normative **foundation** semantics for product-oriented control delivered in
`app/modules/product_control/` (Slices A–B): identity, enrollment/mode vocabulary,
pure DRR/CPO resolvers, pricing/economics port separation, and read-only campaign
binding projection. Persistence, runtime adapters, and surfaces are out of scope;
see `openspec/evolution/product-control-context-future-boundaries.md`.
## Requirements
### Requirement: Product control identity

The foundation SHALL model canonical control identity as **`(shop_id, nmid)`**
via `ProductRef`.

WBCard SHALL remain catalog/metadata authority and MUST NOT store mutable control
fields in this foundation.

#### Scenario: Catalog vs control separation (design invariant)

- **GIVEN** catalog data for `nmid` N in shop S
- **WHEN** mutable product control is introduced in a future persistence change
- **THEN** control settings MUST NOT be stored on `WBCard`

### Requirement: Enrollment and mode vocabulary

`ShopControlEnrollment` SHALL be `NOT_ENROLLED` | `ENROLLED` | `BLOCKED`
(default `NOT_ENROLLED`).

`ProductControlMode` SHALL be `INHERIT_SHOP` | `OVERRIDE_ENABLED` | `BLOCKED`
(default `INHERIT_SHOP`).

`EffectiveControlResolver` SHALL implement the owner enrollment matrix as pure logic
without I/O.

#### Scenario: Shop master gate blocks product override (S19)

- **GIVEN** `ShopControlEnrollment` `NOT_ENROLLED` and product `OVERRIDE_ENABLED` with profile
- **WHEN** `EffectiveControlResolver.resolve` runs
- **THEN** outcome MUST be `LEGACY_NOT_ENROLLED`

#### Scenario: Shop blocked overrides product modes (S20)

- **GIVEN** `ShopControlEnrollment` `BLOCKED`
- **WHEN** `EffectiveControlResolver.resolve` runs
- **THEN** outcome MUST be `PRODUCT_CONTROL_BLOCKED`

#### Scenario: Override without profile fails closed (S21)

- **GIVEN** shop `ENROLLED` and `OVERRIDE_ENABLED` without product `DrrProfile`
- **WHEN** `EffectiveControlResolver.resolve` runs
- **THEN** outcome MUST be `INVALID_CONFIGURATION` / blocked

### Requirement: DrrProfile atomic inheritance (pure resolver)

`DrrProfile` construction MUST enforce both percent fields and
`max_drr_percent >= target_drr_percent`.

`EffectiveControlResolver` SHALL inherit **whole profiles** only (no field-level mix).

#### Scenario: Shop profile for INHERIT_SHOP (S07)

- **GIVEN** shop `ENROLLED` with shop profile P and product `INHERIT_SHOP`
- **WHEN** resolver runs
- **THEN** effective profile MUST equal P

#### Scenario: LEGACY tier without profiles (S09)

- **GIVEN** shop `ENROLLED`, `INHERIT_SHOP`, no shop or product profile
- **WHEN** resolver runs
- **THEN** outcome MUST be `LEGACY_TIER`

#### Scenario: Invalid profile rejected at construction (S10)

- **GIVEN** `target_drr_percent` > `max_drr_percent`
- **WHEN** constructing `DrrProfile`
- **THEN** construction MUST fail closed

### Requirement: Pricing vs sales economics ports

`ProductPricingReader` and `ProductSalesEconomicsReader` SHALL remain separate
protocols (ports only in foundation).

#### Scenario: Port boundary (S16)

- **GIVEN** foundation module layout
- **WHEN** reviewing control price vs historical economics
- **THEN** `ProductSalesEconomicsReader` MUST NOT substitute for `ProductPricingReader`

### Requirement: ProductCpoResolver pure math

`ProductCpoResolver` SHALL compute `target_cpo_rub` and `max_cpo_rub` at 0.01 RUB
ROUND_HALF_UP when price and profile are provided.

Missing, zero, or negative effective price MUST fail closed with
`BLOCKED_BY_PRODUCT_PRICE_SOURCE`.

#### Scenario: Canonical money (S22)

- **GIVEN** valid profile and positive effective price
- **WHEN** `ProductCpoResolver.resolve` runs
- **THEN** outputs MUST be quantized to 0.01 RUB

### Requirement: ProductCpoResolver scope boundary (price-based path)

`ProductCpoResolver` is canonical for the **product price-based** CPO path
(`ProductPricingReader` → effective unit price × `DrrProfile`).

Implementations MUST NOT treat `ProductCpoResolver` as authority for **V1
hierarchical campaign** `TARGET_CPO_RUB`. That semantics is defined only in
`openspec/decisions/drr-cpo-price-semantics/decision.md` (DIRECT attributed order
value × effective target DRR). This foundation spec does not add hierarchical
runtime requirements.

#### Scenario: Resolver not V1 campaign TARGET_CPO authority (S23)

- **GIVEN** a V1 hierarchical campaign control consumer needs `TARGET_CPO_RUB`
- **WHEN** sourcing economic target semantics
- **THEN** consumer MUST use `drr-cpo-price-semantics` order-value rules
- **AND** MUST NOT use `ProductCpoResolver` output as substitute authority

### Requirement: CampaignProductBinding projector

`CampaignProductBindingProjector` SHALL emit distinct Auto and Search bindings with
separate physical `adv_id` values.

PRIMARY membership MUST require explicit evidence; `main_nmid` MUST NOT be authority.

#### Scenario: Auto and Search legs (S01)

- **GIVEN** Auto and Search legs for one nmid
- **WHEN** projector runs
- **THEN** bindings MUST include both `LegRole.AUTO` and `LegRole.SEARCH`

#### Scenario: One product multiple complexes (S02)

- **GIVEN** same nmid on two complexes
- **WHEN** projector runs per complex
- **THEN** distinct physical adv bindings MUST result

#### Scenario: main_nmid not PRIMARY (S05)

- **GIVEN** multiple nmids on a leg
- **WHEN** projector runs
- **THEN** membership MUST be `UNKNOWN`, not PRIMARY from sorted first nmid

#### Scenario: Search physical id (S17)

- **GIVEN** Search paired `AdvSetting` and auto `search_adv_id` linkage
- **WHEN** projector runs
- **THEN** Search binding physical id MUST equal paired Search `adv_id`, not linkage id

### Requirement: Multi-nmid control product policy

`resolve_control_product_for_complex` SHALL resolve a single nmid; fail closed on
empty or ambiguous membership without authoritative control nmid.

#### Scenario: Single-nmid safe resolve (S03)

- **GIVEN** exactly one unique nmid in membership
- **WHEN** policy runs
- **THEN** control product MUST be `(shop_id, nmid)`

