## MODIFIED Requirements

### Requirement: Corpus identity stays immutable and separate from applied state

The system MUST treat the canonical ClickHouse migration corpus of this database as exactly versions `001`, `002`, `003`, `004`, `005`, and reviewed schema version `006`, and MUST keep corpus identity separate from applied state. Identity is the version id, reviewed filename, privilege class derived from SQL text, and SHA-256 of raw file bytes with no newline normalization and no comment stripping. The system MUST NOT rewrite accepted bytes of `001`–`006`. Accepting a file into the corpus MUST NOT execute its SQL. Presence of a file, and `IF NOT EXISTS` inside schema DDL, MUST NOT be a record that the version was applied. The system MUST NOT store applied state as a file in git or as a PostgreSQL row.

#### Scenario: Register the existing corpus without executing it

- **GIVEN** versions `001` through `006` already exist as reviewed manual SQL and no target ledger is attached
- **WHEN** the control plane accepts that corpus
- **THEN** it MUST record each version id, filename, privilege class, and raw-byte SHA-256
- **AND** MUST classify `005` as privileged grant and `006` as schema DDL
- **AND** MUST NOT change the SQL bytes
- **AND** MUST NOT execute any statement
- **AND** MUST NOT record any version as applied

#### Scenario: Register reviewed 001 through 006 without execution
- **GIVEN** reviewed versions `001` through `006` exist and no target ledger is attached
- **WHEN** the control plane accepts the corpus
- **THEN** it MUST record version id, filename, privilege class, and raw-byte SHA-256 for every version
- **AND** MUST classify `005` as privileged grant and `006` as schema DDL
- **AND** MUST NOT execute any statement
- **AND** MUST NOT record any version as applied

#### Scenario: File presence is not applied state

- **GIVEN** the corpus files are present and `001`–`004` contain `IF NOT EXISTS`
- **WHEN** an operator asks whether those versions are applied on a target
- **THEN** the system MUST NOT answer from the files or from `IF NOT EXISTS`
- **AND** MUST answer only from target ledger state
- **AND** MUST NOT write a `version_applied` event for that reason
### Requirement: Plan does not execute and apply needs explicit authorization

The system MUST keep status, validation, planning, and apply semantics unchanged except that reviewed schema DDL `006` is eligible wherever reviewed schema DDL `001`–`004` is eligible. Plan MUST remain read-only. Apply MUST still require explicit isolated target config, explicit coordinator config, apply authorization, matching checksum, sanctioned baseline, non-partial state, and held advisory lock. `005` MUST remain non-success for the schema writer.

#### Scenario: Plan includes reviewed 006 without execution
- **GIVEN** reviewed corpus `001`–`006`
- **WHEN** the operator requests a plan
- **THEN** the plan MUST include `006` in version order with its privilege class, checksum, statements, and stop reason when applicable
- **AND** MUST NOT execute SQL
- **AND** MUST NOT write target state
- **AND** MUST NOT acquire a writer lock

#### Scenario: Schema writer may run reviewed 006 under existing gates
- **GIVEN** an isolated target satisfies every existing schema-apply gate and reviewed `006` is not partial or applying
- **WHEN** authorized apply reaches `006`
- **THEN** the schema writer MUST execute `006` as schema DDL
- **AND** MUST use the same apply_started → statement_ok → version_applied event protocol
- **AND** MUST NOT execute `005`

#### Scenario: Apply without authorization still refuses
- **GIVEN** reviewed `006` is otherwise eligible
- **WHEN** apply authorization is absent
- **THEN** apply MUST refuse before executing `006`

### Requirement: Privileged grant 005 never enters the schema writer

`005` MUST remain a privileged GRANT and MUST NOT be executed by the schema writer. Reviewed `006` MUST be classified separately as schema DDL. The reviewed schema DDL versions `001`–`004` and `006` MUST keep default database qualification, while `005` keeps its system-object qualification.

#### Scenario: Authorized apply still refuses 005
- **GIVEN** the target satisfies schema-apply gates
- **WHEN** apply reaches `005`
- **THEN** the system MUST refuse before the schema writer receives `005`
- **AND** `005` MUST NOT be executed

#### Scenario: Qualification stays in reviewed SQL
- **GIVEN** reviewed bytes `001`–`006`
- **WHEN** the corpus is validated
- **THEN** schema DDL `001`–`004` and `006` MUST retain default database qualification
- **AND** `005` MUST retain its system-object qualification
- **AND** validation MUST NOT rewrite those files
### Requirement: This change mutates only an isolated target and does not touch production

This change MUST keep all existing isolated-target safety rules for migration mutation. `ensure-ledger`, authorized reconcile, and authorized schema apply MUST operate only through the migration control plane and its exclusive coordinator. Reviewed `006` is added to the same isolated schema-apply surface as `001`–`004`. Production target class MUST continue to refuse before target mutation. Tests MUST prove the behavior with substituted migration target/coordinator seams and MUST NOT rely on a live production connection or the application ClickHouse client.

#### Scenario: Isolated apply includes reviewed 006
- **GIVEN** an isolated test target and coordinator satisfy all migration gates
- **WHEN** authorized apply reaches reviewed `006`
- **THEN** the runner MUST execute its schema DDL and close it with `version_applied` only after all statements succeed
- **AND** the production target MUST remain untouched

#### Scenario: Production target still refuses
- **GIVEN** the target is classified as production
- **WHEN** ensure-ledger, reconcile, or apply is requested
- **THEN** the control plane MUST refuse before target mutation

#### Scenario: Application runtime client is not the migration executor
- **GIVEN** application runtime ClickHouse access exists
- **WHEN** reviewed `006` is validated or applied in tests
- **THEN** the migration control plane MUST NOT use the application runtime client as executor

## REMOVED Requirements

### Requirement: Missing 006 stays out and an unreviewed version blocks apply

**Reason**: `006` is now intentionally reviewed as the campaign-settings-history schema migration.

**Migration**: Replace the old reviewed fingerprint `001`–`005` with reviewed `001`–`006`; keep the fail-closed rule for every numeric prefix outside that fingerprint.

## ADDED Requirements

### Requirement: Reviewed 006 enters the corpus and an unreviewed successor blocks apply

Reviewed version `006` MUST enter the canonical fingerprint only with its exact raw-byte SHA-256 and schema-DDL privilege class. Any numeric migration version not in the reviewed fingerprint, including an unreviewed successor or an alternate `006`, MUST block apply and MUST NOT execute.

#### Scenario: Reviewed 006 is accepted
- **GIVEN** reviewed `006` is present with its accepted raw-byte SHA-256
- **WHEN** the control plane builds the corpus fingerprint
- **THEN** the fingerprint MUST be exactly `001`–`006`
- **AND** `006` MUST be classified as schema DDL

#### Scenario: Unreviewed successor blocks apply
- **GIVEN** a numeric migration file is not in the reviewed fingerprint
- **WHEN** apply is requested
- **THEN** the system MUST classify it as unreviewed
- **AND** MUST block apply
- **AND** MUST NOT execute it
