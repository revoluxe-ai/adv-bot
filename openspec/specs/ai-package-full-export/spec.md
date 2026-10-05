# ai-package-full-export Specification

## Purpose
TBD - created by archiving change ai-package-full-export. Update Purpose after archive.
## Requirements
### Requirement: PackageZipAssembler is the ZIP authority

ZIP production MUST flow `ExportService` → optional family gaps payload →
`encode_package`. A second exporter MUST NOT be introduced.

#### Scenario: Single orchestration path

- **WHEN** full package ZIP is built
- **THEN** `ExportService` MUST run first for domain payloads
- **AND** `PackageZipAssembler` MUST NOT duplicate dataset readers

### Requirement: PACKAGE_FAMILY_GAPS.json

Full ZIP MUST include root `PACKAGE_FAMILY_GAPS.json` listing families with
`status: GAP` and `reason_codes` for families not materialized in v1 export
(campaign settings history, supplier shop orders/sales feed, store DRR,
prices/stocks, finance, discovery).

#### Scenario: Explicit gap not silent success

- **WHEN** a family is absent from export payloads
- **THEN** gaps file MUST name the family with GAP status
- **AND** MUST NOT imply FULL coverage for that family

### Requirement: One shop one ZIP

CLI and assembler MUST accept exactly one `shop_id` per invocation.

#### Scenario: Shop isolation preserved

- **WHEN** export runs for shop S
- **THEN** manifest `shop_id` MUST reference only S

