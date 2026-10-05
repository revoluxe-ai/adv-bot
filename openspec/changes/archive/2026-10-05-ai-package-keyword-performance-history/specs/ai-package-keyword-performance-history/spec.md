# ai-package-keyword-performance-history Specification (delta)

## ADDED Requirements

### Requirement: Canonical keyword daily grain

Keyword daily export MUST preserve grain: shop × logical resource (`adv_setting_id`)
× physical `adv_id` × leg where proven × nmid × normalized query × date. Silent
cross-adv_id or cross-leg aggregation MUST NOT occur.

#### Scenario: Strict daily grain preserved

- **GIVEN** CH rows exist for two physical adv_ids under one shop resource
- **WHEN** `keyword_daily` is exported
- **THEN** each row MUST retain distinct `adv_id` and `leg_role`
- **AND** MUST NOT collapse to date-only aggregate

#### Scenario: Physical adv_id on every row

- **GIVEN** rebound historical adv_id has cluster stats
- **WHEN** daily export includes that history
- **THEN** each row MUST include the physical `adv_id` that produced the fact

### Requirement: Full available history independent of ExportPeriod

Keyword performance datasets MUST export all available persisted history for scope
(`first_available`..`last_available` from CH MIN/MAX). Caller `ExportPeriod` MUST
NOT clip keyword dataset date range. DATA_MAP MUST document both bounds separately.

#### Scenario: History not clipped to ExportPeriod

- **GIVEN** CH contains keyword stats from 2024-01-01 through 2025-06-15
- **AND** export invoked with `ExportPeriod` 2025-01-01..2025-03-31 (narrow caller window)
- **AND** `generated_at` is 2026-01-08T15:00:00Z (explicitly later than all returned history)
- **WHEN** keyword daily export completes
- **THEN** rows MUST include dates through `last_available` (2025-06-15)
- **AND** MUST NOT stop at `ExportPeriod.end` (2025-03-31) for keyword datasets
- **AND** MUST NOT include any date after `package_cutoff_date` (2026-01-08)

#### Scenario: UI pagination window not used

- **GIVEN** UI default pagination uses 7-day pages
- **WHEN** AI keyword export runs
- **THEN** export MUST NOT use UI pagination limits as history bound

### Requirement: Auto and Search identity separation

Auto (shelf) and Search (keywords) campaign ids MUST remain separate. Export MUST
NOT silently merge Auto and Search into one indistinguishable row.

#### Scenario: Auto and Search adv_ids distinguishable

- **GIVEN** inventory row with auto_adv_id A and search_adv_id K
- **WHEN** keyword daily export runs
- **THEN** facts for A and K MUST appear as separate rows with correct `leg_role`
- **AND** MUST NOT merge metrics across A and K without explicit labeled aggregate file

### Requirement: Rebound membership expansion

Export scope MUST expand to rebound/rebind adv_ids via Redis membership read keyed
by PG `AdvSetting.id`. Rebound sets prove membership only; transition dates MUST
NOT be invented.

#### Scenario: Rebound adv_ids included in CH filter

- **GIVEN** Redis rebound set contains historical adv_id H for adv_setting_id S
- **WHEN** keyword scope is built
- **THEN** CH queries MUST include H
- **AND** daily rows for H MUST retain adv_id=H provenance

#### Scenario: Rebound does not invent transition timeline

- **GIVEN** rebound set lists H1 and H2 without timestamps
- **WHEN** export emits rows
- **THEN** export MUST NOT attach guessed rebind interval dates to rows

### Requirement: No duplicate logical counting

When one query appears in multiple legs/campaigns, identity MUST preserve separate
rows so logical aggregation does not double-count.

#### Scenario: Same query two legs two rows

- **GIVEN** norm_query Q has stats under auto adv_id A and search adv_id K
- **WHEN** keyword daily export runs
- **THEN** at least two rows MUST exist (A,Q) and (K,Q) for same date
- **AND** window aggregation MUST sum only within explicit identity keys

### Requirement: Missing is not zero

Missing daily row or missing metric MUST NOT be coerced to numeric zero for
views, orders, or position.

#### Scenario: Missing day not fabricated zeros

- **GIVEN** no CH row for (adv_id, nmid, norm_query, date D)
- **WHEN** keyword daily export runs
- **THEN** export MUST NOT emit views=0/orders=0 for D solely due to absence
- **AND** coverage MUST record missing day

#### Scenario: Missing position not coerced

