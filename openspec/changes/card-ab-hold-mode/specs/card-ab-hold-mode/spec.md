## ADDED Requirements

### Requirement: A/B Hold is paid-only
The system MUST expose and enable the card A/B Hold mode only for campaigns with paid bot management active, and only through the paid Telegram UI enable/disable path in MVP. When paid bot management is inactive, the A/B Hold entry MUST be hidden and enable MUST NOT be executed. Excel roundtrip MUST NOT be an enable, disable, or edit path for A/B Hold mode in MVP.

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
The system MUST provide a dedicated A/B Hold screen with instruction text and controls to enable the mode, disable the mode, and return to the campaign menu. The instruction MUST warn that before enable the campaign SHOULD have warm-up traffic under a non-squeezed max CPO and a sufficient sales plan, that shelf mode is recommended off (user choice if shelves are required for traffic), and that price SHOULD NOT be changed during the test. The instruction MUST also state that during A/B Hold minus phrases are fixed, that manual changes in the Wildberries cabinet MAY be restored by the bot to the fixed snapshot, and that to change minus phrases the user MUST disable A/B Hold.

#### Scenario: User opens instruction screen
- **GIVEN** a campaign has paid bot management active
- **WHEN** the user opens the A/B Hold screen
- **THEN** the instruction text is visible
- **AND** enable, disable, and back controls are available
- **AND** the instruction states that minus phrases are fixed during A/B Hold
- **AND** the instruction states that manual WB cabinet changes to minus phrases MAY be restored by the bot
- **AND** the instruction states that changing minus phrases requires disabling A/B Hold

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
While A/B Hold is active after setup, the system MUST NOT update keyword target places automatically, MUST keep the bidder running so bids follow the fixed target places, and MUST NOT perform structural whitelist expansion/trimming, keyword enable/rollout growth, or ordinary minus-phrase recalculation. Overspend protection relative to plan max CPO MAY still turn expensive keywords OFF.

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

### Requirement: ENTER setup freezes minus phrases via PG snapshot before ACTIVE
When A/B Hold enter setup runs, the system MUST bring minus phrases to an up-to-date state with one setup sync/mutation (not an ordinary recalculation loop), MUST persist that set as a durable PostgreSQL snapshot on the campaign (new migration field), and MUST NOT mark setup complete or transition the mode to ACTIVE until that snapshot write succeeds together with the rest of setup. Redis MUST NOT be the source of truth for the minus-phrase snapshot.

#### Scenario: Setup completes only after minus sync and snapshot
- **GIVEN** a campaign is in PENDING_SETUP
- **WHEN** A/B Hold enter setup runs successfully
- **THEN** minus phrases are brought to an up-to-date state once
- **AND** that set is stored as a PostgreSQL snapshot for the campaign
- **AND** the mode transitions to ACTIVE only after the snapshot and the rest of setup succeed

#### Scenario: Setup does not become ACTIVE without minus snapshot
- **GIVEN** a campaign is in PENDING_SETUP
- **AND** minus-phrase sync or PostgreSQL snapshot persistence fails
- **WHEN** A/B Hold enter setup attempts to finish
- **THEN** the mode does not transition to ACTIVE as a completed setup
- **AND** the UI does not report that A/B tests may start

### Requirement: HOLD restores minus-phrase snapshot on drift
While a campaign is preparing or holding for A/B Hold (PENDING_SETUP or ACTIVE), the system MUST NOT run ordinary minus-phrase auto-update recalculation. If current minus phrases differ from the stored PostgreSQL snapshot, the system MUST restore the snapshot to Wildberries. Manual minus-phrase edits by the user in the bot or Wildberries cabinet are freeze violations and MUST be overwritten by restore.

#### Scenario: Ordinary minus recalculation is skipped during hold
- **GIVEN** a campaign is in PENDING_SETUP or ACTIVE A/B Hold
- **WHEN** ordinary minus-phrase auto-update would recalculate the set
- **THEN** that ordinary recalculation path does not apply a new calculated set for that campaign

#### Scenario: Drift from snapshot is restored
- **GIVEN** a campaign is in ACTIVE A/B Hold with a stored minus-phrase snapshot
- **AND** current Wildberries minus phrases differ from that snapshot
- **WHEN** A/B Hold minus-phrase freeze protection runs
- **THEN** the system restores the snapshot minus phrases to Wildberries

### Requirement: UI reports A/B ready only after ACTIVE setup
The system MUST NOT tell the user that A/B Hold is enabled and that A/B tests may start until the campaign mode is ACTIVE after successful full setup (including minus-phrase sync and PostgreSQL snapshot). A PENDING_SETUP or “request accepted” state alone MUST NOT be presented as ready-to-test. Cross-pod interrupt and setup lock MUST prevent a ready UI response while setup is incomplete or aborted.

