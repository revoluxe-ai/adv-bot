# ai-package-v1-exporter Specification (delta)

## ADDED Requirements

### Requirement: Keyword performance datasets in ExportService

`ExportService` MUST integrate keyword performance datasets under logical prefix
`keyword_performance/` as part of the single AI Package export. A second exporter
MUST NOT be introduced.

#### Scenario: Keyword datasets in same manifest

- **GIVEN** keyword export enabled for shop S
- **WHEN** `ExportService.export` completes
- **THEN** manifest MUST list keyword dataset cards alongside existing v1 datasets
- **AND** MUST NOT require separate export invocation

#### Scenario: ExportService remains sole authority

- **WHEN** AI Package ZIP is produced for keyword feature
- **THEN** orchestration MUST flow through `ExportService`
- **AND** MUST NOT use standalone script as sole authority

### Requirement: DATA_MAP and coverage root files in manifest

Export MUST emit `DATA_MAP.json` and `coverage.json` as manifest payload files with
sha256 descriptors. Tampered DATA_MAP MUST fail validation.

#### Scenario: DATA_MAP in file descriptors

- **WHEN** export completes with keyword feature
- **THEN** manifest.files MUST include DATA_MAP.json sha256
- **AND** validator MUST verify hash on decode

### Requirement: Keyword history bounds documented vs ExportPeriod

Manifest `period` MUST continue describing caller bounds for legacy datasets.
Keyword datasets MUST document `all_available` bounds separately in DATA_MAP and
coverage metadata.

#### Scenario: Dual bounds documented

- **WHEN** DATA_MAP emitted
- **THEN** MUST contain `export_period_bounds` and `keyword_history_bounds` sections
- **AND** keyword_history_bounds MUST reflect CH MIN/MAX not ExportPeriod clip

### Requirement: Default keyword assembler in ExportService

`ExportService` MUST default-build `KeywordPerformanceAssembler` when the
constructor param is omitted — same pattern as `CampaignSettingsAssembler`
(`export_service.py:93-98`). Default export MUST include keyword datasets using
real read-only readers.

#### Scenario: Default export includes keyword datasets

- **GIVEN** production wiring constructs `ExportService()` without keyword params
- **WHEN** export completes for a shop with keyword history
- **THEN** manifest MUST list keyword dataset cards and payloads
- **AND** MUST NOT require optional feature flag opt-in

### Requirement: Constructor-injected keyword seams for tests

ExportService MUST accept optional constructor-injected keyword readers/assemblers
so unit tests use fake CH/Redis without live stores.

#### Scenario: Fake keyword reader in unit test

- **GIVEN** test injects fake `KeywordPerformanceAssembler`
- **WHEN** export runs
- **THEN** MUST NOT open real ClickHouse client for keyword path

### Requirement: Legacy export tests inject keyword fakes

Existing ExportService integration tests MUST inject explicit fake keyword
assemblers/readers to avoid live CH/Redis — same obligation as fake settings
assemblers today. Silent keyword omission is forbidden.

#### Scenario: Legacy integration test uses fake keyword assembler

- **GIVEN** test constructs ExportService with fake settings assembler (existing pattern)
- **WHEN** test also injects fake keyword assembler
- **THEN** export MUST produce existing dataset cards without error
- **AND** MUST NOT open live CH/Redis for keyword path
