## Purpose

Paid-only Telegram A/B Hold mode for card creative tests: confirm keywords,
durable WARM_UP, confirm target places / Auto participation / Auto bid, then
ACTIVE hold with structural freeze while the bidder continues toward confirmed
targets. Broad enablement remains gated behind OD-05.

## Requirements

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

### Requirement: HOLD freezes target places and keeps bidder running
While A/B Hold is active after setup, the system MUST NOT update keyword target places automatically, MUST keep the bidder running so bids follow the fixed target places, and MUST NOT perform structural whitelist expansion/trimming, keyword enable/rollout growth, or ordinary minus-phrase recalculation. The system MUST NOT run the continuous ordinary Search common-bid updater (`update_common_bid_in_search_adv`) for that campaign while mode is `PENDING_SETUP` or `ACTIVE`; Search common bid is reset to WB minimum on ENTER by the owned path (see ENTER resets Search common bid requirement) and then left frozen. Overspend protection relative to plan max CPO MAY still turn expensive keywords OFF. "Keeping the bidder running" means the bidder / cluster-bids path MUST remain eligible during hold and the freeze MUST NOT be implemented by stopping the bidder or the whole campaign; it does NOT forbid the orthogonal campaign activity-control watchdog (ordinary auto-budget / schedule start-pause) from starting or pausing the campaign for reversible operational reasons (daily budget/spend limit, cabinet balance, time schedule, rec_system mode), because those actions do not change the frozen allowed-set, target places, whitelist, keyword enable, minus set, or the frozen Search common bid.

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
- **AND** this is not a structural-freeze violation, because it does not mutate the frozen allowed-set, target places, whitelist, keyword enable, minus set, or frozen Search common bid
- **AND** the campaign returns to the same frozen state when the operational condition clears
- **AND** this activity-control path MUST NOT be extended to mutate any frozen entity

### Requirement: ENTER resets Search common bid to WB minimum then freezes it
Search common bid (the campaign Search auction common CPM written via Wildberries `SetCommonBids` / `update_search_adv_common_cpm`) is a working campaign mechanism: it affects cold / not-yet-visible keywords (including before the views threshold) and catalog bid behavior. It is NOT the keyword/cluster bidder path. When the user successfully enables A/B Hold (ENTER: mode transitions from `OFF` to `PENDING_SETUP` with Redis ENTER / setup start), an A/B Hold owned write-path MUST perform a one-shot reset of Search common bid for all campaign nmids to the Wildberries minimum (`search_adv_min_bids` or equivalent minimum SoT). After that reset, while mode is `PENDING_SETUP` or `ACTIVE`, the continuous ordinary Search common-bid updater (`CoroutinesManager.update_common_bid_in_search_adv` / `UpdateCommotBidInSearchAdvsManager`) MUST NOT change Search common bid for that campaign. The keyword/cluster bidder (`update_cluster_bids`) MUST remain allowed in `ACTIVE` to hold bids toward confirmed target places. A second owned common-bid reset MUST NOT run mid-hold; Enable while already `PENDING_SETUP` or `ACTIVE` remains a no-op (idempotent Enable requirement). Re-reset is allowed only after EXIT to `OFF` and a new ENTER. The continuous ordinary updater MUST NOT be the owner of the ENTER reset.

#### Scenario: ENTER resets Search common bid to minimum
- **GIVEN** a campaign mode is `OFF`
- **AND** its Search common bid is above the Wildberries minimum for at least one nmid
- **WHEN** the user successfully enables A/B Hold (ENTER → `PENDING_SETUP`)
- **THEN** an A/B Hold owned path sets Search common bid for the campaign nmids to the Wildberries minimum
- **AND** the continuous ordinary Search common-bid updater is not the owner of that write

#### Scenario: Ordinary Search common-bid updater skips held campaigns
- **GIVEN** a campaign mode is `PENDING_SETUP` or `ACTIVE`
- **WHEN** the ordinary Search common-bid updater tick runs
- **THEN** that updater does not change Search common bid for that campaign

#### Scenario: Bidder continues cluster bids in ACTIVE after common-bid freeze
- **GIVEN** a campaign is `ACTIVE` under A/B Hold
- **AND** Search common bid was reset to minimum on ENTER
- **WHEN** the keyword/cluster bidder tick runs
- **THEN** the bidder MAY update cluster/keyword bids toward confirmed target places
- **AND** Search common bid remains at the frozen minimum from the ENTER reset

#### Scenario: Mid-hold Enable does not re-reset Search common bid
- **GIVEN** a campaign mode is already `PENDING_SETUP` or `ACTIVE`
- **AND** Search common bid was already reset on ENTER
- **WHEN** the user presses Enable again
- **THEN** mode is unchanged
- **AND** Search common bid is not rewritten by a second owned reset

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
While a campaign is preparing or holding for A/B Hold, the system MUST NOT run ordinary structural campaign auto-update that changes whitelist membership, target places, keyword enable/rollout, ordinary minus-phrase recalculation, or continuous ordinary Search common-bid mutation outside the A/B Hold setup and hold protection paths (including allowed-set enforcement that excludes non-allowed phrases, and the owned ENTER Search common-bid reset-to-min). The keyword/cluster bidder path is not an ordinary structural auto-update under this requirement and remains governed by the HOLD freezes target places / bidder and ENTER resets Search common bid requirements. A/B Hold applies only to campaigns on the V3 auto-updater; the V2-era campaign strategy objective auto-switch (MIN_CPO ↔ MAX_CONV, the `change_adv_strategy` path) is NOT part of this structural freeze and MUST NOT get a separate A/B Hold freeze gate — it is instead governed by the A/B-Hold-requires-V3 requirement below, and the held V3 profile MUST NOT be driven by that campaign-level strategy objective.

