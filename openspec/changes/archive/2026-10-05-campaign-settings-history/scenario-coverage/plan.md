# Scenario coverage plan

CHANGE_ID: campaign-settings-history
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: db0349d67c039d806e4a79cde16b8a71a761c0d73e62b64b96b925a6b4c065f3
LIFECYCLE_STATUS: DERIVED
MIGRATION_PREREQUISITE_LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true

This is derived planning evidence only. It defines required evidence; it does not assert that tests exist or PASS.

## GENERATED_FROM

PLAN_EVIDENCE_ID is sha256 of the UTF-8 LF blob below, including the final newline:

```text
campaign-settings-history
plan
design.md:c86633befed995473ee7c768bdfbd862e7b10f44149290aaa8c69871af38c978
specs/campaign-settings-history/spec.md:c2dd8f1dcf625d2a454e9341572415c39790e8cdee8c0eec1c2b42b7175830ab
specs/clickhouse-migration-lifecycle/spec.md:8d1b1994ca5c6cb46879285d8794f649662060cb77106db0912b06aa07c403fd
owner-contract.md:5295b85b45b38e0410a692e183edeaa10bef6ab9831a21865aa1e6effd1ab903
lifecycle:design.md:c86633befed995473ee7c768bdfbd862e7b10f44149290aaa8c69871af38c978
```

INPUTS:
- DESIGN_REVISION: design.md content_hash c86633befed995473ee7c768bdfbd862e7b10f44149290aaa8c69871af38c978
- SPEC_REVISION: specs/campaign-settings-history/spec.md content_hash c2dd8f1dcf625d2a454e9341572415c39790e8cdee8c0eec1c2b42b7175830ab
- SPEC_REVISION: specs/clickhouse-migration-lifecycle/spec.md content_hash 8d1b1994ca5c6cb46879285d8794f649662060cb77106db0912b06aa07c403fd
- OWNER_CONTRACT_REVISION: owner-contract.md content_hash 5295b85b45b38e0410a692e183edeaa10bef6ab9831a21865aa1e6effd1ab903
- LIFECYCLE_REVISION: design.md content_hash c86633befed995473ee7c768bdfbd862e7b10f44149290aaa8c69871af38c978

## LIFECYCLE_COVERAGE

Runtime product lifecycle is design.md L1-L7. Migration rows use a separate prerequisite lifecycle derived from the modified migration spec and accepted migration-control ownership; they are not forced into polling steps.

### Product/runtime L1-L7
- L1: discover observable PostgreSQL settings owners independently of bot/WB/Redis activity.
- L2: acquire per-cabinet PgBouncer-safe transaction advisory lock.
- L3: read complete current settings from PostgreSQL.
- L4: normalize/validate canonical contract and registry/Excel policy.
- L5: compare canonical state hash against durable ClickHouse latest hash.
- L6: append changed snapshot; durable timeline is the read projection of this output.
- L7: end transaction/release xact lock and report success/degraded/invalid outcome.

### Migration prerequisite M1-M4
- M1: review immutable corpus identity including exact reviewed 006.
- M2: produce a dry migration plan including 006 without execution.
- M3: isolated gated apply; 005/unreviewed/missing authorization remain refused.
- M4: production target and application-runtime executor remain excluded.

LIFECYCLE_GAPS: none
SPEC_SCENARIO_MISSING: none
PLANNING_LIFECYCLE_GAP: none
UNRESOLVED_PRODUCT_SEMANTICS: none

## Steady-state / already-true reconcile

STEADY_STATE_RECONCILE: present

Unchanged settings are not duplicated is the already-true steady-state scenario. Repeated scheduler run remains idempotent covers periodic re-observation without a fresh producer event.

## Global evidence rules

RUNTIME_SCENARIO_SEAM: use real registry/canonical entrypoints for pure contract scenarios and real updater/locked-cabinet/collector orchestration for storage scenarios. Do not mock registry classification, normalization, state_hash, change-only comparison, or lock ownership logic.

RUNTIME_PROVIDER_BOUNDARIES:
- PG_SETTINGS_READ_V1: real isolated/local PostgreSQL discovery + batch settings reader.
- PG_HISTORY_XACT_LOCK_V1: real isolated/local PostgreSQL pg_try_advisory_xact_lock ownership/contention/liveness.
- CH_HISTORY_READ_V1: real isolated/local ClickHouse latest-hash/timeline read.
- CH_HISTORY_WRITE_V1: real isolated/local ClickHouse append plus durable read-after-write.

