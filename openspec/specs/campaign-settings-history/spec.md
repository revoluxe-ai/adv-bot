# campaign-settings-history Specification

## Purpose
Canonical campaign settings history contract: registry-backed settings snapshots,
PostgreSQL authority, ClickHouse append-only history, Excel parity.

## Requirements

### Requirement: Canonical campaign settings are versioned and source-authoritative

The system MUST build one canonical campaign-settings snapshot from registered settings-owned sources while PostgreSQL remains the authority for current settings. The canonical snapshot MUST distinguish settings and identity metadata from WB-observed facts, runtime state, derived metrics, diagnostics, and technical storage fields. ClickHouse history MUST NOT become authority for current production settings writes.

#### Scenario: Build one canonical snapshot from registered settings sources
- **GIVEN** a campaign with campaign-level settings, keyword-level settings, shelf-bid settings, and schedule settings
- **WHEN** the history collector reads current settings
- **THEN** it MUST produce one canonical versioned settings snapshot for that campaign
- **AND** MUST preserve PostgreSQL as current-state authority
- **AND** MUST NOT treat ClickHouse history as a write authority

#### Scenario: WB facts and runtime state stay outside settings history
- **GIVEN** a WB-observed status, performance metric, spend value, diagnostic value, or transient runtime state changes while configured settings do not change
- **WHEN** the canonical settings snapshot is built
- **THEN** those excluded values MUST NOT change the canonical settings state
- **AND** MUST NOT create a settings-history snapshot by themselves

### Requirement: Every candidate settings field has an explicit fail-closed policy

For every field in every registered settings-owned source, the system MUST have an explicit classification that defines semantic role, history policy, Excel policy, normalization/type policy, and an exclusion reason when excluded. An unknown, added, removed, or renamed candidate field without an updated classification MUST fail deterministic validation and MUST NOT be silently included or silently excluded.

#### Scenario: New settings field cannot be forgotten
- **GIVEN** a registered settings-owned source gains a new field
- **WHEN** contract validation runs before release
- **THEN** validation MUST fail until the field receives an explicit history and Excel classification
- **AND** a passing build MUST NOT depend on a developer remembering a second manual list

#### Scenario: Removed or renamed field invalidates stale registry entry
- **GIVEN** a classified field is removed or renamed in its settings-owned source
- **WHEN** contract validation runs
- **THEN** validation MUST fail while the registry and runtime field inventory disagree
- **AND** MUST require an explicit registry update

#### Scenario: Excluded field requires a reason
- **GIVEN** a candidate field is not part of settings history
- **WHEN** it is classified as excluded
- **THEN** the contract MUST record an explicit exclusion reason
- **AND** MUST still define its Excel policy

### Requirement: Canonical normalization and hash are deterministic

The system MUST serialize canonical settings with an explicit schema_version and deterministic normalization. Logically equivalent settings MUST yield the same state hash regardless of source row ordering or collection timing. Collector timestamps and other non-domain metadata MUST NOT affect the state hash. A contract-shape or normalization change that changes interpretation MUST use a new schema_version.

#### Scenario: Reordered keyword or schedule rows do not create false change
- **GIVEN** two reads contain the same logical settings but source rows arrive in a different order
- **WHEN** the canonical payload and state hash are computed
- **THEN** both reads MUST produce the same canonical state and hash

#### Scenario: Contract semantics change requires schema version bump
- **GIVEN** a change alters canonical field shape, meaning, or normalization in a way that changes interpretation
- **WHEN** the new contract is released
- **THEN** it MUST use a new schema_version
- **AND** existing historical snapshots MUST remain interpretable under their recorded schema_version

### Requirement: Settings history is change-only and append-only

The system MUST append an initial canonical snapshot when no prior history exists for a campaign. On later collections it MUST append a new snapshot only when the canonical state hash differs from the latest stored hash for that campaign. Consecutive identical settings MUST NOT create duplicate history rows. History retention MUST NOT delete prior snapshots when the current campaign row later disappears.

#### Scenario: First observation creates baseline snapshot
- **GIVEN** a campaign has no settings-history row
- **WHEN** the collector observes a valid canonical settings state
- **THEN** it MUST append one baseline snapshot

