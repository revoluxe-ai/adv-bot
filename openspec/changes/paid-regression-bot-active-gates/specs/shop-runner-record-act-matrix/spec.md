## ADDED Requirements

### Requirement: Shop-runner operations classified as RECORD or ACT

Every shop-runner background coroutine that processes advertising campaigns MUST be classified as either RECORD (data ingestion and persistence without changing WB ad state) or ACT (mutations of WB advertising state).

#### Scenario: Matrix covers all WBShop run coroutines

- **WHEN** a maintainer reviews the record-act matrix documentation
- **THEN** each coroutine started from the shop run worker is listed with RECORD or ACT classification

### Requirement: RECORD operations target cabinet connectivity not bot active

After the planned data-loader refactor, RECORD operations for a shop MUST run for all non-finished campaigns in a connected cabinet with a valid token, regardless of bot active on individual campaigns.

#### Scenario: Stats ingestion independent of bot active

- **WHEN** a campaign has bot active disabled
- **AND** the cabinet is connected with a valid token
- **THEN** statistics and keyword stamp recording pipelines still run for that campaign

#### Scenario: Snapshot and cache warming for inactive campaigns

- **WHEN** bot active is disabled on campaigns in an active shop
- **THEN** snapshot updater and read-cache warming MAY include those campaigns for analytics (subject to follow-up loader change)

### Requirement: ACT operations require bot active enabled

ACT operations MUST NOT mutate Wildberries advertising state for campaigns where bot active is disabled.

#### Scenario: Single gate semantics for ACT

- **WHEN** any classified ACT coroutine runs
- **THEN** it processes only campaigns where bot active is enabled (or skips WB writes for inactive campaigns)

### Requirement: Data loader separates campaign discovery from paid action eligibility

The shop data loading layer MUST distinguish:

- campaigns eligible for RECORD (connected cabinet, non-done status)
- campaigns eligible for ACT (bot active enabled, plus feature-specific flags)

#### Scenario: Loader refactor does not break paid ACT filtering

- **WHEN** campaign discovery is expanded to include bot-inactive campaigns for RECORD
- **THEN** ACT coroutines still filter to bot-active campaigns only

### Requirement: WB write path inventory maintained

The project MUST maintain an inventory of Wildberries-impacting write paths used by automation, cross-referenced with ACT classification and bot active gate tests.

#### Scenario: New write path requires matrix update

- **WHEN** a developer adds a new automation that mutates WB ad state
- **THEN** they update the record-act matrix and add or extend bot active gate tests

### Requirement: Top-key whitelist path is paid v2 only

The `update_top_key_in_advs` ACT path MUST be treated as applicable only for paid v2 / non-v3 campaigns. V3 whitelist behavior belongs to `adv_settings_auto_update` / `process_adv_v3`.

#### Scenario: V2 and v3 whitelist paths stay separated

- **WHEN** a maintainer reviews whitelist ACT coverage
- **THEN** `update_top_key_in_advs` is listed as paid v2 / non-v3 only
- **AND** v3 whitelist coverage points to `adv_settings_auto_update` / `process_adv_v3`
