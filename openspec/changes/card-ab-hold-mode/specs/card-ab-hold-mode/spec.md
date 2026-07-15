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
- **THEN** the system shows the mode instruction and disable/back controls
- **AND** the Enable control is shown when mode is `OFF` (and MAY be hidden when mode is already `PENDING_SETUP` or `ACTIVE`)

### Requirement: A/B Hold screen includes instruction and controls
The system MUST provide a dedicated A/B Hold screen with instruction text, a control to disable the mode, and a control to return to the campaign menu. The Enable control MUST be available when mode is `OFF` and the user is allowed to start ENTER. When mode is already `PENDING_SETUP` or `ACTIVE`, the UI MAY hide the Enable control (Disable and Back MUST remain). If Enable is still shown while mode is `PENDING_SETUP` or `ACTIVE`, pressing it MUST remain idempotent per the Telegram Enable idempotent requirement. The instruction MUST warn that before enable the campaign SHOULD have warm-up traffic under a non-squeezed max CPO and a sufficient sales plan, that shelf mode is recommended off (user choice if shelves are required for traffic), and that price SHOULD NOT be changed during the test. The instruction MUST also state that during A/B Hold the campaign's set of ad phrases is fixed (new phrases are automatically excluded and manual changes in the Wildberries cabinet MAY be restored by the bot to the fixed set), and that to change the phrase set the user MUST disable A/B Hold. The instruction MUST NOT claim a complete freeze of all phrases regardless of campaign type; where the phrase surface cannot be fully controlled within the WB minus cap, the wording MUST remain scoped/best-effort.

#### Scenario: User opens instruction screen while OFF
- **GIVEN** a campaign has paid bot management active
- **AND** the campaign mode is `OFF`
- **WHEN** the user opens the A/B Hold screen
- **THEN** the instruction text is visible
- **AND** Enable, Disable, and Back controls are available
- **AND** the instruction states that the campaign's set of ad phrases is fixed during A/B Hold (new phrases are automatically excluded)
- **AND** the instruction states that manual WB cabinet phrase changes MAY be restored by the bot to the fixed set
- **AND** the instruction states that changing the phrase set requires disabling A/B Hold
- **AND** the instruction does not claim a full freeze of all phrases irrespective of campaign type / WB minus cap

#### Scenario: User opens instruction screen while ACTIVE or PENDING_SETUP
- **GIVEN** a campaign has paid bot management active
- **AND** the campaign mode is `PENDING_SETUP` or `ACTIVE`
- **WHEN** the user opens the A/B Hold screen
- **THEN** the instruction text is visible
- **AND** Disable and Back controls are available
- **AND** the Enable control MAY be hidden
- **AND** if Enable is shown, pressing it does not demote mode or re-signal ENTER

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
While A/B Hold is active after setup, the system MUST NOT update keyword target places automatically, MUST keep the bidder running so bids follow the fixed target places, and MUST NOT perform structural whitelist expansion/trimming, keyword enable/rollout growth, or ordinary minus-phrase recalculation. Overspend protection relative to plan max CPO MAY still turn expensive keywords OFF. "Keeping the bidder running" means the bidder path MUST remain eligible during hold and the freeze MUST NOT be implemented by stopping the bidder or the whole campaign; it does NOT forbid the orthogonal campaign activity-control watchdog (ordinary auto-budget / schedule start-pause) from starting or pausing the campaign for reversible operational reasons (daily budget/spend limit, cabinet balance, time schedule, rec_system mode), because those actions do not change the frozen allowed-set, target places, whitelist, keyword enable, or minus set.

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

#### Scenario: Orthogonal activity control may still start or pause the campaign
- **GIVEN** a campaign is in active A/B Hold with campaign activity control enabled (auto_budget_watchdog)
- **AND** an orthogonal, reversible operational condition applies (daily budget/spend limit, cabinet balance, time schedule, or rec_system mode)
- **WHEN** the ordinary campaign activity-control watchdog runs during hold
- **THEN** it MAY start or pause the campaign for that operational reason
- **AND** this is not a structural-freeze violation, because it does not mutate the frozen allowed-set, target places, whitelist, keyword enable, or minus set
- **AND** the campaign returns to the same frozen state when the operational condition clears
- **AND** this activity-control path MUST NOT be extended to mutate any frozen entity

