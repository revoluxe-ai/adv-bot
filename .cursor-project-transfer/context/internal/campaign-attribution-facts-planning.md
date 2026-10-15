---
cursor:
  subagentId: "bc-46efa5c9-3468-5b4a-b622-3568beff7e08"
---

# CAMPAIGN_ATTRIBUTION_FACTS_PLANNING_REPORT

Read-only planning for canonical storage of granular campaign attribution from WB `/adv/v3/fullstats`. No product code, migration, branch, commit, or production write was made.

`nm.orders` / `nm.sum_price` are aggregated counts and money at grain `advertId × day × appType × nmId`. They are not individual orders. The generated models do not carry `order_id`, basket id, or an order timestamp.

## Baseline and PR #451

`git fetch origin` then `git rev-parse HEAD` and `git rev-parse origin/stage` both return `1443649281543bc00411d9940a047037ed6d3ffd`. Working tree is `stage...origin/stage` with that commit: `chore(openspec): archive ai-package-full-export-contract-repair`.

PR #451 is OPEN, `mergedAt: null`, title `revert: undo unauthorized ai-package contract repair on stage`, head `cursor/revert-unauthorized-package-archive-a089`. It reverts three stage commits in reverse order so the tree would match `23c0671f372f0435b13a3573ec8990b4303b3e4a` for the files they touched:

- `144364928` archive chore of `ai-package-full-export-contract-repair`
- `8026a18eb` docs fix for archive validation
- `cfa8f4f74` feat adding `PACKAGE_SUMMARY` and canonical family status

The PR body says those commits were fast-forwarded onto `stage` without a PR, and that the authorized repair path remains draft PR #450. Do not open an implementation change until that deviation is off `origin/stage`.

## Token block

```text
BASELINE_SHA: 1443649281543bc00411d9940a047037ed6d3ffd
FULLSTATS_ACTUAL_GRAIN: advertId -> day.date -> apps[].appType -> nm[].nmId (aggregated metrics; not order identity). Typed on POST /adv/v2 DaysItem*. GET /adv/v3 FullStatsItem.days is Any and is collapsed to advertId+date before ClickHouse.
AVAILABLE_SOURCE_FIELDS: advertId, views, clicks, sum, atbs, orders, shks, sum_price, ctr, cpc, cr, date (day bucket), appType, nmId, name; campaign-level canceled and boosterStats. Nested day/app/nm models do not declare canceled.
ORDER_ID_AVAILABLE: NO
EXACT_ORDER_TIME_AVAILABLE: NO
BASKET_EVENT_ID_AVAILABLE: NO
EXPLICIT_ASSOCIATED_FLAG_AVAILABLE: NO
SOURCE_NM_ID_AVAILABLE: NO
CURRENT_DATA_LOSS_POINT: mapper _days_to_day_stats drops apps/nm; DayStats.apps is commented out; full_adv_wb_stat insert persists only (adv_id, date)
EXISTING_REUSABLE_COMPONENTS: FullstatsAdapter + raw FullStatsItem.days dicts; campaign_settings_history payload identity.nmids; full_adv_wb_stat argMax(version) latest read; campaign_settings_history hash-skip append; shop_campaign_inventory current nm_ids (not historical SoT); ComplexAdv.auto_adv_id/search_adv_id
PROPOSED_FACT_GRAIN: shop_id + adv_id + date + app_type + nmid
PROPOSED_STORAGE: append-only MergeTree observation (candidate default_db.full_adv_nm_stat) plus argMax latest projection; identical payload hash does not append. Not ReplacingMergeTree-only.
REVISION_SEMANTICS: append-only observations; latest row per grain via argMax(metric, observed_at); skip insert when canonical metric hash equals latest hash; a changed WB restatement appends and becomes latest; prior rows stay
ATTRIBUTION_CLASSIFICATION: PROMOTED_PRODUCT if attributed nmid is in as-of settings membership; ASSOCIATED_PRODUCT if membership is non-empty and nmid is outside it; UNKNOWN if no covering snapshot. views==0 is not the discriminator.
HISTORICAL_CAMPAIGN_MEMBERSHIP: REUSE_EXISTING
CAMPAIGN_LEVEL_RECONCILIATION: for each (adv_id, date), SUM nm orders/sum_price/atbs across all appType must equal day totals, and SUM of day totals must equal campaign-window totals. Mismatch or missing apps/nm => coverage != COMPLETE.
AUTO_SEARCH_JOIN_MODEL: fact.adv_id = ComplexAdv.auto_adv_id for AUTO and fact.adv_id = ComplexAdv.search_adv_id for SEARCH. No cross-leg fallback. Spend numerator stays argMax spend on full_adv_wb_stat. Attributed orders and GMV come from the nm fact only when coverage is COMPLETE.
MISSING_ZERO_SEMANTICS: missing or contradictory nm detail is not zero. Downstream attributed DRR/CPO must fail closed.
FULL_AI_PACKAGE_IMPACT: campaign_advertising exports CAMPAIGN_FULL_STAT at adv_id+date (views/clicks only). Nm attribution is not in the v1 ZIP or family-gap catalog. Do not merge Auto and Search into that CSV.
CONFLICTS_WITH_ACTIVE_CHANGES: PR #451 unmerged stage deviation blocks implementation. separate-auto-search-cpo is not on stage (branch only; its design forbids an attribution table inside that change). Active owner-bot-read-only-evidence-plane-stability normalizes fullstats dict shape and defers an attribution catalog. inc-ro-08 forbids treating fullstats orders as supplier ORDERS.
OWNER_DECISIONS_REQUIRED: restore clean stage before any change; accept pair-level settings nmids as membership (or require a WB nm_settings history extension); keep campaign spend as CPO/DRR numerator; reviewed ClickHouse corpus decision before any new migration (accepted registry stops at 006; 007 is already in code/tests); do not switch existing leg CPO denominator until coverage is COMPLETE.
IMPLEMENTATION_READY: NO
PRODUCT_CODE_CHANGED: NO
PRODUCTION_WRITES: NONE
FINAL_STATUS: PLANNING_READY
```

