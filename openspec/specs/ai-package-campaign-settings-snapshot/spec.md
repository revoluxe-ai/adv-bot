# ai-package-campaign-settings-snapshot Specification

## Purpose

Read-only detailed campaign settings snapshot for AI Package: machine-readable
domain contract with explicit grain, leg identity, source authority, provenance,
freshness, and completeness — independent of ZIP transport and independent of
control-plane or Redis operational DTOs. Synced from change
`ai-package-campaign-settings-snapshot` (archived 2026-10-05).

## Requirements

### Requirement: Dedicated domain contract separate from control-plane and Redis DTOs

The detailed campaign settings export MUST use domain contract
`CampaignSettingsSnapshotV1` owned by the AI Package export module. Export MUST
NOT treat `CampaignResourceSnapshotV1` (control plane) or
`AdvSettingsSnapshotDTO` (snapshot_data_updater Redis tick) as the export schema.
Manifest card id MUST remain `campaign_settings_snapshot`.

#### Scenario: Export payload is not control-plane snapshot

- **GIVEN** export assembles detailed campaign settings for shop S
- **WHEN** domain payload is serialized
- **THEN** payload schema MUST be `CampaignSettingsSnapshotV1`
- **AND** MUST NOT be a serialized `CampaignResourceSnapshotV1` document

#### Scenario: Export payload is not Redis tick DTO

- **GIVEN** Redis operational snapshot exists for the same shop
- **WHEN** AI Package export builds settings snapshot
- **THEN** export MUST NOT use `AdvSettingsSnapshotDTO` as the contract schema
- **AND** MUST NOT inherit `bot_active`-only scope filter from snapshot_data_updater

### Requirement: Grain and campaign leg identity

Each exported record MUST be keyed by `(shop_id, adv_setting_id)` where
`adv_setting_id` is the PostgreSQL anchor row. Auto (shelf) and Search (keywords)
MUST appear as separate leg sections with distinct `wb_adv_id` values when present.
Legs MUST NOT be silently merged into one indistinguishable campaign row. Pair
linkage MUST be explicit metadata, not inferred from legacy type codes 8 or 9.
Primary export grain MUST NOT be `cmp_*` control-plane resource id.

#### Scenario: Auto and Search legs remain distinguishable

- **GIVEN** an inventory row with auto `adv_id` A and search `search_adv_id` K
- **WHEN** detailed settings snapshot is exported
- **THEN** the record MUST contain separate auto and search leg sections
- **AND** MUST include both A and K as distinct `wb_adv_id` values
- **AND** MUST NOT replace them with a single synthetic campaign id

#### Scenario: Primary grain uses adv_setting anchor

- **GIVEN** export includes detailed settings rows
- **WHEN** a consumer reads record keys
- **THEN** each row MUST include `shop_id` and `adv_setting_id`
- **AND** MUST NOT require `cmp_*` resource_id as the primary key

### Requirement: Source authority classes and field provenance

Every exported field MUST declare an authority class and provenance metadata:
`WB_AUTHORITATIVE`, `LOCAL_POLICY`, `INVENTORY_RELATION`, `UNKNOWN`, or
`UNSUPPORTED`. WB authoritative values and local AdvSetting policy MUST NOT be
silently conflated. When sources conflict, provenance MUST name the value actually
exported and MUST NOT claim a higher authority than evidence supports.

#### Scenario: Local policy not masquerading as WB state

- **GIVEN** a field exists only in local AdvSetting policy columns
- **WHEN** the field is exported
- **THEN** provenance MUST classify it as `LOCAL_POLICY`
- **AND** MUST NOT classify it as `WB_AUTHORITATIVE`

#### Scenario: Unsupported field slot stays explicit

- **GIVEN** a settings field is listed in the contract but no safe reader exists in the active export slice
- **WHEN** export completes
- **THEN** the field MUST be omitted or marked with authority `UNSUPPORTED`
- **AND** `reason_codes` MUST include an explicit unsupported indicator
- **AND** export MUST NOT inject a fabricated default value