### Requirement: ENTER setup freezes the allowed phrase set via PG snapshot before ACTIVE
The frozen unit of A/B Hold is the campaign's allowed (relevant) phrase set — the relevant phrases plus the resulting GOOD/whitelisted keyword profile — NOT the minus-phrase list. The minus list is only the derived enforcement mechanism that keeps non-allowed phrases out. When A/B Hold enter setup runs, the system MUST capture the allowed phrase set and persist it as a durable PostgreSQL snapshot on the campaign (new migration field), MUST bring Wildberries to that state with one setup sync/mutation (excluding, within the WB minus cap, phrases outside the allowed set — not an ordinary recalculation loop), and MUST NOT mark setup complete or transition the mode to ACTIVE until that allowed-set snapshot write succeeds together with the rest of setup. Redis MUST NOT be the source of truth for the allowed-set snapshot.

#### Scenario: Setup completes only after allowed-set snapshot
- **GIVEN** a campaign is in PENDING_SETUP
- **WHEN** A/B Hold enter setup runs successfully
- **THEN** the allowed (relevant) phrase set is captured and stored as a PostgreSQL snapshot for the campaign
- **AND** Wildberries is brought to that state once (phrases outside the allowed set excluded within the WB minus cap)
- **AND** the mode transitions to ACTIVE only after the snapshot and the rest of setup succeed

#### Scenario: Setup does not become ACTIVE without allowed-set snapshot
- **GIVEN** a campaign is in PENDING_SETUP
- **AND** allowed-set capture or PostgreSQL snapshot persistence fails
- **WHEN** A/B Hold enter setup attempts to finish
- **THEN** the mode does not transition to ACTIVE as a completed setup
- **AND** the UI does not report that A/B tests may start

### Requirement: HOLD enforces the frozen allowed phrase set (excludes new/non-allowed phrases)
While a campaign is preparing or holding for A/B Hold (PENDING_SETUP or ACTIVE), the system MUST NOT run ordinary minus-phrase auto-update recalculation (recomputing GOOD/BAD from fresh stats and changing the allowed set). Separately and independently, hold protection MUST keep the campaign's effective spend surface equal to the frozen allowed-set snapshot: any new or non-allowed phrase that appears after ENTER MUST be excluded (minus as enforcement), and any allowed phrase that was manually removed MUST be restored. Manual edits by the user in the bot or Wildberries cabinet are freeze violations and MUST be overwritten. The derived minus enforcement is bounded by the WB minus cap; if enforcing the frozen allowed set would exceed that cap (or the campaign type has open matching whose controllability is not proven), the system MUST degrade visibly (log + honest status) and MUST NOT silently claim a clean hold.

#### Scenario: Ordinary minus recalculation is skipped during hold
- **GIVEN** a campaign is in PENDING_SETUP or ACTIVE A/B Hold
- **WHEN** ordinary minus-phrase auto-update would recalculate the set and change the allowed set
- **THEN** that ordinary recalculation path does not apply a new calculated allowed/minus set for that campaign

#### Scenario: New non-allowed phrase during hold is excluded
- **GIVEN** a campaign is in ACTIVE A/B Hold with a stored allowed-set snapshot
- **AND** a new phrase outside the frozen allowed set starts matching/spending after ENTER
- **WHEN** A/B Hold hold protection runs
- **THEN** the new non-allowed phrase is excluded (minused) so the spend surface stays equal to the frozen allowed set
- **AND** this enforcement is hold protection, not an ordinary recalculation of the allowed set

#### Scenario: Manually removed allowed phrase is restored
- **GIVEN** a campaign is in ACTIVE A/B Hold with a stored allowed-set snapshot
- **AND** an allowed phrase from the snapshot was manually excluded in the Wildberries cabinet
- **WHEN** A/B Hold hold protection runs
- **THEN** the system restores that allowed phrase so the frozen allowed set is preserved