## 1. Generated fullstats model fields

GET `/adv/v3/fullstats` parses `list[FullStatsItem]` in `app/core/mp/wb/api/generated/promotion/v1/marketing_and_promotions_client/api/statistics/get_adv_v3_fullstats.py`. `FullStatsItem` (`models/full_stats_item.py`) declares campaign-period fields: `advertId`, `atbs`, `canceled`, `clicks`, `cpc`, `cr`, `ctr`, `days` typed `Any` ("Statistics by days"), `orders`, `shks`, `sum`, `sum_price`, `views`, optional `boosterStats`. There is no `orderId`, basket id, associated flag, or source nm.

The nested chain exists in the same generated package but is bound to POST `/adv/v2/fullstats`, not to `FullStatsItem`:

- `ResponseWithIntervalItem` and `ResponseWithDateType0Item` use `days: list[DaysItem]`.
- `DaysItem` (`days_item.py`): `date` (`datetime`), `views`, `clicks`, `ctr`, `cpc`, `sum`, `atbs`, `orders`, `cr`, `shks`, `sum_price`, `apps`. No `canceled`.
- `DaysItemAppsItem`: same metrics plus `nm` and `appType` (`1` website, `32` Android, `64` iOS). JSON key is `nm`, not `nms`. No `canceled`.
- `DaysItemAppsItemNmItem`: same metrics plus `name` and `nmId`. No `canceled`, no `orderId`, no associated flag, no originating nm.

`date` is the day bucket. It is not an order timestamp. `nmId` is the article the metrics are attributed to, not a proven promoted source for that row. `boosterStats[].nm` is an average-position article, not an attribution source.

Local pydantic mirrors the same nesting and then drops it: `NmStats` / `AppStats` in `app/modules/full_stat_adv_updater/types/full_adv_stat.py` include `nmId` and `appType`; `DayStats.apps` is commented out (line 49). `DaysItemAppsItemNmItem` has no `canceled`. A defensive read of raw `canceled` in `scripts/wb_a1_associated_conversions.py` is not a schema field.

`SOURCE_NM_ID` contract result: `CAMPAIGN_SCOPE_ONLY`. The fact must not store a fabricated originating nm. A single-nm membership set may be shown as campaign scope in a derived read. A multi-nm campaign must not pick one promoted nm.

