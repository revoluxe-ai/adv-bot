# Capability: scripts-collector-resolution

Machine-driven collector matching for `/opsx-scripts` PLAN_RUN and RUN.

## ADDED Requirements

### Requirement: Resolver CLI is fixed and machine-readable

The system SHALL invoke the resolver from the canonical worktree only. The
`/opsx-scripts` invocation SHALL be equivalent to:

```text
poetry run python <canonical-root>/tools/scripts/resolver.py \
  PLAN_RUN|RUN \
  --request-file <absolute-request-path> \
  --caller-root <absolute-caller-root> \
  --canonical-root <absolute-canonical-root>
```

The resolver SHALL require `--caller-root <absolute-path>` in both modes.
`--canonical-root` MAY be omitted only for direct resolver use outside the
bootstrap command; `/opsx-scripts` SHALL always provide it. The request SHALL
be an absolute-path UTF-8 JSON file with `schema_version`, `mode`, `request_id`, `run_id`,
`change_name_hint`, `capabilities`, `sources`, `required_fields`,
`output_schema_version`, `primary_artifact_pattern`, `required_args`,
`optional_args`, `zero_write_required`, `explicit_script`, and
`owning_change_id`.

#### Scenario: Canonical bootstrap invocation

- **WHEN** `/opsx-scripts` starts PLAN_RUN or RUN
- **THEN** it SHALL execute
  `<canonical-root>/tools/scripts/resolver.py` with canonical working
  directory and Poetry environment
- **AND** it SHALL pass absolute `--request-file`, `--caller-root`, and
  `--canonical-root`
- **AND** it SHALL not execute a resolver from the caller worktree

#### Scenario: User command modes use machine routing

- **WHEN** an operator selects either `PLAN_RUN` or `RUN` in `/opsx-scripts`
- **THEN** the command surface SHALL route the operation through the canonical
  bootstrap and machine resolver
- **AND** command-only matching SHALL not produce an operational result

#### Scenario: Missing caller root

- **WHEN** `--caller-root` is absent, relative, or does not identify a Git
  worktree
- **THEN** the resolver SHALL emit a machine-readable `BLOCKED` result
- **AND** it SHALL exit `2` without matching or Job execution

#### Scenario: Valid machine request

- **WHEN** the request file is valid and `mode` matches the CLI mode
- **THEN** stdout SHALL contain exactly one JSON result with
  `schema_version=scripts-resolver-result.v1`
- **AND** the result SHALL contain one of the four allowed outcomes
- **AND** the resolver SHALL not write files, run Jobs, or mutate Git

#### Scenario: Malformed request

- **WHEN** JSON, required fields, types, mode, kebab-case name, or
  `zero_write_required=true` validation fails
- **THEN** stdout SHALL contain a `BLOCKED` result with
  `error.code=INVALID_REQUEST`
- **AND** the process SHALL exit `2`
- **AND** no write path SHALL be attempted

#### Scenario: Malformed JSON without identifiers

- **WHEN** JSON parsing fails before `request_id` or `run_id` can be extracted
- **THEN** the BLOCKED result SHALL contain `request_id: null` and
  `run_id: null`
- **AND** the process SHALL exit `2`

#### Scenario: Credential material is rejected before output

- **WHEN** request argument names or values contain credential material such as
  `token`, `secret`, `password`, `api_key`, `authorization`, `cookie`,
  `credential`, `Bearer ...`, or a JWT-like value
- **THEN** the resolver SHALL return `BLOCKED` with a sanitized error
- **AND** stdout, stderr, `request_contract`, and `pasteable_prompt` SHALL not
  contain the original credential value

#### Scenario: Canonical root precedence

- **WHEN** both `--canonical-root` and `SCRIPTS_CANONICAL_ROOT` are supplied
- **THEN** the CLI argument SHALL take precedence
- **WHEN** neither is supplied
- **THEN** topology discovery SHALL be used
- **WHEN** no valid root is found
- **THEN** the resolver SHALL return `BLOCKED`

#### Scenario: Resolver outcome exit codes

- **WHEN** the resolver returns REUSE or COMPOSE
- **THEN** it SHALL exit `0`
- **WHEN** it returns FORMAL_CHANGE_REQUIRED, BLOCKED, or an unexpected error
- **THEN** it SHALL exit respectively `10`, `20`, or `30`

#### Scenario: Registry provenance is a Git commit

- **WHEN** a valid canonical Registry snapshot is loaded from fixed
  `execution_sha`
- **THEN** `registry_sha` SHALL be the lowercase 40-hex Git commit SHA that
  contains `scripts/REGISTRY.yaml` at or before `execution_sha`
- **AND** it SHALL not be a content SHA-256 digest
- **AND** any optional content digest SHALL be emitted separately as
  `registry_sha256`

#### Scenario: Registry provenance is Git-backed

- **WHEN** the resolver emits `registry_sha`
- **THEN** it SHALL equal the Git commit containing the Registry snapshot loaded
  from the canonical fixed HEAD
- **AND** it SHALL not equal a SHA-256 digest of Registry contents