#### Scenario: Manual bot minus update does not report success during freeze
- **GIVEN** a campaign is in PENDING_SETUP or ACTIVE A/B Hold
- **WHEN** the user triggers the bot action to refresh/update minus phrases
  («Обновить минус-слова» / ordinary `update_minus_phrases` without setup force)
- **THEN** the ordinary path does not apply a new recalculated set to Wildberries
- **AND** the UI does not report that minus phrases were successfully updated
- **AND** the UI informs the user that the phrase set is fixed and that
  changing it requires disabling A/B Hold

#### Scenario: Enforcement exceeding the WB minus cap degrades visibly
- **GIVEN** a campaign is in ACTIVE A/B Hold
- **AND** keeping only the frozen allowed set would require more excluded phrases than the WB minus cap allows (or the campaign type is open-match without proven controllability)
- **WHEN** A/B Hold hold protection runs
- **THEN** the system logs the degradation and reports an honest status that the hold cannot guarantee a clean surface for that campaign
- **AND** the system does not silently claim a clean or complete freeze

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
While a campaign is preparing or holding for A/B Hold, the system MUST NOT run ordinary structural campaign auto-update that changes whitelist membership, target places, keyword enable/rollout, or ordinary minus-phrase recalculation outside the A/B Hold setup and hold protection paths (including allowed-set enforcement that excludes non-allowed phrases). A/B Hold applies only to campaigns on the V3 auto-updater; the V2-era campaign strategy objective auto-switch (MIN_CPO ↔ MAX_CONV, the `change_adv_strategy` path) is NOT part of this structural freeze and MUST NOT get a separate A/B Hold freeze gate — it is instead governed by the A/B-Hold-requires-V3 requirement below, and the held V3 profile MUST NOT be driven by that campaign-level strategy objective.

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
When A/B Hold is disabled, the system MUST leave the held keyword profile as-is without restoring a prior keyword-settings snapshot, MUST allow automatic target-place updates and ordinary structural auto-update again, MUST allow ordinary minus-phrase auto-update and allowed-set recalculation again, and MUST clear or archive the PostgreSQL allowed-set snapshot for the campaign.

#### Scenario: User disables A/B Hold
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** the user disables A/B Hold
- **THEN** automatic target-place updates are allowed again
- **AND** ordinary structural auto-update may run again
- **AND** ordinary minus-phrase auto-update and allowed-set recalculation may run again
- **AND** the PostgreSQL allowed-set snapshot is cleared or archived
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

### Requirement: Telegram Enable is idempotent while preparing or holding
When the campaign mode is already `PENDING_SETUP` or `ACTIVE`, the paid Telegram Enable action — if reachable (button shown or callback still invoked) — MUST be a no-op for mode and ENTER signaling: it MUST NOT demote the mode back to `PENDING_SETUP`, MUST NOT write a new Redis ENTER signal, and MUST NOT cause a re-run of ENTER `force_ab_hold_setup_sync` / allowed-set setup sync solely from that Enable press. The UI MAY hide Enable in these modes; hiding is optional sugar and MUST NOT replace the handler no-op (stale callback / keyboard race). EXIT (Telegram disable → `OFF` + clear allowed-set snapshot) remains the only in-MVP path back to `OFF` before a new ENTER is allowed. Shop-runner may still continue an in-flight setup while mode stays `PENDING_SETUP` (single-flight lock); that is not a re-ENTER from Enable.

#### Scenario: Enable while ACTIVE does not re-enter
- **GIVEN** a campaign is in `ACTIVE` A/B Hold with a stored allowed-set snapshot
- **WHEN** the user presses Enable on the A/B Hold screen
- **THEN** the campaign mode remains `ACTIVE`
- **AND** Redis ENTER is not written for that press
- **AND** ENTER setup force allowed-set sync is not re-triggered by that press

#### Scenario: Enable while PENDING_SETUP does not restart ENTER
- **GIVEN** a campaign is in `PENDING_SETUP`
- **WHEN** the user presses Enable again
- **THEN** the campaign mode remains `PENDING_SETUP`
- **AND** Redis ENTER is not rewritten solely to restart ENTER from that press
- **AND** the UI does not treat the press as a fresh enable from `OFF`

