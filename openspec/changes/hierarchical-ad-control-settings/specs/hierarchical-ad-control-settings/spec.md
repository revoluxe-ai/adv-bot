# hierarchical-ad-control-settings Specification (foundation)

## Purpose

Normative semantics for hierarchical advertising automation settings:
per-function modes at SHOP and CAMPAIGN, live inheritance, DRR triple separation,
headroom eligibility, diagnostics contract. Slice B adds configured persistence and
ChangeSet dry-run; runtime shop-runner and UI remain out of scope.

## ADDED Requirements

### Requirement: Hierarchical enrollment fail-closed

When `HierarchicalEnrollment` is `NOT_ENROLLED`, the hierarchical resolver MUST
fail closed with `NOT_ENROLLED_FAIL_CLOSED`.

Legacy behavior MUST only use explicit `LEGACY_PASSTHROUGH` and MUST NOT appear as
hierarchical inheritance.

#### Scenario: Not enrolled blocks hierarchical resolve

- **GIVEN** `NOT_ENROLLED` and `HIERARCHICAL` control path
- **WHEN** `AdControlSettingsResolver.resolve_feature` runs
- **THEN** outcome MUST be blocked with `NOT_ENROLLED_FAIL_CLOSED`

### Requirement: Live campaign DRR inheritance

Campaign `INHERIT` for `DRR_POLICY` MUST resolve the current shop configured target
without persisting shop values on the campaign configuration row.

#### Scenario: Shop target change affects inherit campaign

- **GIVEN** campaign A `DRR_POLICY` mode `INHERIT` and shop target 15%
- **WHEN** shop target changes to 13% without campaign row changes
- **THEN** resolved configured target for campaign A MUST be 13%

### Requirement: Per-function independence

Each V1 feature MUST support independent `INHERIT` | `OVERRIDE` | `DISABLED` at
campaign scope where the feature supports `CAMPAIGN`.

#### Scenario: Campaign override fixed while shop changes

- **GIVEN** campaign B `OVERRIDE` configured target 8% and shop 13%
- **WHEN** shop target changes
- **THEN** campaign B configured target MUST remain 8%

### Requirement: Stale actual DRR blocks control action

When `actual_drr` data sufficiency is not `SUFFICIENT`, the controller MUST NOT
emit new control actions from hierarchical evidence.

#### Scenario: Stale blocks action

- **GIVEN** `actual_drr` sufficiency `STALE`
- **WHEN** `control_action_allowed` runs
- **THEN** result MUST be disallowed with `ACTUAL_DRR_STALE`

### Requirement: Price semantics boundary (Slice A foundation)

Slice A catalog-price CPO diagnostics MUST remain fail-closed while
`CATALOG_PRICE_SEMANTICS_ACCEPTED = NO`. V1 order-value acceptance on stage MUST
NOT imply catalog-price authority. Slice B MUST NOT perform runtime CPO actuation.

#### Scenario: Catalog-price CPO actuation still blocked in foundation diagnostics

- **GIVEN** diagnostic build without accepted catalog-price semantics
- **WHEN** proposed CPO is requested on catalog-price authority
- **THEN** proposal MUST remain blocked with an explicit reason code

### Requirement: Configured persistence logical identity

Configured shop and campaign policy MUST persist exactly one authoritative row per
logical feature slot. Shop identity MUST be `(shop_id, feature_id)`. Campaign
identity MUST be `(shop_id, advert_id, feature_id)`. `schema_version` MUST be stored
on that row as an attribute only and MUST NOT be part of logical identity.
Unsupported or newer `schema_version` values MUST fail closed. Multiple rows for one
feature solely because schema versions differ MUST be forbidden. JSONB MUST be decoded
only through domain registry validators.

#### Scenario: Shop row round-trip

- **GIVEN** ENABLED `DRR_POLICY` payload at shop scope
- **WHEN** payload is encoded to JSONB and decoded
- **THEN** typed payload MUST match registry validation for schema_version 1

### Requirement: Ad control ChangeSet dry-run

`AdControlChangeSetV1` mutations MUST be validated by
`validate_ad_control_changeset` without PostgreSQL or WB writes. Concurrency authority
MUST be `expected_revision` only; `state_token` MUST remain a semantic fingerprint for
snapshots and diagnostics and MUST NOT be a second CAS precondition.

#### Scenario: Stale revision rejected

- **GIVEN** an existing shop feature snapshot at authoritative revision `N`
- **WHEN** a ChangeSet presents `expected_revision` not equal to `N`
- **THEN** dry-run MUST return `REJECTED` with `REVISION_CONFLICT`

#### Scenario: Absent row with revision precondition

- **GIVEN** no authoritative row for the feature slot
- **WHEN** a ChangeSet presents `expected_revision` that is not null
- **THEN** dry-run MUST return `REJECTED` with `REVISION_CONFLICT`

#### Scenario: Existing row without create revision

- **GIVEN** an authoritative row exists for the feature slot
- **WHEN** a ChangeSet presents `expected_revision` null
- **THEN** dry-run MUST return `REJECTED` with `REVISION_CONFLICT`