### Requirement: Formal change has one machine artifact and deterministic command

For `FORMAL_CHANGE_REQUIRED`, the system SHALL persist exactly one
`.tmp/opsx-scripts/<run_id>/FORMAL_CHANGE_REQUIRED.json` artifact with
`schema_version=opsx.formal-change-handoff.v1`, `formal_type`,
`command`, `change_name`, `owner_change_id`, `reason`, `evidence`,
`request_contract`, `constraints`, `pasteable_prompt`, and `created_at`.

#### Scenario: New capability

- **WHEN** `formal_type=CREATE`
- **THEN** `command` SHALL be `/opsx-ff`
- **AND** the artifact SHALL contain a complete pasteable `/opsx-ff` request

#### Scenario: Existing capability extension

- **WHEN** `formal_type=EXTEND` and a supplied `owner_change_id` exists
- **THEN** `command` SHALL be `/opsx-update <owner_change_id>`
- **WHEN** `formal_type=EXTEND` and no valid owner change exists
- **THEN** `command` SHALL be `/opsx-ff <change_name>`

#### Scenario: Owner handoff

- **WHEN** the artifact is emitted
- **THEN** `pasteable_prompt` SHALL include workspace, request contract,
  evidence, formal type, safety constraints, and an explicit prohibition on
  apply until separately authorized GO
- **AND** `pasteable_prompt` SHALL not contain an executable `/opsx-apply`
  command
- **AND** the resolver SHALL not create or modify collector code

### Requirement: Mandatory machine resolver and runtime outcomes

`/opsx-scripts` SHALL invoke `tools/scripts/resolver.py` for every PLAN_RUN and
RUN request. Operational resolution SHALL return only `REUSE`, `COMPOSE`,
`FORMAL_CHANGE_REQUIRED`, or `BLOCKED`.

#### Scenario: Reuse existing capability

- **WHEN** exactly one resolution-enabled registry row covers the request's
  sources, capabilities, required fields, output schema, and zero-write rules
- **THEN** the resolver SHALL return `REUSE`
- **AND** the legacy display label `EXISTING` MAY be shown as an alias
- **AND** no collector, registry, or test file SHALL be written

#### Scenario: Ambiguous automatic resolution

- **WHEN** more than one resolution-enabled row fully covers the request
- **AND** there is no deterministic unique selection or valid COMPOSE plan
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** the result SHALL include the candidate registry IDs as evidence

#### Scenario: Compose existing capabilities

- **WHEN** no single row covers the request but composable rows cover it
- **THEN** the resolver SHALL return `COMPOSE`
- **AND** SHALL emit an ordered acyclic child plan
- **AND** SHALL not create or modify collector code

#### Scenario: Compose dependency graph

- **WHEN** a composable row declares `compose_with`
- **THEN** each listed row SHALL be a declared predecessor
- **AND** self-reference, duplicate, unknown dependency, or cycle SHALL return
  `BLOCKED`
- **AND** a valid graph SHALL produce deterministic topological order with
  registry-ID tie breaking

#### Scenario: Missing capability requires formal change

- **WHEN** the request needs new semantics or a shared collector extension that
  REUSE and COMPOSE cannot provide
- **THEN** the resolver SHALL return `FORMAL_CHANGE_REQUIRED`
- **AND** SHALL identify `formal_type=EXTEND` or `formal_type=CREATE`
- **AND** SHALL include a complete pasteable `/opsx-ff` or `/opsx-update`
  request
- **AND** RUN GO SHALL not create or modify collector code

#### Scenario: Incomplete or unsafe request is blocked

- **WHEN** required request fields, authority, canonical worktree, or registry
  evidence is missing or ambiguous
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** SHALL include the exact missing evidence and next safe action

### Requirement: Capability and presentation are separate

The resolver SHALL match data capabilities and sources independently from
consumer/report identity when the output schema remains compatible.

#### Scenario: Consumer label differs only

- **WHEN** two requests differ only by consumer or report identity
- **AND** capabilities, sources, required fields, and
  `output_schema_version` match
- **THEN** the resolver SHALL return `REUSE`
- **AND** SHALL not create a duplicate collector

#### Scenario: Output contract differs

- **WHEN** requests differ in output schema version, required fields, or primary
  artifact semantics
- **THEN** the resolver SHALL not return `REUSE` unless an explicit adapter row
  exists
- **AND** SHALL return `COMPOSE`, `FORMAL_CHANGE_REQUIRED`, or `BLOCKED`
  according to registry evidence

### Requirement: Field coverage controls automatic resolution

For automatic REUSE, the request's `required_fields` SHALL be a subset of the
selected entry's `provided_fields`. For COMPOSE, the union of child
`provided_fields` SHALL cover the request's `required_fields`, while sources,
capabilities, and output contracts remain compatible.

#### Scenario: Reuse covers required fields

- **WHEN** `request.required_fields ⊆ entry.provided_fields`
- **AND** the source, capability, output, and zero-write contracts are compatible
- **THEN** the resolver SHALL allow REUSE

#### Scenario: Reuse lacks a field

