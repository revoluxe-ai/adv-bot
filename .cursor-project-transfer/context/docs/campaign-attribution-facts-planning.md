# Campaign attribution facts — planning

Status: **PLANNING_READY**. Implementation is not started. No branch, no product code, no migration, no production writes.

Source: [campaign-attribution-facts — planning](bc-46efa5c9-3468-5b4a-b622-3568beff7e08). Baseline they read was `origin/stage` `144364928`, which is the unauthorized package-repair fast-forward. Do not implement until [#451](https://github.com/revoluxe-ai/adv-bot/pull/451) restores a clean stage.

## What fullstats actually is

`/adv/v3/fullstats` grain is `advertId → day.date → apps[].appType → nm[].nmId`, with aggregated metrics. It is not an order identity.

- Order id: no
- Exact order time: no
- Basket event id: no
- Explicit associated flag: no
- Originating nm id: no. Contract is campaign-scope only. Do not invent a source nm, and do not pick one promoted nm for a multi-nm campaign.

Typed models exist on `POST /adv/v2` `DaysItem*`. `GET /adv/v3` `FullStatsItem.days` is `Any` and is collapsed to `advertId + date` before ClickHouse.

Current loss: the mapper drops `apps` / `nm`, `DayStats.apps` is commented out, and `full_adv_wb_stat` stores only `(adv_id, date)`.

## Proposed fact

Grain: `shop_id + adv_id + date + app_type + nmid`.

Storage candidate: append-only MergeTree observation `default_db.full_adv_nm_stat`, plus an `argMax` latest projection. An identical payload hash does not append. A changed WB restatement appends and becomes latest. Prior rows stay. Not ReplacingMergeTree-only.

Classification:

- `PROMOTED_PRODUCT` when the attributed nmid is in the as-of settings membership
- `ASSOCIATED_PRODUCT` when membership is non-empty and the nmid is outside it
- `UNKNOWN` when there is no covering snapshot
- `views == 0` is not the discriminator

Historical membership reuses existing settings history. Campaign-level check: for each `(adv_id, date)`, the sum of nm `orders` / `sum_price` / `atbs` across `appType` must equal the day totals, and the sum of day totals must equal the campaign-window totals. A mismatch or missing `apps` / `nm` means coverage is not `COMPLETE`.

Auto and Search join on `fact.adv_id = ComplexAdv.auto_adv_id` or `search_adv_id`. No cross-leg fallback. Spend numerator stays the latest `full_adv_wb_stat` spend. Attributed orders and GMV come from the nm fact only when coverage is `COMPLETE`. Missing or contradictory nm detail is not zero. Downstream attributed DRR/CPO fails closed.

## What this does not change

`campaign_advertising` in the AI package stays `CAMPAIGN_FULL_STAT` at `adv_id + date` (views/clicks only). Nm attribution is not in the v1 ZIP. Do not merge Auto and Search into that CSV.

`separate-auto-search-cpo` is not on stage, and that change must not grow an attribution table. `inc-ro-08` forbids treating fullstats orders as supplier orders.

## Before any implementation

- Restore clean stage ([#451](https://github.com/revoluxe-ai/adv-bot/pull/451) is still draft).
- Accept pair-level settings nmids as membership, or require a WB `nm_settings` history extension.
- Keep campaign spend as the CPO/DRR numerator.
- Review the ClickHouse corpus before a new migration. The accepted registry stops at `006`. `007` is already in code and tests.
- Do not switch the existing leg CPO denominator until coverage is `COMPLETE`.