#### Scenario: Enable from OFF still starts ENTER
- **GIVEN** a campaign is in `OFF` with paid bot management active and stats freshness gate passing
- **WHEN** the user presses Enable
- **THEN** the campaign mode becomes `PENDING_SETUP`
- **AND** Redis ENTER MAY be written
- **AND** shop-runner setup MAY run the one-time ENTER allowed-set capture → snapshot → `ACTIVE` path

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

### Requirement: Enable warns when candidate test keywords have too few recent impressions
When the user attempts to enable A/B Hold from the paid UI and the stats freshness gate passes, the system MUST evaluate the aggregate recent impressions (last-24h window from the same campaign statistics source used for keyword cards) of the keywords that would carry the test. If that aggregate is below the minimum recent-impressions threshold, the system MUST NOT enable silently: it MUST show the reason (too few recent impressions for a reliable A/B test), recommend increasing the plan max CPO and retrying, and present an explicit choice to launch anyway or cancel. The mode MUST remain `OFF` until the user chooses. Choosing launch-anyway proceeds to `PENDING_SETUP` (ENTER). Choosing cancel leaves the mode `OFF` without signaling ENTER. This is a soft warning gate (the user MAY proceed at their own risk), distinct from the stats-freshness hard block and from the empty allowed-set non-ready rule. When the aggregate meets or exceeds the threshold, enable proceeds without this warning.

#### Scenario: Low recent impressions warns with a choice
- **GIVEN** a campaign has paid bot management active, passes the stats freshness gate, and mode is `OFF`
- **AND** the aggregate recent impressions (last 24h) of the candidate test keywords are below the minimum threshold
- **WHEN** the user presses Enable
- **THEN** the campaign mode is not changed yet (stays `OFF`)
- **AND** the user sees the reason (too few recent impressions), a recommendation to raise the plan max CPO and try again, and an explicit choice to launch anyway or cancel

#### Scenario: Launch anyway proceeds to setup
- **GIVEN** the low recent-impressions warning is shown
- **WHEN** the user chooses launch anyway
- **THEN** the campaign mode becomes `PENDING_SETUP`
- **AND** the ENTER setup path may run despite the low-impressions warning

#### Scenario: Cancel keeps the campaign OFF
- **GIVEN** the low recent-impressions warning is shown
- **WHEN** the user chooses cancel
- **THEN** the campaign mode remains `OFF`
- **AND** ENTER is not signaled

#### Scenario: Sufficient recent impressions enable without warning
- **GIVEN** the aggregate recent impressions (last 24h) of the candidate test keywords meet or exceed the minimum threshold
- **WHEN** the user presses Enable
- **THEN** the low recent-impressions warning is not shown
- **AND** enable proceeds per the normal enable path

### Requirement: Enable is blocked when plan max CPO is missing or non-positive
A/B Hold ENTER setup classifies keywords against the campaign plan max CPO; without a positive plan max CPO the setup tick deterministically cannot progress and would leave the campaign in PENDING_SETUP indefinitely while excluded from ordinary automation. The system MUST NOT enable A/B Hold (transition toward PENDING_SETUP) through the paid Telegram UI when the campaign plan `max_price_for_order` is missing or less than or equal to zero. The mode MUST remain `OFF`, and the user MUST see the reason (a positive plan max CPO is required) and a recommendation to set it and retry. This is a hard gate evaluated together with the stats-freshness and V3-only gates, before the low-recent-impressions soft warning.

#### Scenario: Enable blocked when plan max CPO is missing or non-positive
- **GIVEN** a campaign has paid bot management active, is on V3, and passes the stats freshness gate
- **AND** the campaign plan max CPO (`max_price_for_order`) is missing or is less than or equal to zero
- **WHEN** the user attempts to enable A/B Hold from the paid UI
- **THEN** A/B Hold is not enabled
- **AND** the campaign mode remains `OFF`
- **AND** the user sees that a positive plan max CPO is required and is recommended to set it and retry