#### Scenario: Ordinary auto-update skips structural work during hold
- **GIVEN** a campaign is preparing or holding for A/B Hold
- **WHEN** ordinary structural campaign auto-update would run
- **THEN** that ordinary structural path does not change the campaign's held profile
- **AND** the continuous ordinary Search common-bid updater does not change Search common bid for that campaign

### Requirement: Enter interrupts unsafe concurrent structural apply
When the user enables A/B Hold, the system MUST coordinate across bot and runner processes so an in-flight ordinary structural update can stop before applying structural changes, with a safe continuation signal that setup may proceed.

#### Scenario: Concurrent structural update stops safely before apply
- **GIVEN** an ordinary structural update for the campaign is in progress and has not yet applied structural writes
- **WHEN** the user enables A/B Hold for that campaign
- **THEN** the in-progress structural update stops without applying those structural writes
- **AND** the system reports that the stop is safe and enter setup may continue

### Requirement: EXIT restores ordinary target-place and minus updates without profile restore
When A/B Hold is disabled, EXIT MUST set mode to `OFF`, MUST clear the PostgreSQL allowed-set snapshot for the campaign, MUST clear coordination Redis state used for ENTER/EXIT/setup polling, MUST allow automatic target-place updates and ordinary structural auto-update again, MUST allow ordinary minus-phrase auto-update and allowed-set recalculation again, MUST allow the continuous ordinary Search common-bid updater again, and MUST leave the held keyword profile as-is without restoring a prior keyword-settings snapshot. The `card_ab_hold_degraded` flag may remain in `OFF` as non-operative residue; automatic cleanup of that residue is deferred and is not required for EXIT completion in MVP.

#### Scenario: User disables A/B Hold
- **GIVEN** a campaign is in active A/B Hold
- **WHEN** the user disables A/B Hold
- **THEN** the campaign mode becomes `OFF`
- **AND** automatic target-place updates are allowed again
- **AND** ordinary structural auto-update may run again
- **AND** the continuous ordinary Search common-bid updater may run again
- **AND** ordinary minus-phrase auto-update and allowed-set recalculation may run again
- **AND** the PostgreSQL allowed-set snapshot is cleared
- **AND** A/B Hold coordination Redis state is cleared
- **AND** the system does not restore a previous keyword-settings snapshot as part of exit
- **AND** `card_ab_hold_degraded` MAY remain set in `OFF` as non-operative residue

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

#### Scenario: Enable from OFF starts PENDING epoch path, not direct ACTIVE
- **GIVEN** a campaign is in `OFF` with paid bot management active and stats freshness gate passing
- **AND** the new epoch flow is authorized (feature flag / owner entry per `tasks.md` §25; `card_ab_hold_phase` not NULL legacy-MVP-1 semantics)
- **WHEN** the user presses Enable
- **THEN** the campaign mode becomes `PENDING_SETUP`
- **AND** Redis ENTER MAY be written
- **AND** the campaign enters the owner epoch path: keyword-set confirm → durable WARM_UP → TP confirm → Auto participation confirm → Auto bid confirm → durable PENDING intent → WB sync → `ACTIVE`
- **AND** shop-runner MUST NOT translate Enable into direct `ACTIVE` or one-shot legacy `process_ab_setup` → `ACTIVE` without completed confirms and durable PENDING intent (legacy one-shot path gated by `tasks.md` §18.4; `card_ab_hold_phase` NULL = legacy-MVP-1 until EXIT or controlled re-enter)

#### Scenario: Enable from OFF on legacy in-flight MVP-1 campaign keeps legacy semantics
- **GIVEN** a campaign was ACTIVE under legacy MVP-1 before epoch migration (`card_ab_hold_phase` NULL, allowed-set snapshot present)
- **WHEN** the user presses Enable while mode is already `ACTIVE` or `PENDING_SETUP`
- **THEN** existing idempotent Enable behavior applies (decision §10)
- **AND** the campaign MUST NOT auto-convert to epoch-managed generation without explicit EXIT and fail-closed feature-flagged re-enter (§18.5 / Migration Plan)

### Requirement: Manual Telegram target-place write is blocked during A/B Hold freeze
While the campaign mode is `PENDING_SETUP` or `ACTIVE`, manual Telegram input that writes `KeywordSetting.target_place` MUST be blocked before database write/commit. The handler MUST clear FSM state after blocked input and MUST send an explanatory message that target place changes are unavailable until A/B Hold is disabled. When mode is `OFF`, existing manual target-place behavior remains allowed.

#### Scenario: Manual target-place input is blocked in PENDING_SETUP or ACTIVE
- **GIVEN** a campaign mode is `PENDING_SETUP` or `ACTIVE`
- **WHEN** the user sends manual target-place value from Telegram
- **THEN** `KeywordSetting.target_place` is not written
- **AND** FSM state for that input flow is cleared
- **AND** the user receives an explanatory message about disabling A/B Hold first

