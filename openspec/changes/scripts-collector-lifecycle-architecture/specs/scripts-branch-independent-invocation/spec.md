# Capability: scripts-branch-independent-invocation

Invoke scripts Jobs from any Git worktree without mutating the caller branch.

## ADDED Requirements

### Requirement: Canonical worktree is discovered from Git topology

The resolver SHALL discover the canonical scripts worktree by parsing
`git worktree list --porcelain`, selecting exact branch
`refs/heads/scripts`, verifying the same Git common directory as the caller,
and requiring no tracked staged or unstaged changes.

#### Scenario: Exact canonical worktree

- **WHEN** porcelain output contains a worktree on `refs/heads/scripts` with the
  caller's Git common directory and its tracked status is clean
- **THEN** the resolver SHALL use its fixed HEAD for registry and execution SHA
  resolution
- **AND** SHALL read registry and execution inputs from that HEAD

#### Scenario: No valid canonical worktree

- **WHEN** no exact-branch worktree exists or common-directory validation fails
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** SHALL not fall back to a relative path

#### Scenario: Ambiguous canonical topology

- **WHEN** more than one valid clean worktree has exact branch
  `refs/heads/scripts` and the caller's Git common directory
- **THEN** bootstrap and resolver SHALL return `BLOCKED`
- **AND** SHALL not select a candidate by listing order

#### Scenario: Canonical worktree is dirty

- **WHEN** `git -C <canonical> status --porcelain=v1 --untracked-files=no`
  reports staged or unstaged tracked changes
- **THEN** the resolver SHALL return `BLOCKED`
- **AND** SHALL not read registry or execution inputs from the dirty worktree

#### Scenario: Explicit override

- **WHEN** `SCRIPTS_CANONICAL_ROOT` is explicitly supplied
- **THEN** the resolver SHALL validate its exact `refs/heads/scripts` branch
  common directory, and tracked clean state before using it
- **AND** CLI `--canonical-root` SHALL take precedence over the environment
  variable
- **AND** the variable SHALL not define an implicit default

#### Scenario: Root precedence fallback

- **WHEN** no CLI override is supplied but `SCRIPTS_CANONICAL_ROOT` is set
- **THEN** the environment value SHALL be validated and used before topology
  discovery
- **AND** a failed explicit CLI or environment validation SHALL return
  `BLOCKED` without falling through to a lower-precedence source
- **WHEN** neither override is supplied
- **THEN** topology discovery SHALL be used
- **WHEN** no valid candidate remains
- **THEN** the resolver SHALL return `BLOCKED`

### Requirement: Thin bootstrap launches only the canonical resolver

Before PLAN_RUN or RUN, `/opsx-scripts` SHALL perform a read-only bootstrap in
the caller worktree. It SHALL record caller root/worktree/branch/HEAD SHA,
resolve the canonical candidate with precedence
`--canonical-root` → `SCRIPTS_CANONICAL_ROOT` → topology, select exact
`refs/heads/scripts`, and invoke only
`<canonical-root>/tools/scripts/resolver.py` with canonical working directory.
The bootstrap SHALL pass absolute `--caller-root`,
`--request-file`, and `--canonical-root` paths.

The bootstrap SHALL not read Registry, perform matching, select a collector,
run a Job, or interpret resolver outcomes. The resolver SHALL independently
repeat all caller/canonical branch, common-directory, clean-state, and fixed
HEAD checks. If bootstrap cannot find a candidate, it SHALL return `BLOCKED`
without trying a caller-local or stale resolver.

#### Scenario: Caller lacks canonical implementation files

- **WHEN** a feature worktree lacks `tools/scripts/resolver.py`,
  `scripts/REGISTRY.yaml`, or the new command implementation files
- **AND** an exact `refs/heads/scripts` worktree contains the implementation
- **THEN** bootstrap SHALL invoke the absolute canonical resolver
- **AND** the request SHALL execute with canonical working directory and Poetry
  environment
- **AND** the caller-local file absence SHALL not block resolver startup

#### Scenario: Canonical-root precedence is fail-closed

