# Design — ai-package-keyword-performance-history

## Architecture Decision References

| Decision | Role in this change |
|---|---|
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` (Accepted) | Export in `ai_package_v1/`; READ_ONLY_NO_MUTATION; no WBShopDataManager |
| `openspec/decisions/shop-data-source-strategy/decision.md` (Accepted) | PG/CH accumulation read; four completeness dimensions |
| `openspec/decisions/clickhouse-sql-database-qualification/decision.md` (Accepted) | `default_db.<object>` qualification |
| Proposed: `decisions/ai-package-keyword-performance-history-ownership/decision.md` | Keyword scope reader, forbidden UI/Telegram sources, rebound Redis read |

Canonical specs consumed: `grain-preservation`, `coverage-provenance`,
`data-source-selection`, `ai-package-v1-exporter`, `ai-package-v1-contract-tests`.

## Ownership & Placement

| Concern | Owner | Layer | Notes |
|---|---|---|---|
| Keyword daily/windows/current/changes | This change | `app/modules/ai_package_v1/keyword_performance/` | Readers, assemblers, window engine |
| Export orchestration | Existing `ExportService` | `ai_package_v1/export/export_service.py` | Wire keyword payloads + cards; inject deps |
| PG inventory anchor | `PgExportShopScopeReader` pattern | `ai_package_v1/scope/` | Unchanged public DTO |
| Keyword scope + rebound | `KeywordExportScopeReader` | `ai_package_v1/keyword_performance/scope/` | Internal; PG PK + Redis read |
| DATA_MAP / coverage root files | Keyword assembler + domain | `ai_package_v1/keyword_performance/domain/` | Manifest file descriptors |
| ZIP encode/decode | Existing `encode_package` | `ai_package_v1/zip_transport/` | DATA_MAP in payloads list |
| Forbidden | UI managers, Telegram graph, shop-runner updaters | — | Read-only export only |

Checklist:

- [x] Context-first decision lookup performed.
- [x] Relevant decisions cited by path.
- [x] New decision proposed for keyword ownership/forbidden sources.
- [x] Implementation layer matches decision.

## Goals / Non-Goals

**Goals:**

- Одна deterministic AI Package выгрузка содержит canonical keyword daily facts,
  ready windows, current state, change deltas, coverage, DATA_MAP.
- Full available history from CH (not clipped by caller `ExportPeriod`).
- Strict grain, conservative spend, proven position types, rebound membership.
- Constructor-injected fake seams for unit tests; default `ExportService()` includes
  keyword datasets via real read-only assembler (same pattern as `settings_assembler`).

**Non-Goals:**

- WB writes, bid apply, collectors, PG/Redis writes, second exporter.
- Telegram/graph/UI rollup as source.
- AI labels or causal bid→position claims.

## Derived Lifecycle (export read path)

`LIFECYCLE_STATUS: DERIVED`

| Step | Behavior | SOURCE |
|---|---|---|
| L1 | Validate export inputs (`shop_id`, period bounds for non-keyword cards) | owner-contract D-012; `validate_export_inputs` |
| L2 | Load PG inventory scope (read-only) | owner-contract unchanged v1; `PgExportShopScopeReader` |
| L3 | Expand keyword scope: PG `AdvSetting.id` + rebound Redis membership → adv_id superset | owner-contract D-005; inventory report |
| L4 | Discover `first_available`/`last_available` per scope via CH MIN/MAX on `clusters_adv_stats.date` | owner-contract D-002, D-013 |
| L5 | Fetch/stream daily facts at strict grain (`argMax` rollup); emit coverage per row/day | owner-contract D-001, D-003, D-004 |
| L6 | Compute deterministic windows, current state, change deltas from daily facts | owner-contract D-007, D-008 |
| L7 | Assemble DATA_MAP + coverage.json; attach manifest cards + file descriptors; encode ZIP | owner-contract D-006; v1 manifest pattern |

## Semantic Write Target (read-path MEANING_LOCK)

```text
TARGET_ENTITY_OR_LEG: keyword_query_daily_fact @ clusters_adv_stats (physical adv_id grain)
ALLOWED_ADAPTERS:
  - ChKeywordDailyReader (clusters_adv_stats argMax daily rollup)
  - ChKeywordPositionReader (keyword_position_from_api / clusters_adv_stats avr_pos streams)
  - KeywordExportScopeReader (PG AdvSetting.id + Redis rebound read)
FORBIDDEN_ADAPTERS:
  - KeywordDailyHistoryManager / get_keyword_daily_history.sql (UI date rollup)
  - graphic_positions_creator / get_position_history.sql (synthetic fill)
  - get_clusters_stats.sql cross-adv_id aggregation as canonical daily authority
  - spend derived as CPM×views/1000 as factual spend_rub