#### Scenario: Manual target-place input remains allowed in OFF
- **GIVEN** a campaign mode is `OFF`
- **WHEN** the user sends manual target-place value from Telegram
- **THEN** existing manual target-place behavior is applied

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

### Requirement: Enable warns when campaign recent keyword impressions are too low
When the user attempts to enable A/B Hold from the paid UI and the stats freshness gate passes, the system MUST evaluate the aggregate recent keyword-cluster impressions of the campaign as a **campaign-level proxy** (sum over `adv_id` and paired `search_adv_id` via the same ClickHouse campaign keyword-stats path used for keyword cards — `get_keywords_views_by_days` / `mv_clusters_daily_agg`). The evaluation window MUST use the **calendar-day grain** of that daily aggregate covering the last-24h wall-clock interval (not true rolling hour buckets, and not a filter limited to setup non-BAD / would-carry-test keywords). If that measured aggregate is below the minimum recent-impressions threshold, the system MUST NOT enable silently: it MUST show the reason (too few recent impressions for a reliable A/B test), recommend increasing the plan max CPO and retrying, and present an explicit choice to launch anyway or cancel. The mode MUST remain `OFF` until the user chooses. Choosing launch-anyway proceeds to `PENDING_SETUP` (ENTER). Choosing cancel leaves the mode `OFF` without signaling ENTER. If the ClickHouse volume query is unavailable or errors, the system MUST show a **distinct soft reason** that volume statistics are temporarily unavailable, keep mode `OFF`, and MUST NOT signal ENTER; it MUST NOT treat the error as zero impressions and MUST NOT present the low-impressions warning as if the volume was successfully measured. This is a soft warning gate (the user MAY proceed at their own risk when volume was measured low), distinct from the stats-freshness hard block and from the empty allowed-set non-ready rule. When the measured aggregate meets or exceeds the threshold, enable proceeds without this warning.

#### Scenario: Low recent impressions warns with a choice
- **GIVEN** a campaign has paid bot management active, passes the stats freshness gate, and mode is `OFF`
- **AND** the measured campaign-level aggregate recent keyword impressions (calendar days covering last-24h wall-clock) are below the minimum threshold
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
- **GIVEN** the measured campaign-level aggregate recent keyword impressions (calendar days covering last-24h wall-clock) meet or exceed the minimum threshold
- **WHEN** the user presses Enable
- **THEN** the low recent-impressions warning is not shown
- **AND** enable proceeds per the normal enable path

#### Scenario: ClickHouse volume error shows a distinct soft reason
- **GIVEN** a campaign has paid bot management active, passes the stats freshness gate, and mode is `OFF`
- **AND** the campaign volume query against ClickHouse is unavailable or errors
- **WHEN** the user presses Enable
- **THEN** the campaign mode remains `OFF`
- **AND** ENTER is not signaled
- **AND** the user sees a distinct soft reason that volume statistics are temporarily unavailable
- **AND** the user does not see the measured low-impressions warning presented as if volume was successfully measured

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

### Requirement: Explicit keyword-set confirmation starts a durable WARM_UP stage
Confirming A/B Hold participation MUST require the user to explicitly confirm the campaign's keyword set before any target place is proposed or fixed. That confirmation MUST enter a durable pre-epoch WARM_UP stage in **duration-configuration** state (Telegram S2): the confirmed keyword set becomes durable and `warmup_started_at` MUST remain unset so the user can configure (and MAY increase) duration before the timer runs. The WARM_UP **timer** MUST start only when the user confirms the duration (Telegram S2 → S3). Manually changing the confirmed keyword set while WARM_UP is running MUST end the running WARM_UP timer, return the campaign to duration-configuration, and MUST start a new WARM_UP timer only after a subsequent duration confirmation; the elapsed time of the previous timer MUST NOT carry over.

#### Scenario: Keyword-set confirmation enters WARM_UP duration configuration
- **GIVEN** a campaign has paid bot management active and passes the existing enable gates (freshness, V3-only, plan max CPO, launch-volume soft-gate)
- **WHEN** the user explicitly confirms the campaign's keyword set for A/B Hold
- **THEN** the campaign enters the WARM_UP stage in duration-configuration state
- **AND** `warmup_started_at` remains unset (timer has not started)
- **AND** no target place is proposed or fixed yet

#### Scenario: Duration confirmation starts the WARM_UP timer
- **GIVEN** a campaign is in WARM_UP duration-configuration after keyword-set confirmation
- **WHEN** the user confirms the WARM_UP duration (default 24 hours or a longer user-chosen value)
- **THEN** the confirmed duration is persisted
- **AND** `warmup_started_at` is set
- **AND** the WARM_UP timer runs at that duration

#### Scenario: Manual keyword-set change during WARM_UP restarts the timer via duration confirmation
- **GIVEN** a campaign is in the WARM_UP stage with a running warm-up timer
- **WHEN** the user manually changes the confirmed keyword set
- **THEN** the running warm-up timer ends without completing
- **AND** the campaign returns to WARM_UP duration-configuration with `warmup_started_at` unset
- **AND** a new warm-up timer starts only after the user confirms duration again
- **AND** elapsed time from the previous timer is not carried over