- **WHEN** a valid `--canonical-root` and a different
  `SCRIPTS_CANONICAL_ROOT` are both supplied
- **THEN** the explicit CLI root SHALL be selected
- **WHEN** the explicit CLI root is present but is not a valid exact
  `refs/heads/scripts` worktree
- **THEN** bootstrap SHALL return `BLOCKED` without falling back to the
  environment root or topology discovery

#### Scenario: Caller contains a stale resolver

- **WHEN** the caller worktree contains a stale local resolver
- **AND** the canonical worktree contains the selected resolver
- **THEN** bootstrap SHALL not execute the caller-local resolver
- **AND** caller provenance SHALL be computed from `--caller-root`

#### Scenario: Bootstrap cannot find a candidate

- **WHEN** no valid exact `refs/heads/scripts` candidate is discoverable
- **THEN** bootstrap SHALL return `BLOCKED` fail-closed
- **AND** it SHALL not read Registry or perform matching

#### Scenario: Caller provenance and common directory

- **WHEN** canonical resolver starts with `--caller-root <absolute-path>`
- **THEN** the resolver SHALL derive caller root/worktree/branch/SHA from that
  path
- **AND** SHALL verify caller and canonical roots belong to the same Git common
  directory
- **AND** SHALL include caller provenance in the machine result/report

#### Scenario: Canonical bootstrap regression evidence

- **WHEN** the bootstrap is exercised from a temporary feature worktree
- **THEN** the caller MAY omit both `tools/scripts/resolver.py` and
  `scripts/REGISTRY.yaml`
- **AND** a stale caller resolver SHALL never execute
- **AND** caller HEAD and tracked-file hashes SHALL be unchanged after the run
- **AND** the canonical resolver SHALL execute by absolute path with canonical
  working directory

### Requirement: Caller branch remains unchanged

PLAN_RUN and RUN SHALL not require commits, pushes, or tracked file writes on
the operator's current feature branch.

#### Scenario: Plan from feature branch

- **WHEN** the operator runs PLAN_RUN from a non-`scripts` branch
- **THEN** the resolver SHALL produce a plan from the canonical registry and
  execution SHA
- **AND** the caller branch SHALL remain unchanged

#### Scenario: Invocation-owned output paths

- **WHEN** a runtime output or formal receipt path is computed
- **THEN** it SHALL be inside `.tmp/opsx-scripts/<run_id>/`
- **AND** `run_id` SHALL match `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`
- **AND** traversal, absolute paths, separators, symlink/reparse escapes, and
  existing output-directory collisions SHALL be blocked
- **AND** arbitrary caller-supplied directories SHALL not be removed

#### Scenario: Run uses immutable execution image

- **WHEN** RUN executes a resolved collector
- **THEN** every Job SHALL use an immutable Harbor proxy-cache image reference
  tagged by execution commit SHA
- **AND** the run SHALL not rely solely on a mutable floating tag

### Requirement: Operational execution has no code-write path

RUN SHALL not create, modify, commit, push, or stash collector code, registry
source, tests, commands, or branches.

#### Scenario: Missing capability during RUN

- **WHEN** resolver returns `FORMAL_CHANGE_REQUIRED`
- **THEN** RUN SHALL stop before creating a collector Job
- **AND** SHALL return the complete pasteable formal-change request

### Requirement: Verification is split before and after merge

Apply-stage verification SHALL use a temporary Git fixture with separate
feature and exact `scripts` worktrees. Real canonical runtime smoke SHALL be
post-merge and require separate merge/deploy authorization.

#### Scenario: Apply-stage fixture

- **WHEN** implementation verification runs before merge
- **THEN** it SHALL test clean HEAD, tracked dirty state, wrong branch, and
  different common directory in an isolated Git fixture
- **AND** it SHALL not claim that the real canonical runtime is updated

#### Scenario: Post-merge smoke

- **WHEN** the scripts branch has been separately merged/deployed and authorized
- **THEN** a real PLAN_RUN MAY run from a non-`scripts` worktree
- **AND** the implementation handoff status SHALL be
  `READY_FOR_MERGE_REVIEW` before that smoke exists

### Requirement: Provenance is additive

