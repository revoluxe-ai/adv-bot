# ai-package-full-export — contract repair delta

## MODIFIED Requirements

### Requirement: PACKAGE_FAMILY_GAPS.json

Full ZIP MUST include root `PACKAGE_FAMILY_GAPS.json` listing families with
`family_status: GAP` (canonical `FamilyStatus` token) and `reason_codes` for
families not materialized in v1 export.

#### Scenario: Explicit gap not silent success

- **WHEN** a family is absent from export payloads
- **THEN** gaps file MUST name the family with `family_status` GAP
- **AND** MUST NOT use legacy `status` key without `family_status`

### Requirement: PackageZipAssembler is the ZIP authority

ZIP production MUST flow `ExportService` → family gaps → package summary →
`encode_package`. Determinism contract is `PAYLOAD_HASH_ONLY` (per-file content
sha256); byte-identical ZIP archives are NOT required in this change.

#### Scenario: Single orchestration path

- **WHEN** full package ZIP is built
- **THEN** `ExportService` MUST run first for domain payloads
- **AND** `PackageZipAssembler` MUST NOT duplicate dataset readers

## ADDED Requirements

### Requirement: PACKAGE_SUMMARY.json

Full ZIP MUST include root `PACKAGE_SUMMARY.json` as a deterministic index:
package schema version, shop identity, export period, per exported family and
every gap-catalog family, canonical `family_status`, join keys, missing≠zero
semantics, and pointers under `keyword_performance/` for keyword payloads.

#### Scenario: Gap catalog mirrored in summary

- **WHEN** `PACKAGE_FAMILY_GAPS.json` lists catalog families
- **THEN** `PACKAGE_SUMMARY.json` MUST include each catalog `family_id`
- **AND** GAP families MUST NOT publish `row_count: 0` (omit count; 0 means observed zero)

#### Scenario: Keyword family lists real dataset cards

- **WHEN** keyword export is present
- **THEN** `keyword_performance` summary entry MUST list keyword `dataset_ids`
- **AND** data pointers MUST use `keyword_performance/*.jsonl` paths

#### Scenario: Manifest dataset cards expose family_status

- **WHEN** manifest datasets are serialized
- **THEN** each dataset card MUST include `family_status` from canonical enum
- **AND** unknown tokens MUST fail closed at validation

### Requirement: Authoritative shop identity

Full export MUST preserve authoritative `WBCabinet.shop_id` as `shop_id: str`
with no numeric coercion, hash surrogate, or second hidden identifier.

#### Scenario: UUID shop id roundtrip

- **WHEN** export is requested for a UUID-like `WBCabinet.shop_id`
- **THEN** `manifest.shop_id` MUST equal that exact string
- **AND** campaign, funnel, and keyword payload `shop_id` values MUST equal it
- **AND** `PACKAGE_SUMMARY.json` `shop_id` MUST equal it
- **AND** package validation MUST accept the package

#### Scenario: Blank shop id fails closed

- **WHEN** `shop_id` is empty or whitespace-only
- **THEN** export input validation MUST fail before package production

### Requirement: Missing campaign leg is not a synthetic merge

A missing Auto or Search physical leg MUST NOT be treated as a synthetic merge
or as a zero-valued row. An unexpected `campaign_id` MUST fail closed. A
non-empty proper subset of expected physical ids MUST stay partial coverage
with `PARTIAL_COLLECTION`.

#### Scenario: Both physical ids present

- **GIVEN** rows for Auto id A and Search id K
- **WHEN** campaign stat is exported
- **THEN** the payload MUST contain both A and K as separate `campaign_id`s
- **AND** MUST NOT replace them with one synthetic id

#### Scenario: Only Auto rows exist

- **GIVEN** PG scope has distinct Auto id A and Search id K
- **AND** the campaign-stat slice contains rows only for A
- **WHEN** campaign stat is exported
- **THEN** export MUST succeed
- **AND** the payload MUST contain A and MUST NOT contain a fabricated K row
- **AND** campaign coverage MUST NOT be `FULL` or family `COMPLETE`
- **AND** reason metadata MUST include `PARTIAL_COLLECTION`

#### Scenario: Only Search rows exist

- **GIVEN** PG scope has distinct Auto id A and Search id K
- **AND** the campaign-stat slice contains rows only for K
- **WHEN** campaign stat is exported
- **THEN** export MUST succeed
- **AND** the payload MUST contain K and MUST NOT contain a fabricated A row

#### Scenario: Neither physical id has rows

- **GIVEN** PG scope has distinct Auto and Search ids
- **AND** the campaign-stat slice is empty
- **WHEN** campaign stat is exported
- **THEN** the payload MUST NOT contain fabricated zero rows
- **AND** campaign coverage MUST NOT be `FULL` or family `COMPLETE`

#### Scenario: Unexpected campaign id rejected

- **GIVEN** a row whose `campaign_id` is not a permitted physical adv_id
- **WHEN** campaign stat is exported
- **THEN** export MUST fail closed
- **AND** MUST NOT emit that id as a campaign row
