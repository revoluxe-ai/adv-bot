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