#### Scenario: Enable proceeds when plan max CPO is positive
- **GIVEN** a campaign has paid bot management active, is on V3, passes the stats freshness gate, and mode is `OFF`
- **AND** the campaign plan max CPO is greater than zero
- **WHEN** the user presses Enable
- **THEN** the plan-max-CPO gate does not block enable
- **AND** enable proceeds per the normal enable path (subject to the low-recent-impressions soft warning)

### Requirement: PENDING_SETUP setup blockers are surfaced and recoverable
While a campaign is in PENDING_SETUP it is excluded from ordinary structural automation, so the system MUST NOT leave it in a silent, indefinite semi-frozen state when setup cannot make progress. When A/B Hold enter setup cannot complete for a deterministic reason detectable only at the setup tick (for example an empty allowed-set / no non-BAD keyword surface, or a plan max CPO that became missing or non-positive after enable), the UI status MUST surface the specific blocking reason and the recommended action (raise plan max CPO, no eligible keywords, or disable A/B Hold), rather than only a generic "preparing" message. Transient reasons (setup lock contention, a single stale tick, keyword-cache warmup) MAY keep a generic preparing status. The user MUST always be able to recover: EXIT (disable → `OFF`) MUST remain available while PENDING_SETUP, returning the campaign to ordinary automation. An owned automatic abort of a stuck PENDING_SETUP to `OFF` is out of MVP scope; the MVP guarantee is a visible actionable reason plus an always-available EXIT.

#### Scenario: Deterministic setup block shows an actionable reason
- **GIVEN** a campaign is in PENDING_SETUP
- **AND** setup cannot progress for a deterministic reason (for example the allowed-set is empty / no eligible keywords, or the plan max CPO is missing or non-positive)
- **WHEN** the UI reports mode status
- **THEN** the status states the specific blocking reason and the recommended action
- **AND** the status does not present the campaign as ready-to-test

#### Scenario: Transient setup delay may stay generic
- **GIVEN** a campaign is in PENDING_SETUP
- **AND** setup has not completed only for a transient reason (setup lock contention, a single stale tick, or keyword-cache warmup)
- **WHEN** the UI reports mode status
- **THEN** a generic preparing status is acceptable
- **AND** the next setup tick retries setup

#### Scenario: EXIT recovers a stuck PENDING_SETUP
- **GIVEN** a campaign is in PENDING_SETUP and setup is blocked
- **WHEN** the user disables A/B Hold (EXIT)
- **THEN** the campaign mode becomes `OFF`
- **AND** ordinary automation is eligible again for that campaign

### Requirement: ACTIVE without ENTER setup snapshot is forbidden
The system MUST NOT transition a campaign to ACTIVE A/B Hold except via successful `process_ab_setup` / setup apply that includes allowed-set capture and PostgreSQL snapshot persistence (decision §8). Direct writes of `active` (including Excel or other non-setup paths) MUST NOT create a held campaign.

#### Scenario: Non-setup ACTIVE write is rejected or ignored
- **GIVEN** a write path other than A/B Hold ENTER setup attempts to set mode to active
- **WHEN** that write is processed
- **THEN** the campaign does not become ACTIVE without the ENTER minus snapshot
- **AND** hold enforcement does not treat an empty/missing allowed-set snapshot as a successful freeze

### Requirement: A/B Hold requires the V3 auto-updater and is mutually exclusive with V2
A/B Hold is a V3 auto-updater feature. The system MUST allow enabling A/B Hold only for a campaign whose auto-updater version is V3. When the user attempts to enable A/B Hold from the paid Telegram UI for a campaign that is not on V3, the system MUST NOT transition the mode toward `PENDING_SETUP`: the mode MUST remain `OFF` and the user MUST see that A/B Hold requires the V3 auto-updater. While a campaign is `PENDING_SETUP` or `ACTIVE`, the system MUST NOT switch its auto-updater version to V2; switching to V2 MUST be blocked until A/B Hold is disabled (EXIT → `OFF`). Because A/B Hold runs only on V3 campaigns, the V2-era campaign strategy objective auto-switch (MIN_CPO ↔ MAX_CONV) is out of A/B Hold scope: it MUST NOT change the held V3 campaign's frozen keyword bidding profile, and no separate A/B Hold freeze gate is added on that V2 strategy path.