### Requirement: WARM_UP duration defaults to 24 hours and MUST NOT be reduced below 24 hours
The WARM_UP stage MUST have a default duration of 24 hours and a minimum duration of 24 hours. Duration configuration MUST be reachable on the happy path after keyword-set confirmation and before the timer starts. The user MAY increase the WARM_UP duration for a campaign. The system MUST NOT allow the user to configure a WARM_UP duration shorter than 24 hours, and the system MUST NOT itself shorten an in-progress WARM_UP below 24 hours from its start.

#### Scenario: Default WARM_UP duration is 24 hours
- **GIVEN** the user confirms keyword set and reaches WARM_UP duration configuration without changing the duration
- **WHEN** the user confirms the duration
- **THEN** the WARM_UP duration is 24 hours
- **AND** the timer starts at that duration

#### Scenario: User increases WARM_UP duration
- **GIVEN** the user is in WARM_UP duration configuration after keyword-set confirmation
- **WHEN** the user sets a WARM_UP duration longer than 24 hours and confirms it
- **THEN** the WARM_UP stage uses the longer, user-chosen duration
- **AND** the timer starts at that longer duration

#### Scenario: User cannot reduce WARM_UP below 24 hours
- **GIVEN** the user is configuring the WARM_UP duration
- **WHEN** the user attempts to set a duration shorter than 24 hours
- **THEN** the system rejects the shorter duration
- **AND** the WARM_UP duration remains at least 24 hours

### Requirement: WARM_UP freezes automatic keyword growth while allowing safety exclusion
While a campaign is in the WARM_UP stage, the system MUST NOT automatically add new keywords to the confirmed keyword set and MUST NOT automatically return a keyword that was excluded. The system MAY still exclude a keyword during WARM_UP for safety reasons unrelated to experiment growth (for example, overspend protection relative to plan max CPO). WARM_UP MUST NOT fix a target place for any keyword; target place fixation happens only after WARM_UP through the separate target-place confirmation requirement below. The existing keyword-level view threshold (at least 100 views in the weekly keyword-card statistics window) and the existing campaign-level launch-volume threshold used at enable time keep their existing semantics as eligibility/soft-gate conditions and are NOT the WARM_UP duration.

#### Scenario: No automatic keyword addition during WARM_UP
- **GIVEN** a campaign is in the WARM_UP stage
- **WHEN** ordinary automation would otherwise add a new keyword to the campaign
- **THEN** that keyword is not added to the confirmed keyword set during WARM_UP

#### Scenario: No automatic return of an excluded keyword during WARM_UP
- **GIVEN** a keyword was excluded from the confirmed keyword set before or during WARM_UP
- **WHEN** ordinary automation would otherwise return that keyword
- **THEN** the keyword is not automatically returned during WARM_UP

#### Scenario: Safety exclusion remains allowed during WARM_UP
- **GIVEN** a campaign is in the WARM_UP stage
- **AND** a keyword triggers an overspend-protection condition relative to plan max CPO
- **WHEN** the safety exclusion check runs
- **THEN** that keyword MAY be excluded during WARM_UP for that safety reason

#### Scenario: Target place is not fixed during WARM_UP
- **GIVEN** a campaign is in the WARM_UP stage
- **WHEN** the WARM_UP stage is in progress
- **THEN** no keyword target place is fixed as a confirmed epoch parameter

### Requirement: After WARM_UP the system displays factual position and proposed target place as separate fields
Once WARM_UP completes, for each keyword in the confirmed keyword set the system MUST display the keyword's factual current position and, separately, a proposed target place computed by `ab_hold_target_place_from_keyword(position)` from that factual position. Factual position and target place are separate semantic fields and MUST be displayed and tracked separately, even where their numeric values coincide after rounding or clamping. The system MUST NOT merge factual position and target place into a single displayed or stored value.

#### Scenario: Post-warm-up display shows factual position and proposed target place separately
- **GIVEN** WARM_UP has completed for a campaign's confirmed keyword set
- **WHEN** the user views the post-warm-up screen for a keyword
- **THEN** the keyword's factual current position is shown
- **AND** a proposed target place computed from that factual position is shown as a separate field
- **AND** the two fields are not merged into one value

#### Scenario: Numeric coincidence does not merge the fields
- **GIVEN** a keyword's factual position and its proposed target place happen to be numerically equal after rounding or clamping
- **WHEN** the post-warm-up screen displays the keyword
- **THEN** factual position and target place are still presented as two distinct fields

### Requirement: Target place requires explicit confirmation and becomes immutable for the epoch
Fixing a keyword's target place as a confirmed epoch parameter MUST require an explicit user confirmation of the proposed target place shown after WARM_UP. Once confirmed, the target place MUST become durable and MUST remain immutable for the current epoch: neither a later ENTER/setup tick nor a retry of activation MUST recalculate it. Ordinary drift of the keyword's factual position after confirmation MUST NOT reopen the confirmation and MUST NOT trigger recalculation of the confirmed target place for that epoch. Changing a confirmed target place is possible only by starting a new epoch (for example after EXIT and a new ENTER, or after a keyword-set change that restarts WARM_UP and the full confirmation sequence).