- **GIVEN** position absent for date D
- **WHEN** daily row is emitted
- **THEN** position field MUST be null or absent
- **AND** MUST NOT substitute max_pos or zero

### Requirement: Forbidden presentation sources

Telegram/graph presentation paths (`graphic_positions_creator`, nearest-day fill,
jitter, zero→max_pos SQL) MUST NOT be used as canonical export sources.

#### Scenario: Graphic creator not on export path

- **GIVEN** export assembles keyword datasets
- **WHEN** module import graph is traced
- **THEN** `graphic_positions_creator` MUST NOT be imported by keyword export modules

#### Scenario: UI daily rollup SQL not authority

- **GIVEN** keyword daily export
- **WHEN** CH SQL is selected
- **THEN** MUST NOT use `get_keyword_daily_history.sql` date-only GROUP BY as authority

### Requirement: Position direction and delta convention

Position semantics MUST document: lower numeric position = better ranking.
`position_delta = position_end - position_start` (negative delta = improvement).
DATA_MAP MUST document convention.

#### Scenario: Delta sign documented in DATA_MAP

- **WHEN** DATA_MAP is emitted
- **THEN** it MUST state lower position is better and delta formula

### Requirement: Deterministic window catalog

Window engine MUST implement Owner catalog: rolling closed 1d/3d/7d/14d/30d/90d/
180d/365d; MTD/QTD/YTD (open-to-last-closed-day); previous calendar month/quarter/
year; year_before_previous; all_available; comparable previous windows. Calendar
year windows MUST NOT equal rolling 365d.

#### Scenario: Rolling 365d differs from previous calendar year

- **GIVEN** export date anchor 2026-03-15
- **WHEN** windows `last_365d` and `previous_year` computed
- **THEN** date bounds MUST differ
- **AND** DATA_MAP MUST document distinct definitions

#### Scenario: Comparable previous window aligned

- **GIVEN** sufficient history for 7d vs prev 7d
- **WHEN** change dataset emitted
- **THEN** previous window MUST be immediately preceding 7 closed days
- **AND** MUST NOT overlap current window

#### Scenario: Insufficient history partial coverage

- **GIVEN** only 3 days history available
- **WHEN** 7d window computed
- **THEN** window row MUST mark partial coverage with observed_days=3, requested_days=7

### Requirement: Window metrics from sum ratios

Window traffic/funnel rates MUST use ratios of summed numerators/denominators over
observed days. Intraday summation MUST NOT replace daily argMax snapshots.

#### Scenario: CTR from summed clicks and views

- **GIVEN** two days with views/clicks in window
- **WHEN** window CTR computed
- **THEN** CTR MUST equal sum(clicks)/sum(views) when views sum > 0

### Requirement: Conservative spend semantics

`spend_rub` MUST be factual only with proven WB→storage lineage. UI formula
`CPM×views/1000` MUST NOT be exported as factual spend. Per-row
`query_spend_status` MUST be explicit. CPO only when spend proven.

#### Scenario: NULL spend not fabricated

- **GIVEN** CH row with views and cpm but spend column NULL
- **WHEN** daily row exported
- **THEN** spend_rub MUST be null
- **AND** query_spend_status MUST be UNAVAILABLE
- **AND** CPO MUST be null

#### Scenario: Factual spend when column populated

- **GIVEN** CH spend non-null from ingest in the row-coherent latest snapshot tuple
- **WHEN** daily row exported
- **THEN** spend_rub MUST reflect the snapshot tuple `spend` value (not per-field argMax)
- **AND** query_spend_status MUST be FACTUAL

### Requirement: Current state deterministic selection

`keyword_current_state` MUST select latest observation deterministically using
(observation_date, observation_ts, tie_breaker) ordering; MUST include freshness
timestamp, not arbitrary is_current flag without time evidence.

#### Scenario: Latest row wins deterministically

- **GIVEN** two observations for same identity with different timestamps
- **WHEN** current state exported
- **THEN** row with greatest (date, ts) MUST be selected
- **AND** selection MUST be stable across repeated export

### Requirement: Change dataset facts only

`keyword_changes` MUST emit current, previous, deltas, and coverage without AI
labels (GOOD/BAD/INCREASE_BID/STOP).

#### Scenario: No AI labels in changes

- **WHEN** keyword_changes rows emitted
- **THEN** MUST NOT contain recommendation labels
- **AND** MUST contain numeric/string deltas only

### Requirement: Bid decision context classification

