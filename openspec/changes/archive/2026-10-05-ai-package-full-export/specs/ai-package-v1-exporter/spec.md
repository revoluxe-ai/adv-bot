## ADDED Requirements

### Requirement: Full package ZIP via PackageZipAssembler

Operator full export MUST use `PackageZipAssembler` calling existing
`ExportService` and `encode_package`.

#### Scenario: ExportService remains sole dataset authority

- **WHEN** `PackageZipAssembler.assemble_zip` runs
- **THEN** all dataset payloads MUST originate from `ExportService.export`
- **AND** MUST NOT invoke a parallel exporter

### Requirement: Family gaps manifest file

Full ZIP MUST list `PACKAGE_FAMILY_GAPS.json` in manifest file descriptors
with deterministic content for identical export inputs.

#### Scenario: Gaps file hashed in manifest

- **WHEN** full ZIP is validated
- **THEN** `PACKAGE_FAMILY_GAPS.json` sha256 MUST match manifest entry