## 2. Collector / mapper collapse point

`full_stats_item_to_full_adv_stat` (`app/core/mp/wb/api/adapter/promotion_client/fullstats/mapper.py`) keeps raw `item.days` only long enough for `_days_to_day_stats` (lines 37–66), which copies day `views/clicks/sum/atbs/orders/shks/sum_price` and ignores `apps` / `nm`. `fetch_fullstats_v3` (`app/modules/full_stat_adv_updater/fullstats_v3_legacy.py`) always maps through that function. `scripts/wb_a1_associated_conversions.py` lines 1–6 state that this mapper drops `apps[].nms[]` and therefore walks raw JSON instead. That script looks up `nms`; the generated key is `nm`. A future collector must read `nm` (and may accept `nms` only as an explicit alias), not the other way around.

`full_wb_adv_stat.insert` (`app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py` lines 334–374) writes one row per day: `adv_id`, `date` (`%Y-%m-%d`), `views`, `clicks`, `spend` from day `sum`, `added_to_cart` from `atbs`, `orders`, `sum_price_orders` from `sum_price`, `version=time.time()`. `shks` and `canceled` are not stored. Every insert allocates a new `version` even when the payload is unchanged.

## 3. `full_adv_wb_stat` schema

Test DDL in `tests/support/destructive_ch_reset.py` lines 34–46:

`adv_id Int32`, `date Date`, `views Int32`, `clicks Int32`, `spend Float64`, `added_to_cart Int32`, `orders Int32`, `sum_price_orders Float64`, `version Float64`, `ENGINE = MergeTree()`, `PARTITION BY toYYYYMM(date)`, `ORDER BY (adv_id, date, version)`.

No `shop_id`, `app_type`, `nmid`, `shks`, or `canceled`. Reads use `argMax(metric, version)` grouped by `(adv_id, date)` (`full_wb_adv_stat.py` lines 102–114; `app/modules/shop_runner/shop_wide_collection/full_adv_read_latest.py` lines 19–31; `app/modules/ai_package_v1/sql/campaign_full_stat_by_adv_ids.sql`). `get_stats_by_last_days` then sums those latest rows across the passed `adv_ids`, so a mixed Auto+Search id list collapses legs. `001_create_incremental_tables.sql` defines `full_adv_wb_stat_incremental` / `_hourly` (delta log), not the nm fact.

## 4. `campaign_settings_history.payload_json` and `nmids`

`scripts/clickhouse_migrations/006_create_campaign_settings_history.sql`: append-only `MergeTree`, columns include `observed_at DateTime64(3, 'UTC')`, `snapshot_id`, `adv_setting_id`, `shop_id String`, `adv_id Nullable(UInt64)`, `search_adv_id Nullable(UInt64)`, `schema_version UInt16`, `state_hash FixedString(64)`, `payload_json String`. Order key `(wb_cabinet_id, adv_setting_id, observed_at, snapshot_id)`.

Canonical payload (`app/modules/campaign_settings_contract/canonical.py`) puts METADATA `AdvSetting` fields in `identity`, including `nmids`. Registry (`registry.py` line 148) classifies `nmids` as metadata with `NormalizationPolicy.INT_LIST` (sorted unique ints). Excel alias `nmid:first` does not truncate storage. Unit proof: `tests/unit/test_campaign_settings_canonical.py` line 171 expects `payload["identity"]["nmids"] == [10, 30]`. Collector (`campaign_settings_history/collector.py` lines 74–76) skips insert when `state_hash` is unchanged.

As-of membership for a stat date is the latest snapshot with `observed_at` at or before the end of that date, joined by history `adv_id` or `search_adv_id`. The list is the settings pair's product list, shared by both legs, not a per-`adv_id` WB `nm_settings` timeline. If the first snapshot is after the stat date, or `nmids` is absent, classification is `UNKNOWN`. That is `REUSE_EXISTING`, not a new membership table. It is not sufficient to classify from current inventory alone.

## 5. `shop_campaign_inventory`

