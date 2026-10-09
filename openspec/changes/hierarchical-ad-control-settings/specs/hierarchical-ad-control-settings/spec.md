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

### Requirement: Price semantics boundary

Foundation MUST NOT perform authoritative price-dependent CPO production actuation
while `PRICE_SEMANTICS_ACCEPTED = NO`.

#### Scenario: Diagnostics proposal blocked

- **GIVEN** diagnostic build with valid configured DRR
- **WHEN** proposed CPO is requested semantically
- **THEN** `proposed_max_cpo_rub` MUST be withheld with
  `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`

### Requirement: Versioned persistence identity

Configured shop and campaign policy MUST be stored with identity
`(scope, feature_id, schema_version)`; JSONB MUST be decoded only through the
domain registry validators.

#### Scenario: Shop row round-trip

- **GIVEN** ENABLED `DRR_POLICY` payload at shop scope
- **WHEN** payload is encoded to JSONB and decoded
- **THEN** typed payload MUST match registry validation for schema_version 1

### Requirement: Ad control ChangeSet dry-run

`AdControlChangeSetV1` mutations MUST be validated by
`validate_ad_control_changeset` without PostgreSQL or WB writes.

#### Scenario: Stale state_token rejected

- **GIVEN** an existing shop feature snapshot with `state_token` `acs_live`
- **WHEN** a ChangeSet presents `acs_wrong` for the same feature
- **THEN** dry-run MUST return `REJECTED` with `STATE_TOKEN_STALE`
