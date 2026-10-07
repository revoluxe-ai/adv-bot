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

### Requirement: Contract test — keyword export deterministic hash

Tests MUST run keyword-inclusive export twice on frozen fake fixtures and compare
manifest and DATA_MAP sha256 hashes.

#### Scenario: Repeatable keyword manifest hash

- **GIVEN** frozen keyword fixture via injected fake readers
- **WHEN** export runs twice with same generated_at
- **THEN** manifest sha256 and DATA_MAP sha256 MUST match

### Requirement: Contract test — tampered DATA_MAP detected

Validator MUST fail when DATA_MAP.json bytes altered post-export.

#### Scenario: DATA_MAP tamper fails validation

- **GIVEN** valid keyword export ZIP
- **WHEN** one byte in DATA_MAP.json is changed
- **THEN** `validate_zip_package` MUST fail with hash mismatch

### Requirement: Contract test — keyword path no WB calls

Keyword export contract tests MUST spy/deny WB API same as existing v1 export tests.

#### Scenario: Keyword export zero WB calls

- **GIVEN** WB layer spied
- **WHEN** keyword-inclusive export runs with fakes
- **THEN** zero WB API calls MUST be recorded

### Requirement: Contract test — keyword path no store writes

Tests MUST assert keyword export performs no PG INSERT/UPDATE and no Redis writes.

#### Scenario: No PG Redis writes on keyword export

- **GIVEN** PG/Redis write trackers or mocks
- **WHEN** keyword export runs
- **THEN** no mutating PG/Redis operations MUST occur

### Requirement: Contract test — full history not period-clipped

Contract test MUST assert keyword daily dates extend beyond ExportPeriod bounds when
fixtures contain wider history still within package cutoff.

#### Scenario: Dates beyond period end present within cutoff

- **GIVEN** fake daily reader returns rows through 2025-06-15
- **AND** ExportPeriod is 2025-01-01..2025-03-31
- **AND** `generated_at` is 2026-01-08T15:00:00Z
- **WHEN** export completes
- **THEN** keyword payload MUST include 2025-06-15 rows
- **AND** MUST NOT stop at ExportPeriod.end (2025-03-31)

### Requirement: Contract test — rebound scope expansion

Test MUST assert CH query adv_id filter includes rebound id from fake Redis reader.

#### Scenario: Rebound adv_id in query scope

- **GIVEN** fake rebound reader returns historical adv_id H
- **WHEN** keyword scope built
- **THEN** assembled scope adv_ids MUST contain H

### Requirement: Contract test — spend not fabricated

Test MUST assert NULL spend stays null with UNAVAILABLE status.

#### Scenario: Null spend contract

- **GIVEN** fixture row views>0 cpm>0 spend=null
- **WHEN** daily row encoded
- **THEN** spend_rub MUST be null and status UNAVAILABLE

### Requirement: Contract test — missing position not zero

Test MUST assert absent position does not serialize as 0.0.

#### Scenario: Null position contract

- **GIVEN** fixture without position
- **WHEN** daily row encoded
- **THEN** position field MUST NOT equal 0.0 as synthetic default

### Requirement: Contract test — default export includes keyword cards

Test MUST assert `ExportService()` default wiring includes keyword manifest cards
when fake scope/history fixtures are injected at assembler boundary.

#### Scenario: Default keyword cards present

- **GIVEN** ExportService constructed with default keyword assembler and fakes at reader boundary
- **WHEN** export completes
- **THEN** manifest MUST include keyword dataset cards

### Requirement: Contract test — package cutoff enforced

Test MUST assert keyword dates beyond `generated_at` UTC date and same-day rows with
`timestamp > generated_at` (daily/decision streams) or `version > cutoff_instant_ms`
(WB position stream — proven UTC epoch ms writer) are excluded from bounds and
payloads where source supports instant cutoff.

#### Scenario: Cutoff excludes future fixture dates

- **GIVEN** fake reader returns rows on 2026-03-01
- **AND** `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** export completes
- **THEN** keyword payloads MUST NOT include 2026-03-01 rows

#### Scenario: Cutoff excludes same-day post-instant rows

- **GIVEN** fake reader returns row with `date=2026-01-07` and `timestamp=2026-01-07T15:00:00Z`
- **AND** `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** export completes
- **THEN** keyword payloads MUST NOT include that row

#### Scenario: Cutoff excludes same-day post-instant position rows (version ms)

- **GIVEN** fake position reader returns row with `date=2026-01-07` and `version`
  equal to UTC epoch ms for `2026-01-07T15:00:00Z`
- **AND** `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** export completes
- **THEN** keyword position payloads MUST NOT include that row

### Requirement: PackageZipAssembler contract tests

Unit tests MUST inject fake `ExportService` or scope/reader fakes at assembler
boundary; MUST NOT require live CH/PG/Redis.

#### Scenario: Validator accepts full ZIP from assembler

- **GIVEN** fakes at ExportService boundary
- **WHEN** `PackageZipAssembler.assemble_zip` runs
- **THEN** `validate_zip_package` MUST pass
- **AND** gaps file MUST be present

### Requirement: CLI does not invoke WB API

`scripts/ai_package_v1_export.py` MUST NOT import WB HTTP clients on default path.

#### Scenario: CLI module import boundary

- **WHEN** CLI module is loaded in unit test
- **THEN** WB promotion client modules MUST NOT be imported

### Requirement: Contract tests for window semantics

Контрактные проверки MUST покрывать номинальные границы окон, агрегаты 1, 3, 7, 14, 30, 90, 180 и 365 дней, идентичность ног Auto и Search и охват пакета отдельно от расхода всего магазина. Проверки MUST NOT требовать записи в WB.

#### Scenario: Tampered analysis contract fails validation

- **GIVEN** пакет с аналитическим контрактом
- **WHEN** байты контракта изменены после сборки
- **THEN** проверка пакета MUST завершиться неуспехом

### Requirement: Contract tests for fail-closed economics

Проверки MUST покрывать изоляцию прямой и связанной областей, несопоставимое сравнение, версии пакета и контракта и одинаковый доменный результат на шве транспорта.

#### Scenario: Uncomputable economics are not numeric

- **GIVEN** нет фактов атрибуции и нет выручки магазина
- **WHEN** проверка читает окно ноги и агрегат охвата пакета
- **THEN** прямые и связанные экономические метрики и DRR магазина MUST быть невычислимы
- **AND** расход всего магазина MUST быть невычислим
- **AND** MUST NOT быть числом ноль
