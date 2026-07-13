## ADDED Requirements

### Requirement: A/B Hold is paid-only
The system MUST expose and enable the card A/B Hold mode only for campaigns with paid bot management active. When paid bot management is inactive, the A/B Hold entry MUST be hidden and enable MUST NOT be executed through UI, Excel, or other write paths.

#### Scenario: Inactive bot hides A/B Hold
- **GIVEN** a campaign does not have paid bot management active
- **WHEN** the user opens the campaign settings menus
- **THEN** the A/B Hold mode entry is not shown
- **AND** enabling A/B Hold for that campaign is not performed

#### Scenario: Active paid bot can open A/B Hold screen
- **GIVEN** a campaign has paid bot management active
- **WHEN** the user opens the A/B Hold mode screen for that campaign
- **THEN** the system shows the mode instruction and enable/disable controls

### Requirement: A/B Hold screen includes instruction and controls
The system MUST provide a dedicated A/B Hold screen with instruction text and controls to enable the mode, disable the mode, and return to the campaign menu. The instruction MUST warn that before enable the campaign SHOULD have warm-up traffic under a non-squeezed max CPO and a sufficient sales plan, that shelf mode is recommended off (user choice if shelves are required for traffic), and that price SHOULD NOT be changed during the test.

#### Scenario: User opens instruction screen
- **GIVEN** a campaign has paid bot management active
- **WHEN** the user opens the A/B Hold screen
- **THEN** the instruction text is visible
- **AND** enable, disable, and back controls are available

### Requirement: ENTER setup classifies keywords by pay_for_order and views
When A/B Hold is enabled, the system MUST run a one-time setup that classifies keywords against the campaign plan max CPO (not resolve) and weekly keyword views from the same statistics source as the keyword card.

#### Scenario: Keyword passes setup
- **GIVEN** paid bot management is active
- **AND** a keyword has pay_for_order less than or equal to plan max CPO
- **AND** that keyword has at least 100 views in the weekly keyword-card statistics window
- **WHEN** A/B Hold enter setup runs
- **THEN** the keyword remains active for the held profile
- **AND** the keyword target place is set to the keyword's current actual place

#### Scenario: Keyword fails on expensive pay_for_order
- **GIVEN** a keyword has pay_for_order greater than plan max CPO
- **WHEN** A/B Hold enter setup runs
- **THEN** the keyword is turned OFF for the held profile

#### Scenario: Keyword fails on insufficient views
- **GIVEN** a keyword has fewer than 100 views in the weekly keyword-card statistics window
- **WHEN** A/B Hold enter setup runs
- **THEN** the keyword is turned OFF for the held profile

#### Scenario: Keyword fails when pay_for_order is missing
- **GIVEN** a keyword has no pay_for_order value
- **WHEN** A/B Hold enter setup runs
- **THEN** the keyword is turned OFF for the held profile

### Requirement: HOLD freezes target places and keeps bidder running
While A/B Hold is active after setup, the system MUST NOT update keyword target places automatically, MUST keep the bidder running so bids follow the fixed target places, and MUST NOT perform structural whitelist expansion/trimming or keyword enable/rollout growth. Overspend protection relative to plan max CPO MAY still turn expensive keywords OFF.

#### Scenario: Target places stay fixed while bidder continues
- **GIVEN** a campaign is in active A/B Hold after successful setup
- **WHEN** automation ticks run during the hold period
- **THEN** keyword target places are not auto-updated to new targets
- **AND** the bidder continues updating bids toward the fixed target places

#### Scenario: Structural key-set changes are blocked during hold
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** automatic whitelist or keyword enable/growth pipelines run
- **THEN** those pipelines do not apply structural whitelist or enable changes for that campaign

#### Scenario: Overspend guard may still protect spend
- **GIVEN** a campaign is in active A/B Hold
- **AND** a keyword exceeds the campaign plan max CPO under overspend protection rules
- **WHEN** hold protection runs
- **THEN** that keyword MAY be turned OFF to protect spend
- **AND** target-place auto-updates remain disabled

### Requirement: Ordinary structural auto-update is suspended during A/B Hold preparation and hold
While a campaign is preparing or holding for A/B Hold, the system MUST NOT run ordinary structural campaign auto-update that changes whitelist membership, target places, or keyword enable/rollout outside the A/B Hold setup and hold protection paths.