#### Scenario: User confirms a proposed target place
- **GIVEN** the post-warm-up screen shows a proposed target place for a keyword
- **WHEN** the user explicitly confirms that target place
- **THEN** the target place becomes a durable confirmed parameter of the current epoch

#### Scenario: Confirmed target place is not recalculated on a later setup tick or retry
- **GIVEN** a keyword has a confirmed target place for the current epoch
- **WHEN** a later A/B Hold setup tick or an activation retry runs for that epoch
- **THEN** the confirmed target place is not recalculated or overwritten

#### Scenario: Ordinary position drift after confirmation does not reopen confirmation
- **GIVEN** a keyword has a confirmed target place for the current epoch
- **AND** the keyword's factual position later drifts away from that confirmed target place
- **WHEN** the system observes the drifted factual position
- **THEN** the confirmation is not reopened
- **AND** the confirmed target place for that epoch is not recalculated

### Requirement: Keyword bidder only holds confirmed target places
While a campaign is holding an active A/B Hold epoch, the keyword bidder MUST direct bids only toward the confirmed target places of that epoch. The bidder MUST NOT add a keyword to the confirmed keyword set, MUST NOT return an excluded keyword, and MUST NOT change a confirmed target place.

#### Scenario: Bidder targets the confirmed target place
- **GIVEN** a campaign is in an active A/B Hold epoch with confirmed target places
- **WHEN** the bidder updates bids during hold
- **THEN** bids are directed toward the confirmed target places
- **AND** the bidder does not add, return, or retarget any keyword outside those confirmed target places

### Requirement: Auto participation requires a separate explicit confirmation
Whether the campaign's Auto (automatic) advertising participates in the current A/B Hold epoch MUST be confirmed by a separate explicit user action, distinct from confirming the Search keyword set or Search target places. Confirming the Search keyword set MUST NOT be treated as implying Auto participation confirmation, and confirming Auto participation MUST NOT be treated as implying Search confirmation.

#### Scenario: Auto participation is confirmed independently of Search
- **GIVEN** the user has confirmed the Search keyword set for the epoch
- **WHEN** the user is asked to confirm Auto participation
- **THEN** a separate explicit confirmation action is required
- **AND** the Search keyword-set confirmation alone does not confirm Auto participation

### Requirement: Auto bid requires a separate explicit confirmation and is frozen while ACTIVE
The Auto bid value for the current epoch MUST be confirmed by a separate explicit user action, distinct from the Auto participation confirmation and from any Search confirmation. Once the campaign is in an active A/B Hold epoch, ordinary Auto bid auto-update mutators MUST NOT change the confirmed Auto bid.

#### Scenario: Auto bid is confirmed independently of Auto participation
- **GIVEN** the user has confirmed Auto participation for the epoch
- **WHEN** the user is asked to confirm the Auto bid for the epoch
- **THEN** a separate explicit confirmation action is required for the Auto bid value

#### Scenario: Ordinary Auto bid auto-update does not change the confirmed bid while ACTIVE
- **GIVEN** a campaign is in an active A/B Hold epoch with a confirmed Auto bid
- **WHEN** ordinary Auto bid auto-update would otherwise change the bid
- **THEN** the confirmed Auto bid for that epoch is not changed by that ordinary auto-update path

### Requirement: Activation requires a durable PENDING intent recorded before any WB mutation
After the keyword set, target places, Auto participation, and Auto bid are all confirmed for an epoch, the system MUST persist a durable PENDING activation intent (the confirmed parameters together with an epoch identifier) before performing any Wildberries write for that epoch. The system MUST NOT perform a Wildberries mutation of the confirmed parameters based on an intent that has not yet been durably recorded.

#### Scenario: PENDING intent is recorded before any WB write
- **GIVEN** all confirmations (keyword set, target places, Auto participation, Auto bid) are complete for an epoch
- **WHEN** the system prepares to synchronize Wildberries for that epoch
- **THEN** a durable PENDING activation intent is recorded first
- **AND** the first Wildberries write for that epoch happens only after that durable record exists

### Requirement: Partial Wildberries synchronization is recoverable and keeps the campaign non-ACTIVE
If Wildberries synchronization for an epoch's confirmed parameters completes only partially, the campaign MUST remain in a non-ACTIVE state with the same durable PENDING intent and the same epoch identifier preserved. The campaign MUST NOT be presented as an active, ready-to-test A/B Hold epoch while synchronization for that epoch is incomplete.

#### Scenario: Partial sync leaves the campaign non-ACTIVE with the same intent preserved
- **GIVEN** Wildberries synchronization for an epoch was attempted and only partially completed
- **WHEN** the system evaluates the campaign's A/B Hold status
- **THEN** the campaign is not treated as an active, ready-to-test A/B Hold epoch
- **AND** the durable PENDING intent and epoch identifier from that attempt are preserved

### Requirement: Retry reuses the same epoch and confirmed parameters without recalculation
When the system retries Wildberries synchronization after an incomplete attempt, the retry MUST reuse the same epoch identifier and the same confirmed parameters (keyword set, target places, Auto participation, Auto bid) recorded in the durable PENDING intent. The retry MUST NOT recalculate target places, MUST NOT recalculate or re-request confirmation of the Auto bid, and MUST NOT start a new epoch. A new epoch is created only through a new full confirmation sequence (for example after EXIT and a new ENTER, or after a keyword-set change that restarts WARM_UP).

