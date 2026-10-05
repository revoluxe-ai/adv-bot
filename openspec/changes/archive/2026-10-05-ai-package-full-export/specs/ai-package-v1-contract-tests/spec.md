## ADDED Requirements

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