SCRIPTS_REPORT SHALL add caller and execution provenance without removing or
renaming existing consumer-facing fields.

#### Scenario: Provenance fields present

- **WHEN** a contract run completes
- **THEN** the report SHALL include caller branch, caller worktree, and caller SHA
- **AND** SHALL include execution SHA, image reference, and registry SHA
- **AND** existing report consumers SHALL remain parse-compatible

### Requirement: COMPOSE runs are isolated and auditable

Concurrent composite runs SHALL isolate parent and child Jobs, output directories,
and primary artifacts. The parent manifest SHALL record child execution evidence.

#### Scenario: Two parallel composite runs

- **WHEN** two COMPOSE runs use different run IDs
- **THEN** parent and child Job names SHALL be distinct
- **AND** local output directories SHALL be distinct
- **AND** each child SHALL have an independent checksum gate

### Requirement: COMPOSE manifest has a fixed evidence schema

The composite parent SHALL create `.tmp/opsx-scripts/<run_id>/COMPOSE_MANIFEST.json`
with `schema_version=opsx.compose-manifest.v1`, `run_id`, `outcome`,
`status`, parent `execution_sha`, `registry_sha`, ordered `children`,
`failure_details`, `primary_artifact`, and `external_handoff_ready`.
Each child SHALL contain `order`, `registry_id`, `required`, `collector_path`,
`job_name`, `args`, `execution_sha`, `artifact_path`, `sha256`,
`gate_status`, `status`, and `failure`. The manifest SHALL additionally contain
`checksum_sidecar_path`; `primary_artifact` SHALL contain only `path` and
`accepted`.

#### Scenario: Manifest starts before child execution

- **WHEN** resolver returns a valid COMPOSE plan with valid run, registry, and
  execution identities
- **THEN** the manifest SHALL be created with `status=RUNNING`
- **AND** it SHALL be updated after every child gate
- **AND** pending child `job_name`, `artifact_path`, `sha256`, and `failure`
  MAY be null

#### Scenario: Terminal child fields

- **WHEN** a child reaches `SUCCEEDED`, `FAILED`, or `SKIPPED`
- **THEN** its terminal contract fields SHALL not be null
- **AND** failed children without an artifact SHALL use
  `artifact_path=NOT_AVAILABLE` and `sha256=NOT_AVAILABLE`
- **AND** skipped children SHALL use `job_name=NOT_CREATED`,
  `artifact_path=NOT_AVAILABLE`, `sha256=NOT_APPLICABLE`, and a non-null
  skip failure object

#### Scenario: Composite manifest

- **WHEN** all required children pass
- **THEN** the parent SHALL finalize `COMPOSE_MANIFEST.json` with
  `status=SUCCEEDED`
- **AND** the manifest SHALL be accepted as the primary artifact
- **AND** `external_handoff_ready` SHALL be `true`
- **AND** `COMPOSE_MANIFEST.json.sha256` SHALL contain the finalized manifest
  digest and SCRIPTS_REPORT SHALL store it as `COMPOSE_MANIFEST_SHA256`
- **AND** each manifest child record SHALL include child Job, execution SHA,
  artifact path, and SHA-256

#### Scenario: Partial composite

- **WHEN** any required child fails
- **THEN** partial artifacts SHALL be retained
- **AND** the manifest SHALL still be finalized as evidence
- **AND** the composite primary SHALL not be accepted
- **AND** `external_handoff_ready` SHALL be `false`

#### Scenario: Optional child fails

- **WHEN** an optional child fails its Job or artifact/checksum gate
- **THEN** the runner SHALL record the failure and continue with later children
- **AND** the parent status SHALL be `PARTIAL_FAILURE`
- **AND** the manifest SHALL not be accepted as a successful primary
- **AND** `external_handoff_ready` SHALL be `false`

#### Scenario: Manifest checksum is external

- **WHEN** the manifest is finalized
- **THEN** its SHA-256 SHALL be computed only after finalization
- **AND** the digest SHALL be written to `COMPOSE_MANIFEST.json.sha256` and
  SCRIPTS_REPORT
- **AND** the manifest SHALL not contain its own SHA-256