### Requirement: Unknown null and missing state without fabricated defaults

Missing, null, and unknown WB or local values MUST remain explicit in export.
Export MUST NOT apply generated-client default injection or DTO constructor
defaults to replace null/missing reads. Nullable database null MUST export as JSON
null with provenance, not as inferred enum/string defaults.

#### Scenario: Null PG column stays null

- **GIVEN** an AdvSetting column value is SQL NULL
- **WHEN** the column is exported
- **THEN** export MUST emit JSON null or explicit UNKNOWN wrapper
- **AND** MUST NOT substitute a non-null default from client models or Redis DTOs

#### Scenario: Unknown WB field fails closed for mutation eligibility

- **GIVEN** a downstream consumer uses export for mutation eligibility heuristics
- **WHEN** a required WB-authoritative field is `UNKNOWN`
- **THEN** consumer MUST treat mutation as disallowed based on export semantics
- **AND** export MUST NOT mark the field as authoritative success

### Requirement: Snapshot timestamp freshness and completeness semantics

The settings snapshot MUST carry `snapshot_assembled_at` for the export assembly
event. Dataset card MUST carry independent `collection_outcome`, `coverage`,
`reason_codes`, and `freshness` per coverage-provenance rules. Freshness MUST NOT
substitute for entity coverage. Inventory export MUST NOT claim full WB cabinet
campaign universe coverage. Point-in-time snapshot MUST NOT imply historical period
completeness for settings unless a separate time-series source is defined.

#### Scenario: Four completeness dimensions stay independent

- **GIVEN** export emits detailed settings card metadata
- **WHEN** metadata is read
- **THEN** `collection_outcome`, `coverage`, `reason_codes`, and `freshness` MUST each be present
- **AND** fresh assembly time MUST NOT alone imply `coverage=FULL` for WB universe

#### Scenario: Partial PG WB sync is explicit

- **GIVEN** WB-authoritative fields are only partially available from accumulated PostgreSQL sync columns
- **WHEN** export completes
- **THEN** `coverage` MUST reflect partial settings coverage
- **AND** appropriate `reason_codes` MUST document partial WB sync
- **AND** export MUST NOT claim full detailed WB settings coverage

### Requirement: Read-only accumulated sources on export path

Detailed settings snapshot on the AI Package export path MUST read accumulated
PostgreSQL (and ClickHouse only when a field's source card assigns CH with
evidence). Export MUST NOT invoke WB API, MUST NOT start collectors, and MUST NOT
mutate AdvSetting, Redis, queues, campaign lifecycle, budgets, bids, or
`bot_active`.

#### Scenario: No WB API on settings export path

- **GIVEN** export builds detailed campaign settings snapshot
- **WHEN** datasets are loaded
- **THEN** no WB HTTP client or promotion adapter MUST run on the export path

#### Scenario: Export does not write operational state

- **GIVEN** export completes successfully
- **WHEN** PostgreSQL and Redis state are compared before and after
- **THEN** no campaign settings, bot flags, or snapshot_data_updater keys MUST change

### Requirement: Transport-decoupled AI Package dataset exposure

Settings snapshot MUST be exposable as an AI Package dataset through manifest
card `campaign_settings_snapshot` referencing a versioned domain JSON payload and
`sha256`. Domain contract MUST be independent of ZIP encoding. Card MUST declare
whether detailed settings export is active versus minimal inventory-only v1
semantics.

#### Scenario: Manifest references domain payload

- **GIVEN** export produces ZIP transport
- **WHEN** manifest describes `campaign_settings_snapshot`
- **THEN** manifest MUST reference logical payload file, schema version, and hash
- **AND** validator MUST apply to domain JSON without requiring a specific compression library beyond listed files

#### Scenario: Detailed export flag distinguishes v1 inventory

- **GIVEN** detailed settings export is enabled per this change
- **WHEN** manifest card is emitted
- **THEN** card MUST indicate detailed settings export semantics
- **AND** MUST NOT reuse minimal inventory-only coverage claims from v1