EVIDENCE:
  - scripts/adv_bot_historical_state_extractor.py:1000-1018
  - inventory report FORBIDDEN paths
  - owner-contract D-001, D-003, D-004
PAIRED_TESTS:
  - scenario_seam: default ExportService() includes keyword cards (S29)
  - scenario_seam: export uses ChKeywordDailyReader not UI SQL (S09)
  - negative: Telegram graph module not imported on export path (S10)
  - unit: legacy tests inject fake keyword assembler explicitly (S34)
```

## Scope and identity model

### Internal DTO (keyword scope — not public ExportScopeAdv change)

```python
@dataclass(frozen=True)
class KeywordScopeRow:
    shop_id: str
    adv_setting_id: int          # PG AdvSetting.id — logical resource anchor
    auto_adv_id: int
    search_adv_id: int | None
    main_nmid: int | None
    rebound_auto_adv_ids: frozenset[int]   # membership only
    rebound_search_adv_ids: frozenset[int] # membership only (auction kind)
```

`KeywordExportScopeReader.load_keyword_scope(shop_id)`:

1. Reuse PG inventory rows from `PgExportShopScopeReader.load_scope` internally.
2. Map each row to `AdvSetting.id` via same inventory query (add `AdvSetting.id`
   to internal select — **not** added to `ExportScopeAdv`).
3. For each `adv_setting_id`, `await get_rebound_wb_adv_ids(adv_setting_id)`.
4. Build `all_adv_ids = {auto, search?, rebound_auto, rebound_search}` deduped.
5. Assign `leg_role` per adv_id: `AUTO` | `SEARCH` | `REBOUND_AUTO` |
   `REBOUND_SEARCH` when proven; if adv_id appears in both auto and search slots
   for same resource, emit `AMBIGUOUS_LEG` coverage (fail-closed row flag, no silent pick).
6. **Ownership validation (cross-shop / rebound overlap):** `adv_id IN expanded_set`
   alone is insufficient. Two independent probes are required:

   - **Requested-shop resource qualification:** for every `(adv_id, adv_setting_id)`
     assignment intended under the requested shop, validate against PG inventory
     (`PgExportShopScopeReader` / `AdvSetting` join
     `WBCabinet.shop_id == requested shop_id`). Rebound adv_ids MUST map to exactly
     one logical resource **for the requested shop** or be marked
     `AMBIGUOUS_OWNERSHIP` / `UNSUPPORTED` (fail-closed — no row emission under
     multiple logical IDs on that shop).
   - **Global adv_id overlap probe (mandatory):** run a read-only PG query for
     **all shops** that maps each expanded `adv_id` → `(shop_id, adv_setting_id)`
     rows via the same inventory join pattern. A requested-shop-only inventory query
     **MUST NOT** be claimed as proof of global ownership isolation. If an adv_id
     appears under more than one shop, or under a foreign shop without a proven
     resource-qualified rebound anchor for the requested shop, mark
     `AMBIGUOUS_OWNERSHIP` / `FOREIGN_SHOP_ADV_ID` and fail-closed (no silent
     reassignment). Coverage MUST record `ownership_evidence_scope`:
     `REQUESTED_SHOP_PG_PLUS_GLOBAL_ADV_ID_OVERLAP` — not `REQUESTED_SHOP_ONLY`.
   - **Trusted historical membership:** rebound adv_ids MAY emit daily/historical
     rows only when Redis membership + requested-shop `adv_setting_id` anchor are
     both proven; global overlap probe confirms no conflicting foreign-shop owner.
     No fabricated historical interval and no requirement to scan production CH —
     PG overlap uses existing inventory joins only.

   Apply `nmid` constraints from inventory (`main_nmid`) where proven; when CH row
   nmid ∉ proven resource nmids, flag `AMBIGUOUS_NMID` rather than reassign.
   Preserve unassigned historical provenance: physical `adv_id` stays on the row;
   do **not** synthesize ownership when PG mapping is absent — emit coverage
   `UNASSIGNED_PROVENANCE` and omit `adv_setting_id` only when truly unmapped
   (never guess shop/resource from adv_id alone).

**Rebind semantics (D-005):** rebound sets prove **membership only**; export rows
retain physical `adv_id` on each daily fact; no guessed transition dates.

**Auto/Search (D-001):** separate rows per physical adv_id; no silent merge across
Auto shelf and Search keywords campaigns.

## Time semantics (D-011 — resolved from evidence)

| Concept | Resolution | Evidence |
|---|---|---|
| Source `date` column | CH `Date` on `clusters_adv_stats.date`; populated from WB `NormqueryStatsDTO.day` at ingest (`convertor.py:26-41`) — **opaque calendar day key** | `destructive_ch_reset.py:75`; ingest path |
| `source_calendar_timezone` | **`UNKNOWN`** — repo does not prove WB reporting-day TZ for `NormqueryStatsDTO.day`; MUST NOT label CH rows as UTC/Moscow solely from package timestamp | ingest uses `stat_dto.day` without TZ conversion |
| Package calculation TZ | **`UTC`** for `manifest.generated_at`, `package_cutoff_date`, `last_closed_calendar_day`, and all window boundary math | `export_service.py:243-245` |
| Package cutoff (stable) | Parse `generated_at` as ISO-8601 UTC → `package_cutoff_instant = generated_at` (UTC `DateTime`) and `package_cutoff_date = UTC date(generated_at)`. **Every** keyword source filter MUST apply both where temporal semantics allow (see per-source row below). | fail-closed: exclude future dates and same-day post-instant rows |
| Per-source cutoff semantics | **`clusters_adv_stats`:** `date <= package_cutoff_date` **AND** `timestamp <= package_cutoff_instant` (proven `DateTime` ingest stamp — `destructive_ch_reset.py:77`). **`bid_decision_log`:** `decision_time <= package_cutoff_instant`; when `stats_max_timestamp` present, also `stats_max_timestamp <= package_cutoff_instant`. **`keyword_position_from_api`:** `date <= package_cutoff_date` **AND** `version <= cutoff_instant_ms` where `version UInt64` is **proven UTC epoch milliseconds** at ingest (`click_house_manager.update_positions:88` sets `version = int(time.time() * 1000)` per batch). CH filter: `version <= toUInt64(toUnixTimestamp64Milli(toDateTime64({package_cutoff_instant}, 3, 'UTC')))`. Assembler param `{cutoff_instant_ms}` = same conversion in Python. Rows with unproven version lineage (backfill without writer audit) → date-only fallback + `UNKNOWN_VERSION_TIME_SEMANTICS` in coverage — **MUST NOT** label current writer path `SAME_DAY_INSTANT_UNSUPPORTED`. | code-proven ms cutoff; no guessed capture timestamp |
| `first_available` / `last_available` | **Per source independently:** `MIN(date)`, `MAX(date)` on each object with that object's cutoff filters (daily bounds from `clusters_adv_stats`; position bounds from `keyword_position_from_api`; decision bounds from `bid_decision_log`). Package-level bounds in coverage = union/intersection documented in DATA_MAP — **MUST NOT** reuse cluster `first_available` as position history lower bound. `last_available` MUST NOT include future source dates even if present in CH | Owner D-002, D-013 |
| Source day closure | **Not proven** — export MUST NOT assert CH `date` keys represent "closed UTC days"; document limitation in DATA_MAP (`source_period_closure: UNKNOWN`) | no stat_date/TZ proof in DDL |
| `last_closed_calendar_day` | `(package_cutoff_date UTC) - 1 calendar day` — used **only** for package-side window/freshness anchors, not as proof that source day D is closed in WB reporting TZ | package-side convention |
| Rolling windows (1d, 7d, 365d) | End = `last_closed_calendar_day`; start = end − (N−1) UTC calendar days inclusive | Owner D-007 |
| OPEN MTD/QTD/YTD | UTC calendar boundaries ending at `last_closed_calendar_day`: MTD = UTC month start → end; QTD = UTC quarter start → end; YTD = UTC Jan 1 → end | distinct from rolling |
| Calendar year windows | Fixed UTC calendar year (Jan 1–Dec 31); distinct from rolling 365d | Owner D-007 |
| Comparable previous MTD/QTD/YTD | **Elapsed-day aligned (UTC):** comparable end = same ordinal day in previous month/quarter/year, capped by that period's length (leap-year safe: Feb 29 → Feb 28 prev year). Example: if `last_closed_calendar_day = 2026-03-15`, comparable prev MTD = 2026-02-01..2026-02-15; if end = 2026-03-31, comparable prev MTD = 2026-02-01..2026-02-28/29 | DATA_MAP MUST document formula |
| First-day boundaries | Month/quarter/year windows include their first UTC calendar day when `last_closed_calendar_day` falls inside the period; when `last_closed_calendar_day` precedes period start, window is empty/partial with explicit coverage | deterministic |
| ExportPeriod vs keyword history | Keyword datasets use `[first_available, last_available]` (≤ cutoff); `manifest.period` applies to legacy cards only | Owner D-002 |

## Daily snapshot selection (row-coherent / fail-closed)

**DDL evidence (`destructive_ch_reset.py:62-81`):** `clusters_adv_stats` has
`timestamp DateTime`, `spend Nullable(Float64)`, **no** `ingest_sequence` or row
`version`. Per-field `argMax(spend, timestamp)` (and other nullable metrics) is
**forbidden** — it can pick spend from an older row while views/clicks come from
a newer row at the same calendar date.

**Required pattern — row-coherent latest snapshot:**

1. Within `(adv_id, nmid, norm_query, date)`, compute `last_snapshot_ts = max(timestamp)`.
2. Consider all source rows with `timestamp = last_snapshot_ts`.
3. If all rows share an **identical** metric tuple `(views, clicks, add_to_cart,
   orders, spend, cpm, cpc, avr_pos, ctr)` → emit that tuple (duplicate-identical
   collapse).
4. If rows at `last_snapshot_ts` disagree on any metric → **fail-closed:**
   `collection_outcome=AMBIGUOUS`, `reason_codes` includes `SNAPSHOT_CONFLICT`,
   affected metric fields `null` (hashing/`cityHash64` MAY order serialization for
   tests but MUST NOT pick an arbitrary conflicting factual value).

**SQL template** (valid two-stage CTE — implement in
`keyword_daily_from_clusters.sql` + assembler validation). No nested aggregate inside
`uniqExactIf`; no `ifNull(..., -1)` sentinel (distinct nullable shapes MUST remain
distinct); no `argMax` on ties — conflict path MUST be reachable:

```sql
WITH latest_ts AS (
    SELECT
        adv_id,
        nmid,
        norm_query,
        date,
        max(timestamp) AS last_snapshot_ts
    FROM default_db.clusters_adv_stats
    WHERE adv_id IN {adv_ids}
      AND date >= {first_available}
      AND date <= {package_cutoff_date}
      AND timestamp <= {package_cutoff_instant}
    GROUP BY adv_id, nmid, norm_query, date
),
rows_at_latest AS (
    SELECT
        s.adv_id,
        s.nmid,
        s.norm_query,
        s.date,
        lt.last_snapshot_ts,
        s.views,
        s.clicks,
        s.add_to_cart,
        s.orders,
        s.spend,
        s.cpm,
        s.cpc,
        s.avr_pos,
        s.ctr
    FROM default_db.clusters_adv_stats AS s
    INNER JOIN latest_ts AS lt
        ON s.adv_id = lt.adv_id
       AND s.nmid = lt.nmid
       AND s.norm_query = lt.norm_query
       AND s.date = lt.date
       AND s.timestamp = lt.last_snapshot_ts
    WHERE s.timestamp <= {package_cutoff_instant}
)
SELECT
    adv_id,
    nmid,
    norm_query,
    date,
    last_snapshot_ts,
    uniqExact(
        (views, clicks, add_to_cart, orders, spend, cpm, cpc, avr_pos, ctr)
    ) AS snapshot_variants_at_max_ts,
    any(
        (views, clicks, add_to_cart, orders, spend, cpm, cpc, avr_pos, ctr)
    ) AS snapshot_tuple