#### Scenario: Enable blocked when campaign is not on V3
- **GIVEN** a campaign has paid bot management active and passes the stats freshness gate
- **AND** the campaign auto-updater version is not V3
- **WHEN** the user attempts to enable A/B Hold from the paid UI
- **THEN** A/B Hold is not enabled
- **AND** the campaign mode remains `OFF`
- **AND** the user is told that A/B Hold requires the V3 auto-updater

#### Scenario: Enable proceeds on a V3 campaign
- **GIVEN** a campaign has paid bot management active, passes the stats freshness gate, and is on the V3 auto-updater
- **AND** the campaign mode is `OFF`
- **WHEN** the user presses Enable
- **THEN** the campaign mode becomes `PENDING_SETUP`
- **AND** ENTER MAY proceed per the normal enable path

#### Scenario: Version downgrade to V2 blocked during A/B Hold
- **GIVEN** a campaign is in `PENDING_SETUP` or `ACTIVE` A/B Hold
- **WHEN** the user attempts to switch the campaign auto-updater version to V2
- **THEN** the auto-updater version is not changed
- **AND** the user is told to disable A/B Hold before switching to V2

#### Scenario: Version downgrade to V2 allowed after EXIT
- **GIVEN** a campaign has A/B Hold disabled (mode `OFF`)
- **WHEN** the user switches the campaign auto-updater version to V2
- **THEN** the auto-updater version change is applied

#### Scenario: Campaign strategy auto-switch does not affect the held V3 profile
- **GIVEN** a campaign is in `ACTIVE` A/B Hold on the V3 auto-updater
- **WHEN** the automatic campaign strategy objective would change between MIN_CPO and MAX_CONV
- **THEN** the held campaign's frozen keyword bidding profile is not changed by that campaign strategy switch

### Requirement: Shared defaults MUST NOT disable or mutate A/B Hold on a held campaign
The shared campaign-defaults application path — the "Применить дефолты" / "apply defaults" actions (single campaign and shop-wide) and the shared `apply_defaults_to_adv_setting` helper — is NOT an A/B Hold enable/disable path. When a campaign's mode is `PENDING_SETUP` or `ACTIVE`, this path MUST NOT change `card_ab_hold_mode` (MUST NOT force it to `off`), MUST NOT clear or leave the allowed-set snapshot stale, and MUST NOT reset the A/B-Hold-coupled structural fields (auto-updater version, whitelist/target-place automation, bidder profile) in a way that breaks the freeze or the V3-only invariant. Disabling A/B Hold remains available only through the owned paid Telegram EXIT path (mode → `off` + clear allowed-set snapshot), the single enable/disable write path in MVP. When a campaign's mode is `OFF`, applying defaults proceeds normally.

#### Scenario: Apply defaults on a held campaign preserves A/B Hold
- **GIVEN** a campaign is in `PENDING_SETUP` or `ACTIVE` A/B Hold with a stored allowed-set snapshot
- **WHEN** the user triggers "apply defaults" for that single campaign
- **THEN** the campaign mode is not changed to `off` by this path
- **AND** the allowed-set snapshot is not cleared or left stale by this path
- **AND** the A/B-Hold-coupled structural fields are not reset in a way that breaks the freeze or the V3-only requirement
- **AND** disabling A/B Hold remains available only via the owned paid Telegram EXIT

#### Scenario: Shop-wide apply defaults does not disable held campaigns
- **GIVEN** a shop has a mix of campaigns, some in `PENDING_SETUP`/`ACTIVE` A/B Hold and some `OFF`
- **WHEN** the user triggers shop-wide "apply defaults"
- **THEN** the held campaigns are not switched to `off` and their allowed-set snapshots are not cleared or left stale by this path
- **AND** the `OFF` campaigns still receive the defaults

#### Scenario: Apply defaults on an OFF campaign applies normally
- **GIVEN** a campaign has A/B Hold mode `OFF`
- **WHEN** the user triggers "apply defaults"
- **THEN** the campaign defaults are applied as usual
- **AND** the A/B Hold mode remains `OFF`