All four receipts are required fresh at mode=certify where their rows apply. Their absence now is not an unresolved semantic gap; mode=plan does not execute provider tests.

Production WB writes, production PostgreSQL settings mutation, and production ClickHouse migration/apply are forbidden evidence. Any destructive/local provider test keeps its own authorization gate.

MIGRATION_THIN_ENDS: existing in-process isolated migration target/coordinator contract; live provider receipts are not required for migration prerequisite rows.

STUB_PARITY_RULE: runtime seam stubs must match provider DTO/query/return/error shape; bare boolean mocks are insufficient.
LOAD_OR_PERFORMANCE: not_required
UNRESOLVED_GAPS: none
OPEN_QUESTIONS: none

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: campaign-settings-history
PLAN_STATUS: ready
SCENARIO_COUNT: 30

### SCENARIOS

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Build one canonical snapshot from registered settings sources
  REQUIREMENT_CONTEXT: Canonical campaign settings are versioned and source-authoritative
  LIFECYCLE_STEPS: L3,L4
  GIVEN_WHEN_THEN: GIVEN a campaign with campaign-level settings, keyword-level settings, shelf-bid settings, and schedule settings WHEN the history collector reads current settings THEN it MUST produce one canonical versioned settings snapshot for that campaign AND MUST preserve PostgreSQL as current-state authority AND MUST NOT treat ClickHouse history as a write authority
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_READ
  THIN_ENDS: PG_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings-read boundary
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: required: seam DTO/error parity with PG boundary
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::WB facts and runtime state stay outside settings history
  REQUIREMENT_CONTEXT: Canonical campaign settings are versioned and source-authoritative
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a WB-observed status, performance metric, spend value, diagnostic value, or transient runtime state changes while configured settings do not change WHEN the canonical settings snapshot is built THEN those excluded values MUST NOT change the canonical settings state AND MUST NOT create a settings-history snapshot by themselves
  PRODUCTION_ENTRYPOINT: build_canonical_settings_snapshot
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::New settings field cannot be forgotten
  REQUIREMENT_CONTEXT: Every candidate settings field has an explicit fail-closed policy
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a registered settings-owned source gains a new field WHEN contract validation runs before release THEN validation MUST fail until the field receives an explicit history and Excel classification AND a passing build MUST NOT depend on a developer remembering a second manual list
  PRODUCTION_ENTRYPOINT: validate_registry_against_inventory
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Removed or renamed field invalidates stale registry entry
  REQUIREMENT_CONTEXT: Every candidate settings field has an explicit fail-closed policy
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a classified field is removed or renamed in its settings-owned source WHEN contract validation runs THEN validation MUST fail while the registry and runtime field inventory disagree AND MUST require an explicit registry update
  PRODUCTION_ENTRYPOINT: validate_registry_against_inventory
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Excluded field requires a reason
  REQUIREMENT_CONTEXT: Every candidate settings field has an explicit fail-closed policy
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a candidate field is not part of settings history WHEN it is classified as excluded THEN the contract MUST record an explicit exclusion reason AND MUST still define its Excel policy
  PRODUCTION_ENTRYPOINT: validate_registry
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Reordered keyword or schedule rows do not create false change
  REQUIREMENT_CONTEXT: Canonical normalization and hash are deterministic
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN two reads contain the same logical settings but source rows arrive in a different order WHEN the canonical payload and state hash are computed THEN both reads MUST produce the same canonical state and hash
  PRODUCTION_ENTRYPOINT: build_canonical_settings_snapshot
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Contract semantics change requires schema version bump
  REQUIREMENT_CONTEXT: Canonical normalization and hash are deterministic
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a change alters canonical field shape, meaning, or normalization in a way that changes interpretation WHEN the new contract is released THEN it MUST use a new schema_version AND existing historical snapshots MUST remain interpretable under their recorded schema_version
  PRODUCTION_ENTRYPOINT: build_canonical_settings_snapshot
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::First observation creates baseline snapshot
  REQUIREMENT_CONTEXT: Settings history is change-only and append-only
  LIFECYCLE_STEPS: L2,L3,L4,L5,L6
  GIVEN_WHEN_THEN: GIVEN a campaign has no settings-history row WHEN the collector observes a valid canonical settings state THEN it MUST append one baseline snapshot
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ+CH_WRITE
  THIN_ENDS: PG_COORD+PG_READ+CH_READ+CH_WRITE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: required: real isolated/local ClickHouse append boundary
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Unchanged settings are not duplicated
  REQUIREMENT_CONTEXT: Settings history is change-only and append-only
  LIFECYCLE_STEPS: L2,L3,L4,L5,L7
  GIVEN_WHEN_THEN: GIVEN the latest stored snapshot has the same canonical state hash as the current settings WHEN the collector runs again THEN it MUST NOT append another snapshot
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ
  THIN_ENDS: PG_COORD+PG_READ+CH_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Changed settings append a new snapshot
  REQUIREMENT_CONTEXT: Settings history is change-only and append-only
  LIFECYCLE_STEPS: L2,L3,L4,L5,L6
  GIVEN_WHEN_THEN: GIVEN the latest stored snapshot exists WHEN one or more history-included settings change and the canonical state hash changes THEN the collector MUST append a new snapshot AND MUST leave prior snapshots unchanged
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ+CH_WRITE
  THIN_ENDS: PG_COORD+PG_READ+CH_READ+CH_WRITE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: required: real isolated/local ClickHouse append boundary
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Inactive settings owners remain observable
  REQUIREMENT_CONTEXT: Periodic collection is isolated from production settings writes
  LIFECYCLE_STEPS: L1,L3
  GIVEN_WHEN_THEN: GIVEN a cabinet/campaign owns current PostgreSQL settings rows but is absent from Redis active-shop discovery or has bot/WB active flags disabled WHEN the history updater discovers collection scope THEN that settings owner MUST remain eligible for history collection AND discovery MUST NOT depend on Redis active-shop membership, bot_active, or WB active_status
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_READ
  THIN_ENDS: PG_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings-read boundary
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: required: seam DTO/error parity with PG boundary
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Concurrent collectors serialize per cabinet
  REQUIREMENT_CONTEXT: Periodic collection is isolated from production settings writes
  LIFECYCLE_STEPS: L2,L5,L6
  GIVEN_WHEN_THEN: GIVEN one collector already owns the dedicated cabinet advisory transaction lock WHEN another collector attempts the same cabinet concurrently THEN the contender MUST report lock contention or skip that cabinet AND MUST NOT reach ClickHouse latest-hash comparison or history insert for that cabinet
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ+CH_WRITE
  THIN_ENDS: PG_COORD+PG_READ+CH_READ+CH_WRITE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: required: real isolated/local ClickHouse append boundary
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::History write failure does not mutate current settings
  REQUIREMENT_CONTEXT: Periodic collection is isolated from production settings writes
  LIFECYCLE_STEPS: L2,L3,L4,L5,L6,L7
  GIVEN_WHEN_THEN: GIVEN current settings can be read but history storage is unavailable WHEN a collection cycle runs THEN current settings MUST remain unchanged AND the cycle MUST expose a failed/degraded history result
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ+CH_WRITE
  THIN_ENDS: PG_COORD+PG_READ+CH_READ+CH_WRITE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: required: real isolated/local ClickHouse append boundary
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Repeated scheduler run remains idempotent
  REQUIREMENT_CONTEXT: Periodic collection is isolated from production settings writes
  LIFECYCLE_STEPS: L1,L2,L3,L4,L5,L6,L7
  GIVEN_WHEN_THEN: GIVEN the scheduler runs more than once while settings are unchanged WHEN each cycle completes THEN at most one snapshot for that canonical state MUST exist as the latest change event
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_COORD+PG_READ+CH_READ+CH_WRITE
  THIN_ENDS: PG_COORD+PG_READ+CH_READ+CH_WRITE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: required: real isolated/local ClickHouse append boundary
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings read + ClickHouse latest/timeline read boundary
    BOUNDARY_INTEGRATION_OTHER: required: real isolated/local PostgreSQL pg_try_advisory_xact_lock boundary
    STUB_CONTRACT: required: seam stubs must match provider DTO/query/error contracts
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Adding a field forces an Excel decision
  REQUIREMENT_CONTEXT: Excel is a human-facing projection of the same field contract
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN a new settings field is added WHEN contract validation runs THEN the field MUST have an explicit Excel policy before validation passes AND the policy MAY be editable, read-only, or excluded
  PRODUCTION_ENTRYPOINT: registry-backed Excel projection validation
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Excel cannot silently diverge from history contract
  REQUIREMENT_CONTEXT: Excel is a human-facing projection of the same field contract
  LIFECYCLE_STEPS: L4
  GIVEN_WHEN_THEN: GIVEN the Excel projection contains an editable or read-only field not permitted by the canonical registry, or omits a registry field without an explicit excluded policy WHEN parity validation runs THEN validation MUST fail
  PRODUCTION_ENTRYPOINT: registry-backed Excel projection validation
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Read campaign settings timeline
  REQUIREMENT_CONTEXT: History remains queryable by campaign and time
  LIFECYCLE_STEPS: L6
  GIVEN_WHEN_THEN: GIVEN multiple settings changes were recorded for one campaign WHEN a caller requests that campaign's history for a time interval THEN the system MUST return snapshots in deterministic temporal order AND each snapshot MUST expose its schema_version and state hash
  PRODUCTION_ENTRYPOINT: ClickHouseCampaignSettingsHistoryRepository.timeline
  CAUSAL_PATH: CH_READ
  THIN_ENDS: CH_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: required: real isolated/local ClickHouse history-read boundary
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: required: seam query/result parity with CH boundary
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/campaign-settings-history/spec.md::Unsupported field value is not recorded as valid history
  REQUIREMENT_CONTEXT: Unknown or unsupported settings state fails closed
  LIFECYCLE_STEPS: L3,L4,L7
  GIVEN_WHEN_THEN: GIVEN current settings contain a value the active schema_version cannot normalize WHEN the collector builds the canonical snapshot THEN it MUST fail that campaign snapshot AND MUST NOT append a replacement history row with partial or guessed data
  PRODUCTION_ENTRYPOINT: CampaignSettingsHistoryUpdater.run_once / collect_one_locked_cabinet / collect_cabinet
  CAUSAL_PATH: PG_READ
  THIN_ENDS: PG_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: required: real isolated/local PostgreSQL settings-read boundary
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: required: seam DTO/error parity with PG boundary
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Register reviewed 001 through 006 without execution
  REQUIREMENT_CONTEXT: Corpus identity stays immutable and separate from applied state
  LIFECYCLE_STEPS: M1
  GIVEN_WHEN_THEN: GIVEN reviewed versions `001` through `006` exist and no target ledger is attached WHEN the control plane accepts the corpus THEN it MUST record version id, filename, privilege class, and raw-byte SHA-256 for every version AND MUST classify `005` as privileged grant and `006` as schema DDL AND MUST NOT execute any statement AND MUST NOT record any version as applied
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::File presence is not applied state
  REQUIREMENT_CONTEXT: Corpus identity stays immutable and separate from applied state
  LIFECYCLE_STEPS: M1
  GIVEN_WHEN_THEN: GIVEN reviewed corpus files are present WHEN an operator asks whether a version is applied THEN the system MUST answer only from target ledger state AND MUST NOT write `version_applied` because the file exists
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET_READ
  THIN_ENDS: MIG_TARGET_READ
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Plan includes reviewed 006 without execution
  REQUIREMENT_CONTEXT: Plan does not execute and apply needs explicit authorization
  LIFECYCLE_STEPS: M2
  GIVEN_WHEN_THEN: GIVEN reviewed corpus `001`–`006` WHEN the operator requests a plan THEN the plan MUST include `006` in version order with its privilege class, checksum, statements, and stop reason when applicable AND MUST NOT execute SQL AND MUST NOT write target state AND MUST NOT acquire a writer lock
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Schema writer may run reviewed 006 under existing gates
  REQUIREMENT_CONTEXT: Plan does not execute and apply needs explicit authorization
  LIFECYCLE_STEPS: M3
  GIVEN_WHEN_THEN: GIVEN an isolated target satisfies every existing schema-apply gate and reviewed `006` is not partial or applying WHEN authorized apply reaches `006` THEN the schema writer MUST execute `006` as schema DDL AND MUST use the same apply_started → statement_ok → version_applied event protocol AND MUST NOT execute `005`
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Apply without authorization still refuses
  REQUIREMENT_CONTEXT: Plan does not execute and apply needs explicit authorization
  LIFECYCLE_STEPS: M3
  GIVEN_WHEN_THEN: GIVEN reviewed `006` is otherwise eligible WHEN apply authorization is absent THEN apply MUST refuse before executing `006`
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Authorized apply still refuses 005
  REQUIREMENT_CONTEXT: Privileged grant 005 never enters the schema writer
  LIFECYCLE_STEPS: M3
  GIVEN_WHEN_THEN: GIVEN the target satisfies schema-apply gates WHEN apply reaches `005` THEN the system MUST refuse before the schema writer receives `005` AND `005` MUST NOT be executed
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Qualification stays in reviewed SQL
  REQUIREMENT_CONTEXT: Privileged grant 005 never enters the schema writer
  LIFECYCLE_STEPS: M1
  GIVEN_WHEN_THEN: GIVEN reviewed bytes `001`–`006` WHEN the corpus is validated THEN schema DDL `001`–`004` and `006` MUST retain default database qualification AND `005` MUST retain its system-object qualification AND validation MUST NOT rewrite those files
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Isolated apply includes reviewed 006
  REQUIREMENT_CONTEXT: This change mutates only an isolated target and does not touch production
  LIFECYCLE_STEPS: M3
  GIVEN_WHEN_THEN: GIVEN an isolated test target and coordinator satisfy all migration gates WHEN authorized apply reaches reviewed `006` THEN the runner MUST execute its schema DDL and close it with `version_applied` only after all statements succeed AND the production target MUST remain untouched
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Production target still refuses
  REQUIREMENT_CONTEXT: This change mutates only an isolated target and does not touch production
  LIFECYCLE_STEPS: M4
  GIVEN_WHEN_THEN: GIVEN the target is classified as production WHEN ensure-ledger, reconcile, or apply is requested THEN the control plane MUST refuse before target mutation
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Application runtime client is not the migration executor
  REQUIREMENT_CONTEXT: This change mutates only an isolated target and does not touch production
  LIFECYCLE_STEPS: M4
  GIVEN_WHEN_THEN: GIVEN application runtime ClickHouse access exists WHEN reviewed `006` is validated or applied in tests THEN the migration control plane MUST NOT use the application runtime client as executor
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Reviewed 006 is accepted
  REQUIREMENT_CONTEXT: Reviewed 006 enters the corpus and an unreviewed successor blocks apply
  LIFECYCLE_STEPS: M1
  GIVEN_WHEN_THEN: GIVEN reviewed `006` is present with its accepted raw-byte SHA-256 WHEN the control plane builds the corpus fingerprint THEN the fingerprint MUST be exactly `001`–`006` AND `006` MUST be classified as schema DDL
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: NONE
  THIN_ENDS: NONE
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: not_applicable
    STUB_CONTRACT: not_applicable
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