#### Scenario: Ready message waits for ACTIVE
- **GIVEN** the user enables A/B Hold and setup is still PENDING_SETUP
- **WHEN** the UI reports mode status
- **THEN** the UI does not state that A/B tests may start
- **AND** the ready-to-test message appears only after the mode becomes ACTIVE

#### Scenario: Interrupted setup never shows ready
- **GIVEN** enter setup is interrupted or fails before ACTIVE
- **WHEN** the UI reports mode status
- **THEN** the UI does not state that the mode is fully enabled for starting A/B tests

### Requirement: Ordinary structural auto-update is suspended during A/B Hold preparation and hold
While a campaign is preparing or holding for A/B Hold, the system MUST NOT run ordinary structural campaign auto-update that changes whitelist membership, target places, keyword enable/rollout, or ordinary minus-phrase recalculation outside the A/B Hold setup and hold protection paths (including minus-phrase snapshot restore).

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

### Requirement: EXIT restores ordinary target-place and minus updates without profile restore
When A/B Hold is disabled, the system MUST leave the held keyword profile as-is without restoring a prior keyword-settings snapshot, MUST allow automatic target-place updates and ordinary structural auto-update again, MUST allow ordinary minus-phrase auto-update again, and MUST clear or archive the PostgreSQL minus-phrase snapshot for the campaign.

#### Scenario: User disables A/B Hold
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** the user disables A/B Hold
- **THEN** automatic target-place updates are allowed again
- **AND** ordinary structural auto-update may run again
- **AND** ordinary minus-phrase auto-update may run again
- **AND** the PostgreSQL minus-phrase snapshot is cleared or archived
- **AND** the system does not restore a previous keyword-settings snapshot as part of exit

### Requirement: Excel MUST NOT expose or apply A/B Hold mode
Excel roundtrip MUST NOT export, import, or apply the A/B Hold mode setting (`card_ab_hold_mode`) in MVP. The Excel schema MUST NOT include an A/B Hold edit column. If an import payload still contains `card_ab_hold_mode` (including `off`, `pending_setup`, or `active`), the system MUST ignore it and MUST NOT change the campaign mode. Excel enable/edit of A/B Hold is deferred to a future change.

#### Scenario: Excel import of active does not change mode
- **GIVEN** a campaign has any current A/B Hold mode
- **WHEN** an Excel import requests `card_ab_hold_mode=active`
- **THEN** the campaign mode is left unchanged
- **AND** no ACTIVE transition without setup snapshot is performed

#### Scenario: Excel import of pending_setup does not enable
- **GIVEN** a campaign is off
- **WHEN** an Excel import requests `card_ab_hold_mode=pending_setup`
- **THEN** A/B Hold is not enabled
- **AND** the campaign mode remains off

#### Scenario: Excel import of off does not disable via Excel
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** an Excel import requests `card_ab_hold_mode=off`
- **THEN** the campaign mode is left unchanged by Excel apply
- **AND** EXIT remains available only via the paid Telegram disable path in MVP

### Requirement: Enable is blocked when campaign stats freshness fails
The system MUST NOT enable A/B Hold (transition toward PENDING_SETUP) through the paid Telegram UI (or any other in-MVP enable write path) when the campaign fails the same statistics freshness / retrieval health class used by shop-runner automation filtering (`_split_advs_by_stats_freshness` / not admitted to the fresh automation set). Excel is not an enable path in MVP. After the mode is already PENDING_SETUP or ACTIVE, setup and hold ticks MUST still be scheduled even if the campaign would be excluded from that fresh set; post-enter stats failures MUST NOT leave the campaign stuck without a setup tick solely due to the freshness filter.

#### Scenario: Enable rejected when stats are not fresh
- **GIVEN** a campaign has paid bot management active
- **AND** the campaign fails the stats freshness / retrieval health check used for automation filtering
- **WHEN** the user attempts to enable A/B Hold from the paid UI
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

### Requirement: ACTIVE without ENTER setup snapshot is forbidden
The system MUST NOT transition a campaign to ACTIVE A/B Hold except via successful `process_ab_setup` / setup apply that includes minus-phrase sync and PostgreSQL snapshot persistence (decision §8). Direct writes of `active` (including Excel or other non-setup paths) MUST NOT create a held campaign.

#### Scenario: Non-setup ACTIVE write is rejected or ignored
- **GIVEN** a write path other than A/B Hold ENTER setup attempts to set mode to active
- **WHEN** that write is processed
- **THEN** the campaign does not become ACTIVE without the ENTER minus snapshot
- **AND** ordinary hold restore does not treat an empty/missing snapshot as a successful freeze
