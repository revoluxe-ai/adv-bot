## ADDED Requirements

### Requirement: Inactive bot blocks common search bid WB write

When bot active is disabled on a campaign, the system MUST NOT apply common bid updates to the search campaign on Wildberries, even if common bid automation flags are enabled.

#### Scenario: Common bid coroutine skips WB write when inactive

- **WHEN** shop-runner runs common search bid update for a campaign with bot active disabled
- **AND** common bid automation is enabled for that campaign
- **AND** the test supplies a non-empty WB adverts DTO/search input that would reach the common-bid write manager if the bot-active guard were missing
- **THEN** no common search bid mutation is sent to Wildberries

### Requirement: Inactive bot blocks keyword target place WB write

When bot active is disabled, the system MUST NOT update target positions for keywords on Wildberries through automated target-place pipelines (including individual keyword target place and auto-updater v3 target place sync).

#### Scenario: Individual target place updater skips when inactive

- **WHEN** shop-runner runs individual keyword target place update
- **AND** campaign has bot active disabled
- **AND** individual target place mode is enabled
- **THEN** no target place mutation is applied on Wildberries for that campaign

#### Scenario: Auto-updater v3 skips target place actions when inactive

- **WHEN** auto-updater v3 processes a campaign with bot active disabled
- **THEN** no automated target place write actions are applied on Wildberries

### Requirement: Inactive bot blocks whitelist automation WB write

When bot active is disabled, the system MUST NOT add, remove, or trim whitelist phrases on Wildberries through automated whitelist pipelines.

#### Scenario: Top key whitelist updater skips when inactive

- **WHEN** shop-runner runs top-key whitelist update
- **AND** campaign has bot active disabled
- **AND** auto whitelist update is enabled
- **AND** the campaign is in the v2 / non-v3 updater path where `update_top_key_in_advs` is applicable
- **THEN** no whitelist mutation is sent to Wildberries

#### Scenario: Top key whitelist updater is paid v2 only

- **WHEN** top-key whitelist behavior is tested for a campaign with bot active enabled
- **AND** the campaign uses updater v2 / non-v3 automation
- **THEN** `update_top_key_in_advs` is the applicable ACT path
- **AND** v3 whitelist behavior is covered through `adv_settings_auto_update` / `process_adv_v3`

#### Scenario: Whitelist tail trimmer skips when inactive

- **WHEN** shop-runner runs whitelist tail trimming
- **AND** campaign has bot active disabled
- **AND** whitelist trim mode is enabled
- **THEN** no whitelist trim mutation is sent to Wildberries

### Requirement: Inactive bot blocks shelf bid WB write

When bot active is disabled, the system MUST NOT set or change shelf campaign bids on Wildberries through automated shelf bid control.

#### Scenario: Shelf bid control skips setter when inactive

- **WHEN** shelf bid control runs for a campaign with bot active disabled
- **AND** shelf bid control is enabled in settings
- **THEN** no shelf bid PATCH is sent to Wildberries

### Requirement: Inactive bot blocks additional paid ACT writes

When bot active is disabled, the system MUST NOT execute other paid automation
WB writes: cluster bid updates and CPM bidder updates, when their respective
automation is enabled. Auto minus-phrase updates are part of the free package
and are gated by `auto_update_minus_phrases` (default off), not by bot active.

#### Scenario: Cluster bids skip when inactive

- **WHEN** cluster bid update runs for a campaign with bot active disabled and bidder active
- **THEN** no cluster bid mutation is sent to Wildberries

#### Scenario: Free campaign with minus flag still syncs minus phrases

- **WHEN** minus phrase update runs for a campaign with bot active disabled
- **AND** `auto_update_minus_phrases` is enabled
- **THEN** minus phrase mutation MAY be sent to Wildberries (free package)

### Requirement: Gate tests use enabled flags to detect leaks

Bot active gate tests MUST configure automation flags as enabled while bot active is disabled, and MUST provide non-empty downstream inputs for coroutines that otherwise return early, so that missing gates are detected as test failures.

#### Scenario: Leak detection with flags on

- **WHEN** a gate test runs with bot active disabled and all relevant automation flags enabled
- **AND** the mocked loader/resolver inputs make the WB write path reachable except for the bot-active gate
- **AND** implementation incorrectly performs a WB write
- **THEN** the gate test fails

### Requirement: Recording path specification for inactive campaigns

The target product behavior (validated after data-loader refactor) is that recording pipelines continue for connected cabinets when bot active is disabled. Gate documentation MUST distinguish ACT gate tests (required now) from RECORD continuation tests (may be marked expected-fail until loader refactor).

#### Scenario: Recording tests documented as future contract

- **WHEN** a developer reads bot active gates documentation
- **THEN** they see which tests verify recording continues when inactive and which are expected-fail until loader refactor
