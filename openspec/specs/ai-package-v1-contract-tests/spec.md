# ai-package-v1-contract-tests Specification

## Purpose

Contract tests and deterministic validator for AI Package v1 export (tests-first
gates for read-only semantics and manifest integrity). Synced from change
`ai-package-v1-contract` (archived 2026-10-01).
## Requirements
### Requirement: Validator is deterministic and transport-aware

A package validator MUST parse manifest + payloads, verify `sha256`, schema
version, required dataset cards, and coverage fields. Validator MUST NOT call
WB API or open network I/O in unit contract tests.

#### Scenario: Valid package passes

- **GIVEN** a ZIP built from golden fixtures
- **WHEN** validator runs
- **THEN** validation MUST pass with no errors

#### Scenario: Tampered payload fails

- **GIVEN** a ZIP with one payload byte changed
- **WHEN** validator runs
- **THEN** validation MUST fail with hash mismatch

### Requirement: Contract test — no WB on export path

Unit or integration contract tests MUST prove export/validator path does not
invoke WB API stack (mock/spy on `app/core/mp/wb/api` or export boundary hook).

#### Scenario: Export spy shows no WB calls

- **GIVEN** WB client layer is spied or denied
- **WHEN** export runs against test PG/CH
- **THEN** zero WB API calls MUST be recorded

### Requirement: Contract test — absent shop orders source UNKNOWN

Tests MUST assert shop product orders/sales dataset declares
`SOURCE_NOT_ASSIGNED` or `UNKNOWN` and contains no rows pretending to be
supplier orders/sales.

#### Scenario: Orders sales unassigned

- **WHEN** export completes
- **THEN** shop orders/sales source field MUST be `SOURCE_NOT_ASSIGNED` or
  `UNKNOWN`
- **AND** MUST NOT contain supplier-identity rows

### Requirement: Contract test — empty data not full coverage

Tests MUST assert empty campaign or funnel slices do not set package-level full
`coverage` without evidence.

#### Scenario: Empty campaign stat

- **GIVEN** no `full_adv_wb_stat` rows for P
- **WHEN** export completes
- **THEN** `coverage` MUST NOT be `FULL` for that dataset without explicit proof
- **AND** appropriate `reason_codes` MUST be present

### Requirement: Contract test — Auto Search campaign ids separated

Tests MUST use fixtures with distinct Auto and Search `campaign_id`s and assert
exported campaign stat rows remain distinguishable (no silent merge).

#### Scenario: Two campaign ids preserved

- **GIVEN** Auto id A and Search id K for same ComplexAdv
- **WHEN** campaign stat is exported
- **THEN** rows MUST include both A and K as separate `campaign_id`s
- **AND** MUST NOT replace them with a single synthetic id

### Requirement: Contract test — sha256 determinism

Tests MUST run export twice on frozen fixtures and compare manifest hashes.

#### Scenario: Repeatable manifest

- **GIVEN** frozen CH/PG fixtures and fixed clock
- **WHEN** export runs twice
- **THEN** manifest `sha256` entries MUST be identical

### Requirement: Contract test — shop isolation

Tests MUST run export for S1 and assert no S2 shop_id or foreign campaign ids
appear.

#### Scenario: Foreign shop excluded

- **GIVEN** CH rows for S1 and S2
- **WHEN** export runs for S1
- **THEN** no S2 `shop_id` or S2-only campaign ids MUST appear in outputs

### Requirement: Contract test — PG inventory not detailed settings snapshot

Tests MUST assert the `campaign_settings_snapshot` card (when present) reflects
minimal shop-scoped inventory/relations only: `PARTIAL` or `UNKNOWN` when
detailed settings are unavailable, and MUST NOT assert full field-level
advertising settings export (deferred to change
`ai-package-campaign-settings-snapshot`).

#### Scenario: Inventory card partial semantics

- **WHEN** export completes with PG inventory materialized or explicitly UNKNOWN
- **THEN** manifest MUST NOT claim FULL detailed campaign settings coverage
- **AND** card metadata MUST NOT imply v1 includes the future detailed settings
  snapshot change