- SCENARIO_ID: openspec/changes/campaign-settings-history/specs/clickhouse-migration-lifecycle/spec.md::Unreviewed successor blocks apply
  REQUIREMENT_CONTEXT: Reviewed 006 enters the corpus and an unreviewed successor blocks apply
  LIFECYCLE_STEPS: M1,M3
  GIVEN_WHEN_THEN: GIVEN a numeric migration file is not in the reviewed fingerprint WHEN apply is requested THEN the system MUST classify it as unreviewed AND MUST block apply AND MUST NOT execute it
  PRODUCTION_ENTRYPOINT: scripts.clickhouse_migration_control_plane validate/plan/apply/status
  CAUSAL_PATH: MIG_TARGET+MIG_COORD
  THIN_ENDS: MIG_TARGET+MIG_COORD
  REQUIRED_EVIDENCE:
    SCENARIO_SEAM: required
    BOUNDARY_INTEGRATION_WRITE: not_applicable
    BOUNDARY_INTEGRATION_READ: not_applicable
    BOUNDARY_INTEGRATION_OTHER: required: existing in-process isolated migration target/coordinator contract
    STUB_CONTRACT: required: recording-port/coordinator shared contract
    UNIT_COMPONENT: optional/additive
    LOAD_OR_PERFORMANCE: not_required
  EXECUTION_IN_PLAN_MODE: NOT_EXECUTED
  ROW_PLAN_STATUS: ready

## Provider route requirements

Future certify inputs, not unresolved product semantics: PG settings-read receipt, PG xact-lock receipt, CH read receipt, CH write/read-after-write receipt.

PLAN_STATUS: ready
MATERIALIZATION_STATUS: COMMITTED
UNRESOLVED_GAPS: none
OPEN_QUESTIONS: none
