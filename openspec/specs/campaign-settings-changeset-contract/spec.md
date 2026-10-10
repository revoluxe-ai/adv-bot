# campaign-settings-changeset-contract Specification

## Purpose
TBD - created by archiving change campaign-settings-changeset-contract. Update Purpose after archive.
## Requirements
### Requirement: ChangeSetV1 envelope and state_token

The system MUST accept a transport-independent `ChangeSetV1` (canonical type in
`wb_sky_control_plane` `models/changeset.py`) with `contract_version`, `changeset_id`,
shop scope, metadata, and a non-empty operation list. Each bounded operation MUST
carry per-operation `preconditions.state_token` (not an envelope-level token).
Phase A (pre-I/O) MUST reject missing or empty `preconditions.state_token`.
After authoritative snapshot resolution, stale or mismatched token equality MUST
reject the whole ChangeSet with `REJECTED`. The document MUST NOT be Excel or
`CampaignSettingsSnapshotV1`.

#### Scenario: Valid existing bounded operation produces OK

- **GIVEN** a `ChangeSetV1` with one operation from the existing bounded WIP operation set
- **AND** a `state_token` matching the injected snapshot generation
- **AND** grants satisfy required capabilities
- **AND** normalized requested value differs from the snapshot
- **WHEN** `validate_changeset` runs as dry-run
- **THEN** the status MUST be `OK`
- **AND** at least one `SemanticDiffEntryV1` MUST include old, requested, and normalized values

#### Scenario: Stale state_token is REJECTED

- **GIVEN** a `ChangeSetV1` whose `state_token` does not match the injected snapshot generation
- **WHEN** dry-run validation runs
- **THEN** the status MUST be `REJECTED`
- **AND** the reason MUST identify stale or invalid generation token

#### Scenario: Missing state_token is REJECTED

- **GIVEN** a `ChangeSetV1` with a missing or empty `state_token`
- **WHEN** dry-run validation runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Duplicate changeset id with a different body is REJECTED

