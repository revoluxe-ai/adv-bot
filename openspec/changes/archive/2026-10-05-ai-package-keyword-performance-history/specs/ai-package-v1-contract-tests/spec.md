# ai-package-v1-contract-tests Specification (delta)

## ADDED Requirements

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