#### Scenario: Retry reuses the same epoch without recalculating confirmed parameters
- **GIVEN** a Wildberries synchronization attempt for an epoch was incomplete
- **WHEN** the system retries synchronization for that epoch
- **THEN** the retry uses the same epoch identifier and the same confirmed keyword set, target places, Auto participation, and Auto bid
- **AND** no target place or Auto bid is recalculated as part of the retry
- **AND** no new epoch is started by the retry

### Requirement: After successful Wildberries sync, later ticks finish activation without re-entering Wildberries
When Wildberries synchronization for an epoch is durably marked fully successful (`card_ab_hold_sync_status=complete`) and the campaign mode is still not ACTIVE (the in-PENDING phase MAY remain `WB_SYNC`), a subsequent shop-runner epoch tick MUST only finish activation (transition toward ACTIVE). That tick MUST NOT re-apply the confirmed epoch intent to the durable store, MUST NOT re-run Wildberries synchronization for that generation, and MUST NOT perform further Wildberries mutations for that generation. Incomplete synchronization states (`pending` / `partial`) remain eligible for Wildberries retry as specified in the retry requirement above. Generation and idempotency semantics are unchanged; ACTIVE remains Allowed only after a fully successful Wildberries synchronization for that generation.

#### Scenario: Complete sync residual activates without re-entering Wildberries
- **GIVEN** Wildberries synchronization for the current epoch/generation is durably marked complete (`card_ab_hold_sync_status=complete`)
- **AND** the campaign mode is still not ACTIVE
- **AND** the phase MAY remain `WB_SYNC`
- **WHEN** the next shop-runner epoch tick runs
- **THEN** the system only finishes activation
- **AND** it does not re-apply the confirmed epoch intent to the durable store
- **AND** it does not re-synchronize that generation to Wildberries
- **AND** it does not perform further Wildberries mutations for that generation

### Requirement: Stale or missing statistics freeze keyword and bid mutations without stopping the campaign
While a campaign is in WARM_UP, awaiting confirmation, or in an active A/B Hold epoch, if the campaign or a keyword has stale or missing statistics, the system MUST NOT make a keyword inclusion/exclusion decision and MUST NOT make a Search or Auto bid mutation based on that stale or missing data; both classes of **decide** MUST freeze for the affected keyword or campaign until fresh statistics are available. Keyword inclusion/exclusion includes ENTER/setup Classification **FAIL→OFF** (epoch-managed `process_ab_setup` / `apply_ab_hold_setup_mutations`): that path MUST NOT write keyword OFF when stats are stale or missing. Stale or missing statistics alone MUST NOT be a reason to stop the campaign; freezing inclusion/exclusion and bid mutation decisions is distinct from, and MUST NOT be treated as equivalent to, stopping the campaign. After a durable PENDING activation intent exists for the epoch, applying that intent's confirmed parameters to PostgreSQL and synchronizing them to Wildberries (apply snapshot) MUST NOT be blocked solely because statistics are stale or missing; decide-class freezes MAY still apply on the same tick. The paid UI MUST show a soft-policy disclaimer (at Enable and/or hold/status) that temporary statistics gaps are usually harmless, that the bot freezes decide-class changes rather than guessing, and that the user remains responsible for monitoring the test; the copy MUST NOT claim that protection was "weakened" if the behavior is freeze-decide.

#### Scenario: Stale statistics freeze keyword inclusion/exclusion decisions
- **GIVEN** a campaign is in WARM_UP, awaiting confirmation, or in an active A/B Hold epoch
- **AND** a keyword's statistics are stale or missing
- **WHEN** an inclusion or exclusion decision for that keyword would otherwise run
- **THEN** that decision is frozen for the affected keyword until fresh statistics are available

#### Scenario: Stale statistics freeze epoch-managed setup FAIL→OFF
- **GIVEN** a campaign is in `PENDING_SETUP` on the epoch-managed setup path
- **AND** campaign or keyword statistics are stale or missing (`stats_fresh=False`)
- **WHEN** Classification would otherwise mark keywords FAIL→OFF
- **THEN** `apply_ab_hold_setup_mutations` / FAIL→OFF MUST NOT run for that tick
- **AND** the epoch is not aborted or reset solely because of the stale or missing statistics

#### Scenario: Stale statistics freeze Search and Auto bid mutations
- **GIVEN** a campaign is in WARM_UP, awaiting confirmation, or in an active A/B Hold epoch
- **AND** the campaign's statistics are stale or missing
- **WHEN** a Search or Auto bid mutation would otherwise run
- **THEN** that mutation is frozen for the affected campaign until fresh statistics are available

#### Scenario: Stale statistics alone do not stop the campaign
- **GIVEN** a campaign has stale or missing statistics during WARM_UP, awaiting confirmation, or an active A/B Hold epoch
- **WHEN** the system evaluates the campaign's operational state
- **THEN** the campaign is not stopped solely because of the stale or missing statistics

