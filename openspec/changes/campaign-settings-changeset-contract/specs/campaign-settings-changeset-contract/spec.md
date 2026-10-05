## ADDED Requirements

### Requirement: ChangeSetV1 envelope

The system MUST accept a transport-independent `ChangeSetV1` document with
`schema_version` equal to `changeset.v1`, a unique `changeset_id`, `shop_id`,
source metadata, actor metadata, `created_at`, an optional intent/reason, and
a non-empty operation list. Any other `schema_version`, missing identity, or
empty operation list MUST yield `REJECTED`. The document MUST NOT be treated
as an Excel workbook or as `CampaignSettingsSnapshotV1`.

#### Scenario: Valid single-field change produces CHANGE

- **GIVEN** a `changeset.v1` document with one operation for a mutable field
- **AND** the injected current snapshot matches `expected_current_value`
- **AND** the normalized requested value differs from the current value
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `CHANGE`
- **AND** the operation diff MUST include `field`, `old_value`, `requested_value`, and `normalized_value`

#### Scenario: Duplicate changeset id with a different body is REJECTED

- **GIVEN** an injected prior record with the same `changeset_id` and a different canonical hash
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** the reason MUST identify a changeset id conflict
- **AND** no writer MUST be invoked

#### Scenario: Identical changeset id replay is deterministic

- **GIVEN** an injected prior record with the same `changeset_id` and the same canonical hash
- **WHEN** `validate_changeset_v1` runs again
- **THEN** the diff status MUST equal the prior status `NO_CHANGE` or `CHANGE`
- **AND** the pure function MUST NOT persist a new idempotency record

### Requirement: Operation target identity

Each operation MUST include `operation_id`, a target, `field`, `requested_value`,
and `expected_current_value`. The target MUST name a registered settings source,
the PostgreSQL `adv_setting_id` anchor, and `leg_role` of `AUTO`, `SEARCH`, or
`ROW` when the source is row-scoped. Auto and Search legs MUST remain distinct
targets. An unsupported source, campaign type, or leg MUST yield `REJECTED`
for the whole ChangeSet.

#### Scenario: Auto and Search targets stay separate

- **GIVEN** one snapshot row with auto `adv_id` A and search `search_adv_id` K
- **AND** a ChangeSet operation whose target leg is `SEARCH`
- **WHEN** validation builds the diff
- **THEN** the diff MUST bind the field to the Search leg identity
- **AND** MUST NOT show the Auto leg value as `old_value`
- **AND** MUST NOT merge A and K into one synthetic campaign id

#### Scenario: Unsupported campaign source or type is REJECTED

- **GIVEN** an operation whose target source or campaign type is not registered
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** no field diff MUST be marked actionable

#### Scenario: Duplicate operation id rejects the changeset

- **GIVEN** two operations in one ChangeSet with the same `operation_id`
- **WHEN** structural validation runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** neither operation MUST be partially accepted

### Requirement: mutation_policy extension

Mutable fields MUST be declared in `mutation_policy` keyed by the existing
campaign settings registry. A declaration MUST state mutability, supported
target scope, normalization via the registry `NormalizationPolicy`, allowed
value domain, required capabilities, and precondition requirement. Excel
`editable` MUST NOT by itself make a field mutable. Fields with semantic role
other than `setting`, and settings without a mutation entry, MUST be rejected
as read-only or unsupported. Unknown fields MUST fail closed.

#### Scenario: Unsupported field is REJECTED

- **GIVEN** an operation whose `field` is absent from the registry and from `mutation_policy`
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`

#### Scenario: Read-only field is REJECTED

- **GIVEN** an operation that targets an identity, WB-fact, runtime, derived, or technical field
- **OR** a setting field with no mutable `mutation_policy` entry
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** the reason MUST identify the field as not mutable

#### Scenario: Invalid value is REJECTED

- **GIVEN** a mutable field whose requested value is outside the normalization domain or `allowed_values`
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`

#### Scenario: Unknown capability is REJECTED

- **GIVEN** a mutation policy or caller grant that names a capability outside the closed capability catalog
- **OR** a required capability that was not granted
- **WHEN** capability validation runs
- **THEN** the diff status MUST be `REJECTED`

### Requirement: Validation pipeline and normalization

The validator MUST run in this order: structural validation, identity
resolution, registry field validation, normalization, domain validation,
capability validation, current-state precondition validation, then
deterministic diff. A later step MUST NOT run as an accepting path after an
earlier rejection. Normalization MUST use `normalize_value` from the campaign
settings contract. Cross-field invariants MUST NOT be encoded only as JSON
Schema or only as a registry row; a declared invariant with unknown
implementation state MUST fail closed.

#### Scenario: Normalization records requested and normalized values

- **GIVEN** a mutable numeric or boolean field whose requested representation differs in form from the canonical value
- **AND** the normalized value differs from the current value
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `CHANGE`
- **AND** `requested_value` MUST preserve the request
- **AND** `normalized_value` MUST equal the registry normalizer output

#### Scenario: Normalized value equal to current is NO_CHANGE

- **GIVEN** every operation normalizes to the current snapshot value
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `NO_CHANGE`
- **AND** no actionable field change MUST be emitted

### Requirement: Atomic ChangeSet

A ChangeSet MUST be atomic. If any operation is invalid, the ChangeSet status
MUST be `REJECTED`. Valid sibling operations in the same document MUST NOT be
returned as actionable `CHANGE` entries.

#### Scenario: Multiple operations produce one atomic CHANGE

- **GIVEN** two operations on two different mutable fields of one resolved target
- **AND** both preconditions match and both normalized values differ
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `CHANGE`
- **AND** both field diffs MUST be present

#### Scenario: Mixed valid and invalid operations reject the whole changeset

- **GIVEN** one valid mutable operation and one unsupported or invalid operation
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** the valid operation MUST NOT be marked actionable `CHANGE`

#### Scenario: Duplicate target field rejects the changeset

- **GIVEN** two operations with different `operation_id` values that name the same target and the same field
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`

### Requirement: Precondition and missing state

Every operation MUST carry `expected_current_value`. Omission MUST NOT be
treated as null. The value MUST be compared after normalization to the
injected current snapshot. A mismatch MUST yield `REJECTED`. A missing
snapshot or an unresolved target row MUST yield `REJECTED`. The validator
MUST NOT take a distributed lock and MUST NOT read or write PostgreSQL itself.

#### Scenario: Stale expected current value is REJECTED

- **GIVEN** a mutable operation whose normalized `expected_current_value` differs from the snapshot
- **WHEN** precondition validation runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** the reason MUST identify a stale precondition

#### Scenario: Missing current state is REJECTED

- **GIVEN** no current snapshot for the operation target
- **WHEN** `validate_changeset_v1` runs
- **THEN** the diff status MUST be `REJECTED`
- **AND** the reason MUST identify missing current state

### Requirement: No production write

`validate_changeset_v1` and the diff builder MUST NOT call WB API writers,
PostgreSQL settings writers, ClickHouse writers, `apply_adv_excel_rows`,
shop-runner mutation, Telegram, MCP, or a public apply API. Rejection and
acceptance both leave current settings unchanged.

#### Scenario: Validation result does not perform production writes

- **GIVEN** a ChangeSet that validates to `CHANGE`, `NO_CHANGE`, or `REJECTED`
- **WHEN** `validate_changeset_v1` returns
- **THEN** no forbidden adapter MUST be invoked
- **AND** the function result MUST be only the diff or rejection document