FROM rows_at_latest
GROUP BY adv_id, nmid, norm_query, date, last_snapshot_ts
```

Assembler: when `snapshot_variants_at_max_ts > 1` → AMBIGUOUS row (`SNAPSHOT_CONFLICT`);
**MUST NOT** unpack `snapshot_tuple` ( `any()` is non-deterministic on conflicts).
When `= 1`, identical duplicate rows collapse; unpack tuple once. Unit tests MUST
cover conflicting same-timestamp fixtures (S25) and identical-duplicate collapse (S43).

## Source queries (read-only lineage)

### Daily facts — `ChKeywordDailyReader`

Primary SQL: row-coherent template above (`keyword_daily_from_clusters.sql`).
All date filters use `{package_cutoff_date}`, not unbounded `last_available`.

Enrichment per row (assembler, not SQL rollup):

- Join keyword scope for `shop_id`, `adv_setting_id`, `leg_role` after ownership
  validation (see Scope model).
- **`raw_query`:** MUST be `null` with `raw_query_status=RAW_QUERY_UNAVAILABLE`
  when no distinct source-proven raw-text column exists on the CH row. **`norm_query`
  MUST NOT be copied into `raw_query`.** Do **not** join PG `keyword_setting.text`
  (or any PG text) as source raw without proven 1:1 correspondence — collision
  or unproven mapping → `AMBIGUOUS_QUERY_IDENTITY` in coverage, `raw_query` stays
  null. Persisted normalized string remains `norm_query` as stored (no re-normalization).
- `spend_rub` + `query_spend_status`: `FACTUAL` only when snapshot tuple `spend IS NOT NULL`
  with ingest lineage; else `null` + `UNAVAILABLE`. Never UI CPM formula.
- `cpc`: from snapshot tuple when non-null; else null + coverage.
- Derived metrics (CTR, conversions, CPO): deterministic; ratios in **0..1** (not percent);
  null when denominator missing/zero; document in DATA_MAP.
- JSON numbers MUST be finite (`null` for missing/non-finite — no `NaN`/`Infinity`).
- `position_observations[]`: optional embedded or split dataset — see positions.

### Earliest / latest discovery (per source)

**Daily facts (`clusters_adv_stats`):**

```sql
SELECT min(date) AS first_available, max(date) AS last_available
FROM default_db.clusters_adv_stats
WHERE adv_id IN {adv_ids}
  AND date <= {package_cutoff_date}
  AND timestamp <= {package_cutoff_instant}