`007_create_shop_campaign_inventory_and_availability.sql`: `shop_campaign_inventory` is `ReplacingMergeTree(version)` ordered by `(shop_id, adv_id)` with `nm_ids Array(UInt64)`. Latest row wins; previous membership is not a historical contract. `discovered_campaign_from_advert` (`inventory_upsert.py` lines 176–197) sets `nm_ids` from current WB `item.nm_settings`. `shop_campaign_collection_availability` is append-only `MergeTree` diagnostics (`collector_id`, `reason_code`, `route_version`), not a fact. Use inventory only as a current hint. Historical classification uses settings history. Do not treat a missing inventory nm as zero attributed orders.

## 6. Migrations 006 and 007

006 creates only `default_db.campaign_settings_history` (section 4). 007 creates inventory plus availability and states that it does not alter `full_adv_wb_stat`, `wb_common_stat`, or `clusters_adv_stats`. Neither migration stores day/app/nm fullstats. Accepted `openspec/decisions/clickhouse-migration-corpus-006/decision.md` extends the reviewed corpus through 006 and says later numeric prefixes stay fail-closed until another reviewed change. Tests already fingerprint 007. A new attribution table would be a further reviewed corpus version, not an ad-hoc `CREATE` from the collector.

## 7. `separate-auto-search-cpo` current inputs

Not on `origin/stage`. Branch `origin/cursor/separate-auto-search-cpo-clean-a089` at `f6c18bb76843a73a0ec929d087592d50d6dcedad` adds `app/modules/shop_runner/wb_stat_manager/leg_cpo.py`. `compute_leg_cpo` is `spend / max(orders, 1)` from `SmallFullAdvStat` loaded per exact `adv_id` via `get_stats_by_adv_ids_last_days` (that function is not on stage). Window default is 2 calendar days, shared by both legs. `auto_adv_id` is `ComplexAdv.auto_adv_id` (`AdvSetting.adv_id`); Search is `ComplexAdv.search_adv_id`. Missing leg is `None`. Design (`openspec/changes/separate-auto-search-cpo/design.md` on that branch) says no new table and "не менять attribution WB". Aggregate `fact_pay_for_order` stays aggregate.

Feed, do not replace, that read model:

- AUTO: `fact.adv_id = auto_adv_id` → `attributed_orders_auto`, `attributed_gmv_auto` (`sum_price_orders`), `auto_cpo = campaign_spend_auto / attributed_orders_auto`, `auto_drr = campaign_spend_auto / attributed_gmv_auto`.
- SEARCH: same with `search_adv_id`. No substitution from the other leg or from the pair aggregate.
- Spend numerator stays `argMax(spend, version)` on `full_adv_wb_stat` for that `adv_id` and window. Nm `sum` is not the billing numerator unless a future check shows it reconciles; this plan does not switch it.
- Denominator and GMV decomposition use the nm fact only when that `(adv_id, date)` coverage is `COMPLETE`. Otherwise attributed CPO/DRR is unavailable. Existing leg CPO, which uses campaign-level orders, remains a different metric and must not be labeled attributed.

## 8. Full AI Package campaign advertising family

`family_status.py` maps `campaign_advertising` to `DatasetId.CAMPAIGN_FULL_STAT`. Card grain is `adv_id + date` from `default_db.full_adv_wb_stat`, notes "Auto and Search adv_id rows preserved separately" (`export/dataset_cards.py`). SQL selects only `argMax` views and clicks (`sql/campaign_full_stat_by_adv_ids.sql`). `package_summary.py` joins `campaign_stat.campaign_id` to per-leg `wb_adv_id` and forbids merging Auto and Search. `family_gaps.py` does not list an nm-attribution family. Orders inside fullstats are advertising metrics, not the shop product order feed (`orders-or-sales-reports-read-identity`; gap `shop_product_orders_sales_feed`). A future export is a new dataset. It must not widen `campaign_full_stat.csv` in place or fill gaps with zeros.

## 9. Revision pattern to reuse

Reuse both of these, not inventory's `ReplacingMergeTree`:

- Append and keep history: `campaign_settings_history` `MergeTree` plus hash skip (`collector.py`). Identical canonical metric payload does not insert.
- Latest projection: `full_adv_wb_stat` / `full_adv_read_latest.py` `argMax(metric, version)`. For the new fact, use `observed_at DateTime64(3, 'UTC')` as the `argMax` version so a restatement of yesterday appends and becomes latest without deleting the previous observation.