#### Scenario: Stale statistics do not block apply of a recorded PENDING intent
- **GIVEN** a durable PENDING activation intent exists for an epoch
- **AND** the campaign or keyword statistics are stale or missing
- **WHEN** shop-runner would apply that intent to PostgreSQL and synchronize it to Wildberries
- **THEN** that apply snapshot and Wildberries synchronization MUST proceed (MUST NOT be skipped solely because of stale or missing statistics)
- **AND** decide-class keyword inclusion/exclusion and ordinary Search/Auto bid mutations MUST still freeze until fresh statistics are available

#### Scenario: Soft-policy disclaimer is visible to the user
- **GIVEN** a paid user opens A/B Hold Enable and/or an in-test status screen
- **WHEN** the instruction or status is shown
- **THEN** a soft-policy disclaimer is observable (temporary stats gaps; freeze decide; user monitors the test)
- **AND** the copy does not describe freeze-decide as "weakened protection"

### Requirement: Daily budget control remains a reused stop-threshold, not a new financial-safety mechanism
A/B Hold MUST reuse the existing daily budget / campaign activity-control behavior as-is: it is a stop threshold, not a hard cap, and spend MAY overshoot that threshold because of statistics reporting delay, worker cadence, in-flight spend, concurrent write paths, and top-up not clipped to remaining daily room; there is no guaranteed numeric upper bound on that overshoot. The daily budget resets each day, and spend MAY resume the next day after the reset. A/B Hold MUST NOT introduce an absolute test budget, an epoch spend cap, a velocity cap, a generic financial safety latch, a new emergency-stop subsystem, or global refill/restart suppression as part of this capability.

#### Scenario: Spend may exceed the daily stop threshold
- **GIVEN** a campaign is in an active A/B Hold epoch under the existing daily budget control
- **WHEN** spend approaches the daily stop threshold
- **THEN** spend MAY exceed that threshold before the campaign stops for the day
- **AND** the system does not guarantee a numeric upper bound on that overshoot

#### Scenario: Spend resumes after the daily reset
- **GIVEN** a campaign stopped for the day under the daily budget control while in an active A/B Hold epoch
- **WHEN** the daily budget resets
- **THEN** spend MAY resume the next day
- **AND** this resumption is not a violation of the A/B Hold epoch's frozen parameters

#### Scenario: No new financial-safety mechanism is introduced
- **GIVEN** a campaign is in an active A/B Hold epoch
- **WHEN** daily budget control is evaluated for that campaign
- **THEN** no absolute test budget, epoch spend cap, velocity cap, financial safety latch, emergency-stop subsystem, or global refill/restart suppression is applied as part of A/B Hold

### Requirement: Confirmation screens paginate keyword lists at a fixed page size
Any A/B Hold confirmation screen that lists keywords (for example the post-warm-up factual-position/target-place display or the confirmed keyword-set review) MUST paginate that list with a page size of 10 keywords per page.

#### Scenario: Keyword list is paginated at 10 per page
- **GIVEN** a confirmation screen lists more than 10 keywords
- **WHEN** the user views the list
- **THEN** the screen shows at most 10 keywords per page
- **AND** the user can navigate to additional pages to see the remaining keywords

### Requirement: Back preserves the confirmation draft; Cancel is a separate explicit action
During the A/B Hold confirmation sequence (keyword-set confirm, post-warm-up target-place confirm, Auto participation confirm, Auto bid confirm), a Back control MUST preserve the user's in-progress draft for the current confirmation step so the user can return to it. Cancel MUST be a separate, explicitly distinct action from Back; choosing Cancel MUST discard the in-progress confirmation attempt rather than preserve it. The current `card_ab_hold` MVP-1 screen is not the reference for this confirmation sequence; the full screen-by-screen UX contract is defined separately.

#### Scenario: Back preserves the in-progress draft
- **GIVEN** the user is partway through a confirmation step with an in-progress draft
- **WHEN** the user presses Back
- **THEN** the in-progress draft for that step is preserved
- **AND** the user can resume from where they left off

#### Scenario: Cancel discards the confirmation attempt
- **GIVEN** the user is partway through a confirmation step with an in-progress draft
- **WHEN** the user chooses Cancel as a separate explicit action from Back
- **THEN** the in-progress confirmation attempt is discarded
- **AND** the draft is not preserved for that attempt

### Requirement: Broad enablement is gated behind owner manual test, limited beta, and an explicit owner decision
Rollout of the WARM_UP/confirmation/epoch flow MUST proceed through an owner manual test on the owner's own or test campaigns, then a limited opt-in beta with structured feedback collection from opted-in paid users, before broad enablement for all paid users. Broad enablement for all paid users MUST NOT proceed until the owner has explicitly accepted the sole open owner decision gating this rollout (OD-05).

#### Scenario: Owner manual test precedes any beta rollout
- **GIVEN** the WARM_UP/confirmation/epoch flow has been implemented
- **WHEN** rollout begins
- **THEN** the owner performs a manual test before any user is opted into a beta

#### Scenario: Limited opt-in beta collects structured feedback before broad enablement
- **GIVEN** the owner manual test has completed
- **WHEN** the flow is made available to a limited set of opted-in paid users
- **THEN** feedback from that beta is collected in a structured way
- **AND** broad enablement is not performed solely because the beta started

#### Scenario: Broad enablement is blocked until OD-05 is accepted
- **GIVEN** the limited opt-in beta has produced feedback
- **WHEN** broad enablement for all paid users is considered
- **THEN** broad enablement does not proceed until the owner explicitly accepts OD-05