```

**WB keyword positions (`keyword_position_from_api`) — independent bounds:**

```sql
SELECT min(date) AS position_first_available, max(date) AS position_last_available
FROM default_db.keyword_position_from_api
WHERE nmid IN {nmids}
  AND date <= {package_cutoff_date}
  AND version <= {cutoff_instant_ms}
```

Position read SQL MUST use `{position_first_available}` / `{position_last_available}`
from this probe — **MUST NOT** inherit cluster `{first_available}` (older position
history may predate cluster stats).

Per-resource optional MIN/MAX for coverage granularity in `coverage.json`.

### Positions — separate stream (`keyword_positions.jsonl`)

| Source | position_type | Grain | Safe read shape |
|---|---|---|---|
| `clusters_adv_stats.avr_pos` | `CLUSTER_AVG_POS` | `adv_id × nmid × norm_query × date` | from daily snapshot tuple |
| `keyword_position_from_api.avr_position` | `WB_KEYWORD_POSITION_API` | `nmid × text × date` | see SQL below |

**WB keyword position API (proven DDL — `conftest.py.bak:255-267`, ReplacingMergeTree):**
columns `nmid Int32`, `text String`, `avr_position Float32`, `total_views Int32`,
`orders Int32`, `date Date`, `version UInt64`. **Version lineage (proven writer):**
`click_house_manager.update_positions` sets `version = int(time.time() * 1000)` —
UTC epoch milliseconds at batch insert; **not** a separate monotonic sequence label.
Cutoff: `date <= package_cutoff_date` **AND** `version <= {cutoff_instant_ms}` where
`{cutoff_instant_ms} = int(generated_at.timestamp() * 1000)` (UTC) matching CH
`toUInt64(toUnixTimestamp64Milli(toDateTime64({package_cutoff_instant}, 3, 'UTC')))`.
Do **not** invent capture timestamps beyond this conversion.

```sql
SELECT
    nmid,
    text,
    date,
    argMax(avr_position, version) AS avr_position,
    argMax(total_views, version) AS total_views,
    argMax(orders, version) AS orders