Bid/decision timeline entries MUST classify as OBSERVATION, DECISION, ACTION, or
OBSERVED_POST_STATE only when source proves class. `bid_decision_log` MUST NOT
masquerade as executed bid history.

#### Scenario: Decision log labeled DECISION

- **GIVEN** row sourced from bid_decision_log
- **WHEN** attached to export context
- **THEN** event_class MUST be DECISION
- **AND** MUST NOT be labeled ACTION

### Requirement: Position observation grain

Keyword position observations MUST retain grain date × nmid × query ×
position_type × source without unsafe many-to-many campaign assignment.

#### Scenario: Separate position types not merged

- **GIVEN** CLUSTER_AVG_POS and WB_KEYWORD_POSITION_API values for same query/day
- **WHEN** positions exported
- **THEN** MUST emit separate records by position_type
- **AND** MUST NOT average unlike types into organic_position

### Requirement: DATA_MAP and coverage mandatory

Export MUST include root `DATA_MAP.json` and `coverage.json` describing grain,
joins, semantics, timezone evidence, window catalog, limitations, unsupported/
failed/ambiguous joins.

#### Scenario: DATA_MAP lists keyword_daily grain

- **WHEN** package emitted
- **THEN** DATA_MAP MUST include keyword_daily primary key and join keys
- **AND** MUST document missing vs zero semantics

### Requirement: Row-coherent daily snapshot selection

Daily rollup MUST select a **full metric tuple** from the latest `timestamp` row
within `(adv_id, nmid, norm_query, date)`. Per-field nullable `argMax` MUST NOT
be used. Conflicting rows at the same max timestamp MUST fail-closed with
`SNAPSHOT_CONFLICT` / `AMBIGUOUS`; identical duplicates MAY collapse.

#### Scenario: Conflicting same-timestamp snapshots ambiguous

- **GIVEN** two intraday rows share max timestamp but disagree on spend or views
- **WHEN** daily row assembled
- **THEN** row MUST mark `AMBIGUOUS` with `SNAPSHOT_CONFLICT`
- **AND** affected metrics MUST be null
- **AND** MUST NOT pick arbitrary mixed fields from different rows

#### Scenario: Identical same-timestamp duplicates collapse

- **GIVEN** two intraday rows share max timestamp and identical metric tuple
- **WHEN** daily row assembled
- **THEN** row MUST emit the shared tuple once

### Requirement: raw_query unavailable without fabrication

`raw_query` MUST be null with `RAW_QUERY_UNAVAILABLE` when no distinct
source-proven raw-text column exists. `norm_query` MUST NOT be copied into
`raw_query`. PG `keyword_setting.text` MUST NOT be joined as raw without proven
1:1 correspondence.

#### Scenario: norm_query not used as raw_query

- **GIVEN** CH row has `norm_query` only (no separate raw column)
- **WHEN** daily row exported
- **THEN** `raw_query` MUST be null
- **AND** `raw_query_status` MUST be `RAW_QUERY_UNAVAILABLE`

### Requirement: Package cutoff excludes future dates and post-instant rows

All keyword MIN/MAX, daily, position, and decision SQL MUST apply
`package_cutoff_date` (UTC date from `generated_at`) and, where source temporal
semantics allow, `package_cutoff_instant` (`generated_at` UTC DateTime).
`keyword_position_from_api.version` MUST be treated as UTC epoch milliseconds
(proven writer `click_house_manager.update_positions:88`) and filtered with
`version <= cutoff_instant_ms` derived from `package_cutoff_instant`. Rows with
unproven version lineage only → date-only cutoff + `UNKNOWN_VERSION_TIME_SEMANTICS`
in coverage; MUST NOT apply blanket `SAME_DAY_INSTANT_UNSUPPORTED` to the proven
writer path. `last_available` MUST NOT include future source dates.

#### Scenario: Future CH dates excluded from last_available

- **GIVEN** CH contains rows through 2026-03-01 and export `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** keyword bounds computed
- **THEN** `last_available` MUST be at most 2026-01-07
- **AND** MUST NOT report 2026-03-01 as available

#### Scenario: Same-day post-instant rows excluded from daily facts

- **GIVEN** CH row with `date=2026-01-07` and `timestamp=2026-01-07T15:00:00Z`
- **AND** export `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** keyword daily export completes
- **THEN** row MUST NOT appear in keyword payloads
- **AND** daily bounds MUST respect `timestamp <= package_cutoff_instant`

#### Scenario: Same-day post-instant position rows excluded via version ms