- **GIVEN** an injected prior record with the same `changeset_id` and a different canonical hash
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`
- **AND** no writer MUST be invoked

#### Scenario: Identical changeset id replay is deterministic

- **GIVEN** an injected prior record with the same `changeset_id` and the same canonical hash
- **WHEN** `validate_changeset` runs again with the same inputs
- **THEN** the status MUST equal the prior `NO_OP` or `OK`
- **AND** the pure function MUST NOT persist a new idempotency record

### Requirement: CampaignResourceRef identity

Each operation MUST include `operation_id`, a `CampaignResourceRef` (or equivalent
target field in WIP `ChangeSetV1`) resolved through the `cmp_*` resource registry,
and payload for one bounded policy operation. Unresolved or unknown resources MUST
yield `REJECTED` for the whole ChangeSet. The plan MUST NOT introduce a parallel
target schema using only `adv_setting_id` and `leg_role` as the ChangeSet owner
identity model.

#### Scenario: cmp_star resource identity binds the diff

- **GIVEN** an injected snapshot where a `cmp_*` resource maps to a known campaign resource row
- **AND** an operation targeting that `CampaignResourceRef`
- **WHEN** dry-run builds `SemanticDiffEntryV1`
- **THEN** the diff MUST bind to that resource identity
- **AND** MUST NOT synthesize a second parallel target key outside `cmp_*` / `CampaignResourceRef`

#### Scenario: Unresolved CampaignResourceRef is REJECTED

- **GIVEN** an operation whose `CampaignResourceRef` does not resolve in the injected registry snapshot
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Duplicate operation id rejects the changeset

- **GIVEN** two operations in one ChangeSet with the same `operation_id`
- **WHEN** structural validation runs
- **THEN** the status MUST be `REJECTED`
- **AND** neither operation MUST be partially accepted

### Requirement: mutation_policy extension

Mutable fields and bounded operations MUST be declared in `mutation_policy` (or
equivalent WIP policy tables) keyed to registry and operation types. Declarations
MUST cover mutability, normalization, allowed domain, capability requirements, and
precondition requirements. Unknown registry fields and unsupported operations MUST
fail closed. Excel `editable` MUST NOT alone grant mutability.

#### Scenario: Unsupported mutation is REJECTED

- **GIVEN** an operation type or field not covered by `mutation_policy` / bounded op set
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Invalid value is REJECTED

- **GIVEN** a mutable operation whose requested value is outside normalization or allowed domain
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Unknown capability is REJECTED

- **GIVEN** a policy or grant naming a capability token outside the known catalog
- **WHEN** capability validation runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Unsupported capability tri-state is REJECTED

- **GIVEN** a required capability that evaluates to unsupported in the existing tri-state model
- **WHEN** capability validation runs
- **THEN** the status MUST be `REJECTED`

### Requirement: Validation pipeline and normalization

Phase A (pure, before PG/WB resolution) MUST reject duplicate operation ids,
duplicate operation slots, unsupported operations, unknown grant tokens, missing
per-operation `preconditions.state_token`, and `changeset_id` replay hash conflict.
Phase B resolves `CampaignResourceRef` and loads authoritative snapshots. Phase C
MUST run in order: stale `state_token` equality check; mutation policy field gate;
normalization via `campaign_settings_contract.normalize_value`; deterministic domain
validation; capability validation (tri-state fail-closed); optional
`expected_current_value`; semantic diff. Cross-field invariants use named domain
validators. A declared invariant without implementation MUST fail closed.

#### Scenario: Normalization records requested and normalized values

- **GIVEN** a mutable settings field whose requested representation differs in form from the canonical value
- **AND** normalized value differs from the current value at `state_token`
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `OK`
- **AND** `SemanticDiffEntryV1` MUST preserve requested and normalized values

#### Scenario: No semantic change is NO_OP

- **GIVEN** every operation normalizes to the current snapshot value at `state_token`
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `NO_OP`
- **AND** no actionable semantic change MUST be emitted

#### Scenario: Deterministic diff for identical inputs

- **GIVEN** two dry-run invocations with the same ChangeSet, snapshot, grants, and prior record injection
- **WHEN** `validate_changeset` runs twice
- **THEN** status and `SemanticDiffEntryV1` lists MUST be byte-for-byte equivalent

### Requirement: Precondition under state_token

`state_token` is the only concurrency contract. `expected_current_value`, when
present, is a field-level semantic precondition evaluated only against the snapshot
generation identified by `state_token`. Omitting `expected_current_value` does not
bypass `state_token`. The validator MUST NOT open PostgreSQL or take distributed
locks.

#### Scenario: expected_current_value mismatch is REJECTED

- **GIVEN** a valid `state_token`
- **AND** an operation with `expected_current_value` that differs from the snapshot field after normalization
- **WHEN** precondition validation runs
- **THEN** the status MUST be `REJECTED`

#### Scenario: Omitting expected_current_value does not bypass state_token

- **GIVEN** an operation with no `expected_current_value` key
- **AND** an invalid or missing `state_token`
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`
- **AND** omission MUST NOT be treated as acceptance

### Requirement: Atomic ChangeSet

A ChangeSet MUST be atomic. Any invalid operation MUST yield `REJECTED` for the
entire document.

#### Scenario: Multiple valid operations produce one OK

- **GIVEN** two valid operations on distinct fields or resources
- **AND** a matching `state_token`
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `OK`
- **AND** both semantic diffs MUST be present

#### Scenario: Mixed valid and invalid operations reject the whole changeset

- **GIVEN** one valid operation and one unsupported or invalid operation
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`
- **AND** the valid operation MUST NOT appear as actionable `OK`

#### Scenario: Duplicate target mutation rejects the changeset

- **GIVEN** two operations with different `operation_id` values targeting the same resource and the same mutable field or op slot
- **WHEN** `validate_changeset` runs
- **THEN** the status MUST be `REJECTED`

### Requirement: No production write

`validate_changeset` and the diff builder MUST NOT call WB API writers, PostgreSQL
settings writers, ClickHouse writers, `apply_adv_excel_rows`, shop-runner mutation,
Telegram, MCP, public apply, or the MIXED
`campaigns_info_v2/adapter.py`.

#### Scenario: Validation result does not perform production writes

- **GIVEN** a ChangeSet that dry-runs to `OK`, `NO_OP`, or `REJECTED`
- **WHEN** `validate_changeset` returns
- **THEN** no forbidden adapter MUST be invoked
- **AND** the result MUST be only the dry-run status and diff or rejection document