Do not copy unconditional `version = time.time()` from `insert()`. That creates a new logical row for an identical payload. `wb_common_stat` `ReplacingMergeTree(version)` (`destructive_ch_reset.py` lines 96–109) is a latest-state pattern and drops prior revisions as a contract. `shop_campaign_inventory` is the same class of loss.

Candidate physical names, mapped onto existing columns rather than the prompt's aliases:

| Candidate | Repository convention |
|---|---|
| `shop_id` | `String`, as in 006/007. `full_adv_wb_stat` has no shop id. |
| `adv_id` | `Int64` to match inventory; `full_adv_wb_stat.adv_id` is `Int32`. Join with an explicit cast. |
| `date` | `Date`. Do not invent `stat_date`. |
| `app_type` | `Int32` from `appType`. |
| `nmid` | `UInt64`, as in `clusters_adv_stats` / `wb_common_stat`. Not `attributed_nm_id`. |
| `views`, `clicks` | `Int32`. |
| `spend` | `Float64` from API `sum`. Not `spend_rub`. Not the CPO numerator. |
| `added_to_cart` | `Int32` from `atbs`. |
| `orders` | `Int32`. Aggregated count. |
| `shks` | `Int32`. Present on the nm model; absent from `full_adv_wb_stat`. |
| `sum_price_orders` | `Float64` from `sum_price`. This is attributed GMV. |
| `canceled` | Do not store as an nm fact. Declared only on campaign `FullStatsItem`. |
| `observed_at` | `DateTime64(3, 'UTC')`. |
| `schema_version` | `UInt16`. |
| `source_endpoint` | `LowCardinality(String)`, value `/adv/v3/fullstats`. |
| `state_hash` | `FixedString(64)` SHA-256 of canonical metric bytes. |
| `collector_id` | `String`, same role as availability `collector_id`. |

No `source_nm_id` column. Classification `PROMOTED_PRODUCT | ASSOCIATED_PRODUCT | UNKNOWN` is a read/projection against as-of `identity.nmids`, not a WB flag and not `views == 0`.

Coverage row per `(shop_id, adv_id, date)`, append-only, `coverage` as `String` (007 avoids CH enums): `COMPLETE` only when, summing every `appType`, child `orders`, `sum_price`, and `atbs` equal the day totals and the day totals equal the campaign window totals. Missing `apps`/`nm`, a parser that only sees `nms`, or any mismatch ⇒ not `COMPLETE`. Downstream attributed DRR/CPO fails closed. `NO_DATA` is not success (`shop-data-source-strategy` points 8 and Forbidden).

## Architecture decisions used

Context-first, three files after `openspec/decisions/index.md`:

- `openspec/decisions/shop-data-source-strategy/decision.md`: keep source grain; do not allocate campaign stats onto `nm_id` without a source breakdown; keep Auto and Search as separate `campaign_id` rows; do not add a physical table for the pair link; coverage and missing data fail closed. Storing the API's own nm breakdown follows that rule. Pair identity stays on `ComplexAdv` / settings `adv_id` + `search_adv_id`.
- `openspec/decisions/shop-runner-shop-wide-collection/decision.md`: shop-wide ad collection is shop-runner, not a `scripts/` Job. The existing "write available data into existing stores" sentence is scoped to `shop-wide-campaign-data-collection`. This fact is a later storage change, which `shop-data-source-strategy` leaves to a future schema change. The writer, when implemented, extends the shop-runner fullstats path rather than a second collector.
- `openspec/decisions/clickhouse-migration-corpus-006/decision.md`: new DDL needs a reviewed corpus extension. Not applied here.

No accepted decision forbids this placement. `Architecture Decision Missing` is not emitted. Implementation still needs an Owner GO and a reviewed migration decision. `IMPLEMENTATION_READY` stays `NO`.

## Non-scope

DRR controller, shop DRR capacity, bid changes, ChangeSet apply, JSON write API, campaign creation, decision/event persistence, and production writes are boundaries only. Advertising `orders` must not be substituted for supplier order/sales identity.