#### Scenario: Unchanged settings are not duplicated
- **GIVEN** the latest stored snapshot has the same canonical state hash as the current settings
- **WHEN** the collector runs again
- **THEN** it MUST NOT append another snapshot

#### Scenario: Changed settings append a new snapshot
- **GIVEN** the latest stored snapshot exists
- **WHEN** one or more history-included settings change and the canonical state hash changes
- **THEN** the collector MUST append a new snapshot
- **AND** MUST leave prior snapshots unchanged

### Requirement: Periodic collection is isolated from production settings writes

The system MUST support periodic history collection with an operational target cadence of approximately five minutes. Discovery MUST come from PostgreSQL settings ownership rather than Redis active-shop membership, bot-active state, or WB campaign active status. Collection MUST be read-only against current settings authority. Concurrent collectors for the same cabinet MUST serialize through the dedicated transaction-scoped PostgreSQL advisory lock. Failure to normalize or write history MUST NOT mutate current settings and MUST surface an observable failure rather than silently pretending that history was recorded.

#### Scenario: Inactive settings owners remain observable
- **GIVEN** a cabinet/campaign owns current PostgreSQL settings rows but is absent from Redis active-shop discovery or has bot/WB active flags disabled
- **WHEN** the history updater discovers collection scope
- **THEN** that settings owner MUST remain eligible for history collection
- **AND** discovery MUST NOT depend on Redis active-shop membership, bot_active, or WB active_status

#### Scenario: Concurrent collectors serialize per cabinet
- **GIVEN** one collector already owns the dedicated cabinet advisory transaction lock
- **WHEN** another collector attempts the same cabinet concurrently
- **THEN** the contender MUST report lock contention or skip that cabinet
- **AND** MUST NOT reach ClickHouse latest-hash comparison or history insert for that cabinet

#### Scenario: History write failure does not mutate current settings
- **GIVEN** current settings can be read but history storage is unavailable
- **WHEN** a collection cycle runs
- **THEN** current settings MUST remain unchanged
- **AND** the cycle MUST expose a failed/degraded history result

#### Scenario: Repeated scheduler run remains idempotent
- **GIVEN** the scheduler runs more than once while settings are unchanged
- **WHEN** each cycle completes
- **THEN** at most one snapshot for that canonical state MUST exist as the latest change event

### Requirement: Excel is a human-facing projection of the same field contract

Excel export/import MUST consume the canonical field classification rather than define an independent settings truth. Each classified field MUST have an explicit Excel policy: editable, read-only, or excluded. A history-included field MAY be excluded from Excel, but that exclusion MUST be explicit. Excel MUST NOT make an excluded field editable, and projection parity validation MUST fail when Excel and the canonical registry drift.

#### Scenario: Adding a field forces an Excel decision
- **GIVEN** a new settings field is added
- **WHEN** contract validation runs
- **THEN** the field MUST have an explicit Excel policy before validation passes
- **AND** the policy MAY be editable, read-only, or excluded

#### Scenario: Excel cannot silently diverge from history contract
- **GIVEN** the Excel projection contains an editable or read-only field not permitted by the canonical registry, or omits a registry field without an explicit excluded policy
- **WHEN** parity validation runs
- **THEN** validation MUST fail

### Requirement: History remains queryable by campaign and time

The system MUST preserve enough identity metadata to retrieve the ordered settings snapshots for a campaign over a requested time range and identify the schema_version and state hash of each snapshot. Querying history MUST be read-only.

#### Scenario: Read campaign settings timeline
- **GIVEN** multiple settings changes were recorded for one campaign
- **WHEN** a caller requests that campaign's history for a time interval
- **THEN** the system MUST return snapshots in deterministic temporal order
- **AND** each snapshot MUST expose its schema_version and state hash

### Requirement: Unknown or unsupported settings state fails closed

If a registered source cannot be normalized under the current contract, contains an unknown classified value, or violates a required type/enum contract, the system MUST NOT persist a misleading canonical snapshot. The collector MUST surface the unsupported state and leave the latest valid history unchanged.

#### Scenario: Unsupported field value is not recorded as valid history
- **GIVEN** current settings contain a value the active schema_version cannot normalize
- **WHEN** the collector builds the canonical snapshot
- **THEN** it MUST fail that campaign snapshot
- **AND** MUST NOT append a replacement history row with partial or guessed data