FROM default_db.keyword_position_from_api
WHERE nmid IN {nmids}
  AND date >= {position_first_available}
  AND date <= {package_cutoff_date}
  AND version <= {cutoff_instant_ms}
GROUP BY nmid, text, date
```

`text` is source column name; export `norm_query` only when proven equal to
`clusters_adv_stats.norm_query` for same `(nmid, date)` — otherwise keep separate
`source_query_text` field and mark join `AMBIGUOUS`/`UNSUPPORTED`. No unsafe
many-to-many campaign assignment (D-010). Missing position → absent row or explicit
`missing` coverage — never `0`, never `max_pos`.

### Current state — `ChKeywordCurrentStateReader`

**Campaign-scoped current state** MUST use strict grain latest daily/intraday
records from `clusters_adv_stats` at `(adv_id, nmid, norm_query)` — same
row-coherent snapshot rules as daily reader, keyed by max `(date, last_snapshot_ts)`
with `timestamp <= package_cutoff_instant`.

**Active vs historical campaign slot labeling (D-001 / D-005):** each row MUST
carry `campaign_slot_role`:

| `leg_role` / adv_id provenance | `campaign_slot_role` | Semantics |
|---|---|---|
| AUTO or SEARCH from current inventory slots | `ACTIVE` | Current active campaign identity for export |
| REBOUND_AUTO / REBOUND_SEARCH physical ids | `REBOUND_HISTORICAL` | Last-observed historical evidence only — **MUST NOT** be presented as the shop's current active campaign slot |
| Ambiguous leg assignment | `AMBIGUOUS` | fail-closed; no silent ACTIVE label |

Historical rebound physical ids MUST NOT populate "current active campaign" identity
fields; they MAY appear as `last_observed_historical` evidence block with physical
`adv_id` preserved.

**`mv_clusters_last_state`** (grain `nmid × text`, no `adv_id` —
`destructive_ch_reset.py:285-307`) is a **separate product-level stream** with its
own identity. It MAY populate optional `product_last_state` observations but MUST
NOT be assigned to campaign current-state rows without proven `(adv_id, nmid,
norm_query)` linkage — no unsafe assignment.

Deterministic pick per `(adv_id, nmid, norm_query)` identity: max
`(observation_date, observation_ts)` lexicographic among rows with
`campaign_slot_role IN (ACTIVE, REBOUND_HISTORICAL)` as separate emitted rows —
ACTIVE rows MUST NOT subsume REBOUND_HISTORICAL ids; ties use same snapshot conflict
rules.

Fields MUST distinguish:

- `campaign_slot_role` — ACTIVE / REBOUND_HISTORICAL / AMBIGUOUS (required)
- `observed_cpm` — from cluster daily snapshot / `mv_clusters_last_state` with source tag
- `current_bid_evidence` — from PG strategy/bid fields when proven
- `decision_cpm_curr` — from `bid_decision_log` labeled `DECISION`, never `ACTION`

### Bid/decision context (read-only availability probe)

At export, probe `bid_decision_log` read-only (pattern:
`adv_bot_historical_state_extractor.export_bid_decision_log` coverage query) before
attach. When table empty/unavailable for scope → `coverage.json` marks dataset
`UNSUPPORTED` (not silent omit). When present, read rows with `event_class=DECISION`;
fields include `cpm_curr`, `pos_*`, `decision_time`, `final_bid`. Filter
`decision_time <= package_cutoff_instant` (and `stats_max_timestamp <=
package_cutoff_instant` when column populated). Join only on exact
`(adv_id, nmid, norm_query)`; derived pipeline rows MUST NOT be labeled `ACTION`.

## Dataset schemas (logical v1)

### Source matrix (exact v1)

| Field / metric | Source object.column | Units | Coverage when absent |
|---|---|---|---|
| views, clicks, add_to_cart, orders | `clusters_adv_stats.*` snapshot tuple | counts | `missing` — not zero |
| spend_rub | `clusters_adv_stats.spend` | RUB | `UNAVAILABLE` if null |
| cpm, cpc | `clusters_adv_stats.cpm/cpc` | RUB | null + per-field coverage |
| ctr | derived clicks/views | ratio 0..1 | null if views=0/missing |
| conv_* | derived from counts | ratio 0..1 | null if denominator zero/missing |
| cpo_rub | spend/orders | RUB | null unless spend FACTUAL & orders>0 |
| cluster_avg_pos | `clusters_adv_stats.avr_pos` | rank (lower=better) | null, not 0/max |
| wb_keyword_position | `keyword_position_from_api.avr_position` | rank | separate stream |
| raw_query | **none proven** | text | `RAW_QUERY_UNAVAILABLE` → null |
| norm_query | `clusters_adv_stats.norm_query` | text | required key |
| strategy/status | PG `AdvSetting` columns | enum/text | `UNSUPPORTED` if unmapped |
| observed_cpm | cluster snapshot / product MV | RUB | source-tagged |
| current_bid_evidence | PG when proven | RUB | distinct from observed_cpm |
| decision_cpm_curr | `bid_decision_log.cpm_curr` | RUB | `DECISION` class only |
| relative_delta | window math | ratio | null if previous=0/missing |
| pp_delta (rates) | window math | ratio points | null if undefined |

All JSON numeric fields MUST be finite or null.

### `keyword_daily.jsonl` — `KeywordDailyRowV1`

| Field | Type | Notes |
|---|---|---|
| schema_version | string | `1.0.0` |
| shop_id | int | manifest shop |
| adv_setting_id | int? | PG PK when ownership proven; null + coverage when unassigned |
| adv_id | int | physical |
| leg_role | enum | AUTO/SEARCH/REBOUND_* / AMBIGUOUS |
| nmid | int | |
| norm_query | string | persisted normalized key (as stored) |
| raw_query | string? | **null** unless distinct source raw proven |
| raw_query_status | enum | `PROVEN` / `RAW_QUERY_UNAVAILABLE` / `AMBIGUOUS` |
| date | string | ISO date (CH opaque source day key) |
| views, clicks, add_to_cart, orders | int? | null = missing/not observed |
| spend_rub | float? | factual only |
| query_spend_status | enum | FACTUAL/DERIVED_VALID/ESTIMATE_ONLY/UNAVAILABLE |
| cpm, cpc | float? | from snapshot tuple |
| ctr | float? | ratio 0..1: clicks/views when views>0 |
| conv_views_to_cart, conv_cart_to_order, conv_views_to_order | float? | ratios 0..1 |
| cpo_rub | float? | only when spend FACTUAL & orders>0 |
| cluster_avg_pos | float? | position_type CLUSTER_AVG_POS |
| snapshot_status | enum | `OK` / `AMBIGUOUS` (`SNAPSHOT_CONFLICT`) |
| source | string | `clusters_adv_stats` |
| row_coverage | object | per-metric observed/missing/reason |

### `keyword_windows.jsonl` — `KeywordWindowRowV1`

| Field | Type | Notes |
|---|---|---|
| schema_version | string | `1.0.0` |
| shop_id, adv_setting_id, adv_id, leg_role, nmid, norm_query | identity | same grain as daily |
| window_id | enum | catalog id (`last_7d`, `month_to_date`, `all_available`, …) |
| window_start, window_end | string | ISO dates (UTC package calendar) |
| comparator_kind | enum | `NONE` / `PREVIOUS_PERIOD` / `PREVIOUS_CALENDAR` |
| observed_days, missing_days, requested_days | int | required coverage counts |
| coverage.partial | bool | true when history shorter than window |
| views_sum, clicks_sum, add_to_cart_sum, orders_sum | int? | sum over observed days only |
| spend_rub_sum | float? | null unless all observed days have FACTUAL spend |
| spend_status | enum | `FACTUAL` / `PARTIAL_UNAVAILABLE` / `UNAVAILABLE` |
| ctr | float? | sum(clicks)/sum(views); null when views_sum=0 or missing |
| conv_views_to_cart, conv_cart_to_order, conv_views_to_order | float? | ratio of sums; null when denominator zero/missing |
| cpo_rub | float? | spend_rub_sum/orders_sum when spend FACTUAL & orders_sum>0 |
| cluster_avg_pos_mean | float? | **weighted mean** by `views_sum` per day when views>0; null when no observed positions |
| cluster_avg_pos_median | float? | optional; unweighted median of daily positions when any observed |
| position_observed_days | int | days with non-null cluster_avg_pos |
| window_coverage | object | per-metric observed/missing/reason |

Window rates = **ratios of sums** over observed days (not average of daily rates).
Economics columns null when any day lacks FACTUAL spend unless DATA_MAP documents
partial economics — default fail-closed.

### `keyword_current_state.jsonl` — `KeywordCurrentStateRowV1`

| Field | Type | Notes |
|---|---|---|
| schema_version | string | `1.0.0` |
| shop_id, adv_setting_id, adv_id, leg_role, nmid, norm_query | identity | strict grain |
| campaign_slot_role | enum | `ACTIVE` / `REBOUND_HISTORICAL` / `AMBIGUOUS` |
| observation_date, observation_ts | string | from winning daily snapshot (≤ cutoff instant) |
| freshness_status | enum | `FRESH` / `STALE` / `UNKNOWN` vs `package_cutoff_instant` |
| views, clicks, orders, spend_rub, cpm, cpc, ctr, cluster_avg_pos | metrics? | from row-coherent snapshot |
| observed_cpm | float? | source-tagged (`clusters_adv_stats` or `mv_clusters_last_state`) |
| current_bid_evidence | float? | PG bid/strategy when proven — distinct from observed_cpm |
| decision_cpm_curr | float? | `bid_decision_log.cpm_curr`, `DECISION` class only |
| strategy_status | string? | PG when proven |
| last_observed_historical | object? | present when `campaign_slot_role=REBOUND_HISTORICAL` — physical adv_id evidence |
| product_last_state | object? | optional `(nmid, norm_query)` MV stream — not campaign authority |
| row_coverage | object | per-field status |

Latest observation per **campaign identity** `(adv_id, nmid, norm_query)`; ACTIVE
and REBOUND_HISTORICAL ids emit as **separate rows** — historical ids MUST NOT
appear as current active campaign identity.

### `keyword_changes.jsonl` — `KeywordChangeRowV1`

| Field | Type | Notes |
|---|---|---|
| schema_version | string | `1.0.0` |
| shop_id, adv_setting_id, adv_id, leg_role, nmid, norm_query | identity | strict grain |
| change_id | enum | `7d_vs_prev7d`, `30d_vs_prev30d`, `mtd_vs_prev_mtd`, … |
| current_window_id, previous_window_id | enum | catalog cross-reference |
| current_start, current_end, previous_start, previous_end | string | ISO bounds (comparator-aligned) |
| metric_name | enum | traffic/funnel/economics/ranking field being compared |
| current_value, previous_value | float? | null when side undefined |
| absolute_delta | float? | current − previous when both defined |
| relative_delta | float? | (current − previous) / previous; **null when previous=0 or missing** |
| pp_delta | float? | percentage-point delta for rates; **null when undefined** |
| ranking_delta | float? | position_end − position_start convention (negative = improvement) |
| spend_status_current, spend_status_previous | enum | FACTUAL / UNAVAILABLE / PARTIAL |
| coverage_current, coverage_previous | object | observed_days, partial flags per side |
| row_coverage | object | fail-closed when either side ambiguous |

Comparisons MUST NOT emit AI recommendation labels. Zero denominators → null deltas,
never fabricated infinity.

### `coverage.json` — package-level + per-dataset

Dimensions: requested, returned, observed, missing, confirmed_zero, unsupported,
failed, first_available, last_available, retrieved_at, freshness, coverage_pct.
Reuse v1 enums from `coverage_rules.py`.

### `DATA_MAP.json`

Root document per Owner §18: per-dataset grain, PK, join keys, timezone evidence,
units, formulas, position direction (**lower = better**;
`position_delta = position_end - position_start` so negative delta = improvement),
missing vs zero, window catalog, ExportPeriod vs all_available bounds,
calculation_version, limitations.

**Manifest integration:** `DATA_MAP.json` and `coverage.json` are `DomainPayload`
entries; `build_file_descriptors` includes their sha256 in manifest; validator
MUST verify tamper — existing `validate_zip_package` extended for new files.

DATA_MAP MUST document: `source_calendar_timezone: UNKNOWN`,
`package_calculation_timezone: UTC`, `package_cutoff_date`, `package_cutoff_instant`,
per-source cutoff semantics (`timestamp` vs `version` ms epoch vs `UNKNOWN_VERSION_TIME_SEMANTICS`),
comparable window formulas (MTD/QTD/YTD elapsed-day alignment), ratio vs percent units,
finite JSON rule, `raw_query` unavailable semantics, `campaign_slot_role` labeling,
`ownership_evidence_scope`, campaign vs product stream grains.

## Window engine

Module: `keyword_performance/windows/engine.py`

Inputs: in-memory stream or chunked iterator of `KeywordDailyRowV1`, scope metadata,
`first_available`, `last_available`, `package_cutoff_date`, `last_closed_calendar_day`.

Catalog (Owner D-007):

- Rolling closed: `1d`, `3d`, `7d`, `14d`, `30d`, `90d`, `180d`, `365d`
- Calendar open-to-closed: `month_to_date`, `previous_month`, `quarter_to_date`,
  `previous_quarter`, `year_to_date`, `previous_year`, `year_before_previous`
- `all_available`
- Comparables: `3d_vs_prev_3d`, …, `365d_vs_prev_365d`, MTD/QTD/YTD vs comparable previous

Partial coverage when history shorter than window — emit window row with
`coverage.partial=true`, `requested_days` vs `observed_days`.

**Economics:** spend/CPO columns null when any day in window lacks FACTUAL spend
unless DATA_MAP documents partial economics with explicit denominator — default
fail-closed: no misleading complete spend.

## Volume / fetch model

Avoid unbounded N+1:

1. Single CH query (or batched by year partition) for daily facts per adv_id superset.
2. Stream rows → JSONL encoder (chunk flush by year or 50k rows).
3. Window engine consumes sorted merge iterator (by identity, date).
4. Physical chunks: `keyword_performance/keyword_daily_2024.jsonl` allowed; DATA_MAP
   lists logical dataset `keyword_daily` with `physical_files[]`.

Upper bound guard: configurable `KEYWORD_EXPORT_MAX_ROWS` env (default unset = no
 artificial clip); if exceeded, fail with `VOLUME_LIMIT_EXCEEDED` not silent truncate.

## ExportService integration

Extend `ExportService.__init__` with optional deps (same default-build pattern as
`settings_assembler` — `export_service.py:93-98`):

- `keyword_scope_reader: KeywordExportScopeReader | None = None`
- `keyword_assembler: KeywordPerformanceAssembler | None = None`

Default wiring when params omitted:

```python
if keyword_assembler is not None:
    self._keyword_assembler = keyword_assembler
