## MODIFIED Requirements

### Requirement: Contract test — PG inventory not detailed settings snapshot

Tests MUST assert the `campaign_settings_snapshot` card (when present) reflects
minimal shop-scoped inventory/relations only **when detailed snapshot export is
not implemented**. When change `ai-package-campaign-settings-snapshot` is
implemented, contract tests MUST additionally assert detailed settings semantics:
`CampaignSettingsSnapshotV1` payload shape, separate Auto/Search legs, explicit
authority/provenance, and fail-closed UNKNOWN handling — and MUST NOT assert full
field-level advertising settings export from minimal inventory-only fixtures.

#### Scenario: Inventory card partial semantics before detailed export

- **GIVEN** detailed snapshot implementation is not active
- **WHEN** export completes with PG inventory materialized or explicitly UNKNOWN
- **THEN** manifest MUST NOT claim FULL detailed campaign settings coverage
- **AND** card metadata MUST NOT imply v1 includes the future detailed settings
  snapshot change

#### Scenario: Detailed settings contract tests when implemented

- **GIVEN** detailed campaign settings snapshot export is active
- **WHEN** contract tests run on golden fixtures with Auto id A and Search id K
- **THEN** payload MUST use `CampaignSettingsSnapshotV1` schema
- **AND** MUST include distinguishable auto and search leg sections
- **AND** MUST NOT equal a serialized `CampaignResourceSnapshotV1` or
  `AdvSettingsSnapshotDTO` document
- **AND** unknown or null authoritative fields MUST remain explicit without fabricated defaults

## ADDED Requirements

### Requirement: Contract test — settings export path has no WB API

Contract tests for detailed campaign settings snapshot MUST prove the settings
assembler/export path does not invoke WB API stack (mock/spy on WB client layer
or export boundary hook).

#### Scenario: Settings export spy shows no WB calls

- **GIVEN** WB client layer is spied or denied
- **WHEN** export builds detailed `campaign_settings_snapshot`
- **THEN** zero WB API calls MUST be recorded on the settings export path

### Requirement: Contract test — settings snapshot non-aliasing

Contract tests MUST assert export does not alias operational or control-plane DTOs
as the AI Package settings contract.

#### Scenario: Payload type guard

- **GIVEN** export produces detailed settings payload bytes
- **WHEN** validator parses domain JSON
- **THEN** root schema version MUST identify `CampaignSettingsSnapshotV1`
- **AND** parsed document MUST NOT validate as `CampaignResourceSnapshotV1`
- **AND** MUST NOT validate as `AdvSettingsSnapshotDTO` array/object schema