#### Scenario: Ordinary auto-update skips structural work during hold
- **GIVEN** a campaign is preparing or holding for A/B Hold
- **WHEN** ordinary structural campaign auto-update would run
- **THEN** that ordinary structural path does not change the campaign's held profile

### Requirement: Enter interrupts unsafe concurrent structural apply
When the user enables A/B Hold, the system MUST coordinate across bot and runner processes so an in-flight ordinary structural update can stop before applying structural changes, with a safe continuation signal that setup may proceed.

#### Scenario: Concurrent structural update stops safely before apply
- **GIVEN** an ordinary structural update for the campaign is in progress and has not yet applied structural writes
- **WHEN** the user enables A/B Hold for that campaign
- **THEN** the in-progress structural update stops without applying those structural writes
- **AND** the system reports that the stop is safe and enter setup may continue

### Requirement: EXIT restores ordinary target-place updates without restore
When A/B Hold is disabled, the system MUST leave the held keyword profile as-is without restoring a prior snapshot, and MUST allow automatic target-place updates and ordinary structural auto-update again.

#### Scenario: User disables A/B Hold
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** the user disables A/B Hold
- **THEN** automatic target-place updates are allowed again
- **AND** ordinary structural auto-update may run again
- **AND** the system does not restore a previous settings snapshot as part of exit

### Requirement: Excel exposes A/B Hold only for paid campaigns
Excel roundtrip MUST allow editing the A/B Hold mode setting only for campaigns with paid bot management active. For inactive paid bot management, Excel MUST NOT apply A/B Hold enable.

#### Scenario: Excel enable rejected when bot inactive
- **GIVEN** a campaign does not have paid bot management active
- **WHEN** an Excel import requests enabling A/B Hold for that campaign
- **THEN** A/B Hold is not enabled for that campaign

### Requirement: Enable is blocked when campaign stats freshness fails
The system MUST NOT enable A/B Hold (transition toward PENDING_SETUP) through UI, Excel, or other write paths when the campaign fails the same statistics freshness / retrieval health class used by shop-runner automation filtering (`_split_advs_by_stats_freshness` / not admitted to the fresh automation set). After the mode is already PENDING_SETUP or ACTIVE, setup and hold ticks MUST still be scheduled even if the campaign would be excluded from that fresh set; post-enter stats failures MUST NOT leave the campaign stuck without a setup tick solely due to the freshness filter.

#### Scenario: Enable rejected when stats are not fresh
- **GIVEN** a campaign has paid bot management active
- **AND** the campaign fails the stats freshness / retrieval health check used for automation filtering
- **WHEN** the user attempts to enable A/B Hold
- **THEN** A/B Hold is not enabled
- **AND** the campaign mode remains off

#### Scenario: Enable shows reason, restriction, and support link
- **GIVEN** enable is blocked because of stats freshness / retrieval problems
- **WHEN** the user attempts to enable A/B Hold from the paid UI
- **THEN** the user immediately sees the blocking reason
- **AND** sees that enabling the test is restricted for this campaign
- **AND** sees a recommendation to contact support / admin including the URL from `app.client_bot.const.SUPPORT_LINK`
- **AND** the message does not silently fail without explanation

#### Scenario: Setup still runs after enter when stats become stale
- **GIVEN** a campaign is already in PENDING_SETUP
- **AND** the campaign would currently be excluded from the fresh automation set
- **WHEN** shop-runner schedules A/B Hold automation
- **THEN** the A/B Hold setup path is still eligible to run for that campaign
- **AND** the campaign is not left without a setup tick solely because of the freshness filter

#### Scenario: Hold still runs when stats are stale
- **GIVEN** a campaign is already in active A/B Hold
- **AND** the campaign would currently be excluded from the fresh automation set
- **WHEN** shop-runner schedules A/B Hold automation
- **THEN** the A/B Hold hold path remains eligible to run for that campaign

### Requirement: Excel enable respects stats freshness gate
Excel roundtrip MUST NOT apply A/B Hold enable when the campaign fails the stats freshness / retrieval health check. Excel MAY omit the detailed Telegram alert copy, but MUST NOT enable the mode.

#### Scenario: Excel enable rejected when stats freshness fails
- **GIVEN** a campaign has paid bot management active
- **AND** the campaign fails the stats freshness / retrieval health check
- **WHEN** an Excel import requests enabling A/B Hold for that campaign
- **THEN** A/B Hold is not enabled for that campaign