- **WHEN** one request field is absent from `entry.provided_fields`
- **THEN** the resolver SHALL not select REUSE
- **AND** SHALL continue to COMPOSE, FORMAL_CHANGE_REQUIRED, or BLOCKED

#### Scenario: Compose covers the union

- **WHEN** the union of selected child `provided_fields` covers all request
  fields and all child contracts are compatible
- **THEN** the resolver SHALL allow COMPOSE
- **AND** SHALL preserve the ordered child plan without semantic merge

#### Scenario: Compose lacks a field

- **WHEN** the child union does not cover a required field
- **THEN** the resolver SHALL not return COMPOSE
- **AND** SHALL return FORMAL_CHANGE_REQUIRED or BLOCKED

### Requirement: Automatic and explicit invocation are separate

Every registry row SHALL declare `resolution_enabled` and
`explicit_invocation_enabled`. Automatic matching SHALL consider only rows with
`resolution_enabled: true`. Explicit selection SHALL require an exact
`explicit_script` and a row with `explicit_invocation_enabled: true`. Such a
row SHALL provide `required_args`, `optional_args`, `provided_fields`,
`output_schema_version`, `primary_artifact_pattern`, `tenant_scope`,
`hardcoded_context`, `side_effects`, and `deprecated_by`.

#### Scenario: Explicit cabinet entrypoint

- **WHEN** cabinet401 v1/v2 has `resolution_enabled=false`,
  `explicit_invocation_enabled=true`, and is selected by exact `script=`
- **THEN** the resolver SHALL return `REUSE` with
  `selection_mode=EXPLICIT`
- **AND** it SHALL perform full args, READ_ONLY, artifact, checksum, and
  provenance validation
- **AND** it SHALL not make the row available to automatic matching

#### Scenario: Ledger-only legacy row

- **WHEN** a legacy row has both flags set to `false`
- **THEN** it SHALL not be selected automatically or explicitly
- **AND** its missing invocation metadata SHALL not block R1

#### Scenario: Explicit safety failure

- **WHEN** an explicit row lacks invocation safety metadata or fails a safety
  check
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** it SHALL not create a Job

### Requirement: COMPOSE has a deterministic runtime contract

For `COMPOSE`, the resolver SHALL describe every child collector, exact args,
declared outputs, dependency order, and required/optional status.

#### Scenario: PLAN_RUN displays child plan

- **WHEN** PLAN_RUN resolves a composable request
- **THEN** its plan SHALL display all child paths, args, outputs, and order
- **AND** SHALL not perform a Job or semantic merge

#### Scenario: RUN executes children sequentially

- **WHEN** RUN receives a valid COMPOSE plan
- **THEN** it SHALL execute required child Jobs sequentially
- **AND** each child SHALL pass its own artifact and checksum gate
- **AND** the parent SHALL write `COMPOSE_MANIFEST.json` only as a manifest,
  without hidden semantic merge

#### Scenario: Required child fails

- **WHEN** any required child Job or artifact/checksum gate fails
- **THEN** the composite run SHALL fail
- **AND** partial child artifacts SHALL remain available
- **AND** `EXTERNAL_HANDOFF_READY` SHALL be `NO`

#### Scenario: Child artifact gate verifies actual bytes

- **WHEN** a child reports success with an artifact path and digest
- **THEN** runtime SHALL verify the path is safe, the artifact exists, and the
  digest equals SHA-256 of the artifact bytes
- **AND** missing artifacts or digest mismatches SHALL make the child gate fail
- **AND** the manifest SHALL record only a verified digest

### Requirement: Resolution-enabled hardcoding policy

The resolver SHALL reject a new or changed collector with undeclared fixed
client, project, branch, or report identity when its registry row has
`resolution_enabled: true`, unless `tenant_scope=SPECIAL_PURPOSE` and the
hardcoded context is documented.

#### Scenario: New undeclared identity

- **WHEN** a resolution-enabled collector contains an undeclared fixed identity
- **THEN** the resolver or verification gate SHALL return `BLOCKED`
- **AND** SHALL include `path:line` evidence

#### Scenario: Legacy row is disabled

- **WHEN** a legacy row has `resolution_enabled: false`
- **THEN** its hardcoded context SHALL not block R1 resolution
- **AND** it SHALL not be eligible for automated REUSE or COMPOSE

### Requirement: Explicit script selection remains safety-gated

An explicit `script=` selection SHALL still invoke the resolver. A disabled or
deprecated registry row MAY be selected explicitly only after registry,
identity, READ_ONLY, artifact, checksum, and provenance validation.

#### Scenario: Explicit deprecated entrypoint

- **WHEN** `script=` names a valid disabled or deprecated row
- **THEN** the resolver SHALL return a validated explicit REUSE selection
- **AND** SHALL mark the selection as explicit
- **AND** SHALL warn about deprecation when applicable

#### Scenario: Explicit selection cannot bypass gates

- **WHEN** explicit selection requests a mutation-capable, unknown, or
  artifact-incomplete row
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** SHALL not create a Job or bypass any safety gate