### Requirement: A/B Hold epoch mutable-state boundaries have an explicit status
The A/B Hold epoch introduces mutable state boundaries beyond the existing allowed-set/minus-phrase boundary already governed by this capability. Each of the following boundaries MUST have an explicit, spec-defined status: confirmed keyword set (frozen once confirmed; changing it during WARM_UP restarts WARM_UP; changing it after activation requires a new epoch), confirmed target places (frozen/immutable within the epoch after confirmation; not reopened by drift), Auto participation (confirmed, fixed for the epoch), Auto bid (confirmed, frozen from ordinary auto-update while ACTIVE), keyword inclusion/exclusion decisions under stale/missing statistics (frozen, not decided), Search/Auto bid mutations under stale/missing statistics (frozen, not decided), Wildberries write actions for the epoch (forbidden before the durable PENDING intent exists; allowed only for the recorded epoch's confirmed parameters), daily budget / campaign activity-control (explicitly out of scope for new freezing — the existing reused stop-threshold behavior continues unchanged, including its ability to pause/resume the campaign for operational reasons).

#### Scenario: Every new epoch boundary has a defined status
- **GIVEN** a reviewer inspects the A/B Hold epoch behavior for this capability
- **WHEN** they check the status of confirmed keyword set, confirmed target places, Auto participation, Auto bid, keyword inclusion/exclusion under stale stats, Search/Auto bid mutation under stale stats, Wildberries write timing, and daily budget control
- **THEN** each boundary has one of frozen, allowed, restored/enforced, or out-of-scope explicitly documented for it
- **AND** none of these boundaries is left undocumented

### Requirement: ENTER setup classifies keywords by pay_for_order and views
When A/B Hold is enabled, the system MUST run a one-time setup that classifies keywords against the campaign plan max CPO (not resolve) and weekly keyword views from the same statistics source as the keyword card. A keyword that passes this classification becomes eligible to enter the WARM_UP stage and, after WARM_UP, the target-place confirmation step; passing this classification MUST NOT by itself fix a target place. Target place fixation happens only through the separate WARM_UP and target-place confirmation requirements, not as part of this classification.

#### Scenario: Keyword passes setup
- **GIVEN** paid bot management is active
- **AND** a keyword has pay_for_order less than or equal to plan max CPO
- **AND** that keyword has at least 100 views in the weekly keyword-card statistics window
- **WHEN** A/B Hold enter setup runs
- **THEN** the keyword remains active for the held profile
- **AND** the keyword becomes eligible for the WARM_UP stage and the post-warm-up target-place confirmation step
- **AND** the keyword's target place is not fixed by this classification alone

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

### Requirement: ACTIVE without ENTER setup snapshot is forbidden
The system MUST NOT transition a campaign to ACTIVE A/B Hold except via a completed epoch: successful `process_ab_setup` / setup apply that includes allowed-set capture and PostgreSQL snapshot persistence (decision §8), a completed WARM_UP of at least the configured duration (minimum 24 hours), explicit confirmation of target places, explicit confirmation of Auto participation, explicit confirmation of Auto bid, a durable PENDING activation intent recorded before any Wildberries mutation for that epoch, and a Wildberries synchronization for that epoch confirmed as fully successful (not partial). Direct writes of `active` (including Excel or other non-setup, non-epoch paths) MUST NOT create a held campaign. A retry of Wildberries synchronization for an already-recorded epoch MAY still lead to ACTIVE once that retry fully succeeds, without repeating the confirmation steps and without recalculating the confirmed parameters.

#### Scenario: Non-setup ACTIVE write is rejected or ignored
- **GIVEN** a write path other than A/B Hold ENTER setup attempts to set mode to active
- **WHEN** that write is processed
- **THEN** the campaign does not become ACTIVE without the ENTER allowed-set snapshot
- **AND** hold enforcement does not treat an empty/missing allowed-set snapshot as a successful freeze

#### Scenario: ACTIVE requires a completed WARM_UP and full confirmation sequence
- **GIVEN** a campaign has an ENTER allowed-set snapshot but WARM_UP has not yet completed, or target places / Auto participation / Auto bid have not all been explicitly confirmed
- **WHEN** the system evaluates whether the campaign may become ACTIVE
- **THEN** the campaign does not become ACTIVE
- **AND** the UI does not report that A/B tests may start

#### Scenario: ACTIVE requires a fully successful, not partial, Wildberries synchronization
- **GIVEN** all confirmations are complete and a durable PENDING intent exists for an epoch
- **AND** the Wildberries synchronization for that epoch is only partially complete
- **WHEN** the system evaluates whether the campaign may become ACTIVE
- **THEN** the campaign does not become ACTIVE
- **AND** the same durable PENDING intent and epoch identifier remain available for retry

#### Scenario: A successful retry of the same epoch may reach ACTIVE without repeating confirmations
- **GIVEN** a Wildberries synchronization retry for an already-recorded epoch completes fully and successfully
- **WHEN** the system evaluates the campaign's A/B Hold status
- **THEN** the campaign becomes ACTIVE for that epoch
- **AND** the confirmation steps and confirmed parameters were not repeated or recalculated to reach that result