else:
    self._keyword_assembler = KeywordPerformanceAssembler(
        scope_reader=self._keyword_scope_reader or KeywordExportScopeReader(),
        # real read-only CH/PG/Redis readers inside assembler
    )
```

**Default export includes keyword datasets** using real read-only assembler (Owner
"one export enough"). Production `ExportService()` MUST emit keyword family cards
and payloads when scope/history exists.

**Unit/regression tests** that must avoid live CH/Redis MUST inject explicit fakes
(`KeywordPerformanceAssembler` stub or `_NoOpKeywordAssembler`) — same obligation
as tests that inject fake `CampaignSettingsAssembler` today
(`test_export_settings_integration.py`). Existing integration tests in scope MUST
be updated at apply to inject keyword fakes; silent omission/DISABLED is forbidden.

Pipeline in `_export_with_scope` after settings snapshot block (~line 226):

1. After existing scope load, run keyword scope expansion + ownership validation.
2. Run keyword pipeline L4–L7; append payloads under `keyword_performance/...`.
3. Add dataset cards with four dimensions independent per keyword family card.

## Risks / Trade-offs

- [Volume] Full history large → chunked fetch + JSONL partition (mitigated D-002).
- [norm_query collision] → AMBIGUOUS coverage flag (mitigated).
- [Spend NULL common] → conservative null (mitigated D-003).
- [Redis unavailable] → export continues with current adv_ids only; coverage
  `REBOUND_IDS_UNAVAILABLE` (not silent omit of documented rebound requirement).

## Migration Plan

Apply-only: add module, wire ExportService default assembler, extend validator,
update existing ExportService tests to inject keyword fakes, add contract tests.
No DDL. Ops-only emergency rollback via env kill-switch permitted but MUST NOT be
default-off in production wiring.

## Open Questions

- none blocking planning (DDL inspected: no `ingest_sequence` on `clusters_adv_stats`;
  row-coherent snapshot rules above are authoritative).

## DESIGN_READINESS

```text
DESIGN_READINESS

PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none

DESIGN_STATUS: READY
REASON: none
```

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