- **GIVEN** CH position row with `date=2026-01-07` and `version` equal to UTC epoch ms
  for `2026-01-07T15:00:00Z`
- **AND** export `generated_at` is 2026-01-07T12:00:00Z
- **WHEN** keyword position export completes
- **THEN** row MUST NOT appear in position payloads
- **AND** position bounds MUST respect `version <= cutoff_instant_ms`

### Requirement: Cross-shop isolation and ownership validation

Keyword rows MUST NOT include data from other shops. Scope expansion MUST
validate PG ownership for every `(adv_id, adv_setting_id)` under the requested shop
**and** run a global adv_id overlap probe across all shops. A requested-shop-only PG
inventory query MUST NOT be treated as proof of global ownership isolation. Rebound
overlap without authoritative mapping MUST fail-closed (`AMBIGUOUS_OWNERSHIP`) without
duplicate logical emission. Coverage MUST record `ownership_evidence_scope`:
`REQUESTED_SHOP_PG_PLUS_GLOBAL_ADV_ID_OVERLAP`.

#### Scenario: Shop filter enforced

- **GIVEN** shops S1 and S2
- **WHEN** export for S1 runs
- **THEN** all keyword rows MUST have shop_id=S1 only

#### Scenario: Rebound adv_id without PG ownership ambiguous

- **GIVEN** rebound adv_id H appears in Redis for S1 but PG inventory cannot map H to S1
- **WHEN** scope is built
- **THEN** export MUST NOT emit rows assigning H under S1 logical resources
- **AND** coverage MUST record `AMBIGUOUS_OWNERSHIP` or `UNASSIGNED_PROVENANCE`

#### Scenario: Foreign-shop adv_id overlap fail-closed

- **GIVEN** expanded adv_id A maps to shop S2 in global PG inventory
- **AND** export requested for shop S1 without resource-qualified rebound anchor for A
- **WHEN** scope is built
- **THEN** export MUST NOT emit rows for A under S1
- **AND** coverage MUST record `FOREIGN_SHOP_ADV_ID` or `AMBIGUOUS_OWNERSHIP`

### Requirement: Campaign current state strict grain

Campaign `keyword_current_state` MUST derive from strict-grain
`(adv_id, nmid, norm_query)` daily snapshots. Each row MUST include
`campaign_slot_role` (`ACTIVE` / `REBOUND_HISTORICAL` / `AMBIGUOUS`). Rebound
physical adv_ids MUST NOT be labeled as the current active campaign slot.
`mv_clusters_last_state` (nmid×text) MAY appear only as separate product-level stream
— MUST NOT populate campaign current-state fields without proven linkage.

#### Scenario: mv_clusters_last_state not campaign authority

- **GIVEN** product-level MV has last_cpm for (nmid, text) without adv_id
- **WHEN** campaign current state exported for adv_id A
- **THEN** MV values MUST NOT be assigned as A's observed_cpm without strict-grain proof

#### Scenario: Rebound historical id not active campaign slot

- **GIVEN** rebound adv_id H has latest daily observation but current inventory slot uses adv_id A
- **WHEN** keyword_current_state exported
- **THEN** row for H MUST have `campaign_slot_role=REBOUND_HISTORICAL`
- **AND** MUST NOT present H as the shop's current active campaign identity

### Requirement: Bid decision log availability probe

Export MUST probe `bid_decision_log` read-only availability before attach.
Unavailable/empty scope → explicit `UNSUPPORTED` coverage; rows MUST remain
`DECISION` not `ACTION`.

#### Scenario: Empty bid_decision_log marked unsupported

- **GIVEN** bid_decision_log has zero rows for scope
- **WHEN** export completes
- **THEN** coverage MUST mark decision context `UNSUPPORTED`
- **AND** MUST NOT silently omit availability metadata

### Requirement: Distinct current bid vs reported CPM

Current-state MUST distinguish reported/stored CPM from current bid evidence where
sources differ; MUST NOT conflate without proven same semantics.

#### Scenario: Bid and CPM fields separate when sources differ

- **GIVEN** bid_decision_log cpm_curr and cluster last_cpm differ
- **WHEN** current state exported
- **THEN** fields MUST remain separate with source tags

### Requirement: Production writes none on export path

Export path MUST NOT perform WB API writes, PG writes, Redis writes, or
control-plane writes.

#### Scenario: Export read-only seam

- **WHEN** keyword export runs
- **THEN** no INSERT/UPDATE/DELETE on PG/Redis MUST occur
- **AND** no WB HTTP mutating calls MUST occur
