# Capability: scripts-registry-contract

Machine registry and generated human-readable view for scripts collectors.

## ADDED Requirements

### Requirement: Registry document shape is exact and versioned

`scripts/REGISTRY.yaml` SHALL have exactly the top-level keys `schema`,
`version`, `generated`, and `entries`, with `schema=scripts-registry`,
`version=2`, `generated.markdown=scripts/REGISTRY.md`, and
`generated.ordering=id`; `generated` SHALL contain no other keys. Each entry
SHALL require `id`, `title`, `path`, `resolution_enabled`,
`explicit_invocation_enabled`, and `readiness`.
`readiness` SHALL contain exactly `runnable`, `tests`, `battle_tested`,
`last_local_at`, `last_cluster_at`, `last_image_ref`, and `notes`.

#### Scenario: Valid enabled row

- **WHEN** an entry has `resolution_enabled: true`
- **THEN** it SHALL contain capabilities, sources, required/optional args,
  `provided_fields`, output schema/artifact pattern, tenant scope, hardcoded context,
  composition, side effects, deprecation, and readiness fields
- **AND** all values SHALL conform to the Registry v2 types and enums
- **AND** no unknown entry keys SHALL be accepted

#### Scenario: Invalid registry structure

- **WHEN** YAML has an unknown top-level/entry key, missing required key,
  invalid enum, duplicate ID/path, invalid composition reference, or automatic
  resolution fields on a disabled row without explicit invocation enabled
- **THEN** validation SHALL fail
- **AND** the resolver SHALL not use the registry snapshot

#### Scenario: Immutable image readiness

- **WHEN** `readiness.last_image_ref` is present
- **THEN** it SHALL be `-` or a Harbor proxy-cache image reference ending in a
  lowercase 40-hex execution commit SHA
- **AND** mutable tags, arbitrary text, and non-confirmed legacy image refs
  SHALL be rejected

#### Scenario: Disabled legacy row

- **WHEN** an entry has `resolution_enabled: false`
- **THEN** it SHALL be excluded from automated REUSE and COMPOSE
- **AND** when `explicit_invocation_enabled: true`, it SHALL contain
  invocation-safety metadata: `required_args`, `optional_args`,
  `provided_fields`, `output_schema_version`, `primary_artifact_pattern`,
  `tenant_scope`, `hardcoded_context`, `side_effects`, and `deprecated_by`
- **AND** when both flags are false, it SHALL contain only identity,
  `deprecated_by`, and readiness keys

### Requirement: Registry maintenance commands are fixed

The repository SHALL provide these exact commands, run from the canonical
scripts worktree:

```text
poetry run python tools/scripts/registry.py validate --input scripts/REGISTRY.yaml
poetry run python tools/scripts/registry.py render --input scripts/REGISTRY.yaml --output scripts/REGISTRY.md
poetry run python tools/scripts/registry.py check-drift --input scripts/REGISTRY.yaml --generated scripts/REGISTRY.md
```

#### Scenario: Validate registry

- **WHEN** `registry.py validate` receives a valid YAML document
- **THEN** it SHALL exit `0`
- **WHEN** schema/content validation fails
- **THEN** it SHALL exit `2`

#### Scenario: Render generated Markdown

- **WHEN** `registry.py render` succeeds
- **THEN** it SHALL deterministically write only the generated Markdown path
- **AND** entries SHALL be ordered by `id`

#### Scenario: Detect projection drift

- **WHEN** generated Markdown is byte-identical to the YAML projection
- **THEN** `check-drift` SHALL exit `0`
- **WHEN** projection differs
- **THEN** `check-drift` SHALL exit `3`

### Requirement: YAML is the machine registry source of truth

The system SHALL use `scripts/REGISTRY.yaml` as the only machine-readable
registry source. `scripts/REGISTRY.md` SHALL be generated from YAML and SHALL
not be treated as an independent source.

#### Scenario: Registry is loaded

- **WHEN** the resolver loads collector metadata
- **THEN** it SHALL read `scripts/REGISTRY.yaml`
- **AND** SHALL record the registry commit SHA in resolution provenance

#### Scenario: Generated view drift

- **WHEN** generated `scripts/REGISTRY.md` differs from the YAML projection
- **THEN** registry verification SHALL fail
- **AND** the resolver SHALL not claim a valid resolution snapshot

### Requirement: Minimal Registry v2 matching fields

Every row with `resolution_enabled: true` SHALL provide
`title`, `path`, `resolution_enabled`, `capabilities`, `sources`,
`explicit_invocation_enabled`, `required_args`, `optional_args`,
`provided_fields`, `output_schema_version`,
`primary_artifact_pattern`, `tenant_scope`, `hardcoded_context`,
`composable`, `compose_with`, `side_effects`, and `deprecated_by`.

#### Scenario: Missing resolution field

- **WHEN** a row is eligible for automated resolution and any required field is
  absent or malformed
- **THEN** verification SHALL flag the row as incomplete
- **AND** the resolver SHALL not use it for REUSE or COMPOSE

#### Scenario: Composition graph validation

- **WHEN** a resolution-enabled row is composable
- **THEN** `compose_with` SHALL be a non-empty predecessor list
- **AND** it SHALL not contain the row itself, duplicates, unknown IDs, or
  dependencies that form a cycle
- **AND** a violation SHALL fail Registry validation

#### Scenario: Legacy row is explicitly disabled

- **WHEN** a legacy row has `resolution_enabled: false`
- **THEN** it MAY remain in the registry with readiness metadata
- **AND** it SHALL not participate in automated resolution
- **AND** its hardcoded context SHALL not block R1

#### Scenario: Provided fields are validated

- **WHEN** `provided_fields` is absent, duplicated, or contains an empty value
  on a resolution-enabled or explicitly invokable row
- **THEN** validation SHALL fail
- **AND** the row SHALL not be used for resolution or explicit invocation

### Requirement: R1 registry scope is bounded

R1 SHALL register or enable resolution only for the four reference migration
entrypoints and SHALL not backfill all unregistered legacy entrypoints.

#### Scenario: Unregistered legacy entrypoint

- **WHEN** an entrypoint is outside the R1 reference set
- **THEN** it SHALL remain outside automated resolution or be explicitly marked
  `resolution_enabled: false`
- **AND** R1 verification SHALL not require its full metadata backfill

### Requirement: Resolution-enabled hardcoding attestation

Hardcoding verification SHALL scan only new or changed collectors whose YAML
row has `resolution_enabled: true`. A fixed identity is allowed only when
`tenant_scope=SPECIAL_PURPOSE` and `hardcoded_context` documents it.

#### Scenario: Undeclared hardcoded identity

- **WHEN** static analysis finds a fixed client, project, cabinet, or branch
  identity in an enabled collector without the required declaration
- **THEN** verification SHALL fail with `path:line` evidence
- **AND** the row SHALL not be eligible for REUSE or COMPOSE

#### Scenario: Disabled legacy hardcoding

- **WHEN** static analysis finds hardcoding in a row with
  `resolution_enabled: false`
- **THEN** the row SHALL not block R1
- **AND** it SHALL remain unavailable to automated resolution

### Requirement: Deprecation preserves explicit access

Deprecated collectors SHALL remain runnable when selected by explicit
`script=` while their registry row is valid, and SHALL reference a replacement
through `deprecated_by`.

#### Scenario: Deprecated cabinet entrypoint

- **WHEN** an operator explicitly selects a deprecated cabinet entrypoint
- **THEN** the Job SHALL remain available under its existing contract
- **AND** status output SHALL identify the replacement
