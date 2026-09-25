# Spec: adv-bot-internal-history-extractor

## Requirements

### REQ-EXTRACT-CLI

The extractor MUST accept:

- `--shop-id` (required)
- `--from`, `--to` (inclusive dates, YYYY-MM-DD)
- repeatable `--adv-id`, `--nmid`
- `--timezone` (default `Europe/Moscow`)
- `--output-dir`
- `--case` (slug for primary ZIP name)

When `--adv-id` / `--nmid` omitted, resolve from PostgreSQL `advsetting` for the shop.

### REQ-READ-ONLY

The extractor MUST perform only SELECT/read operations against PostgreSQL and ClickHouse.
It MUST NOT invoke fill_bid_decision, backfill jobs, Redis writes, or WB API writes.

### REQ-DATASETS

The pack MUST include:

1. plan_fact_stats historical CSV
2. clusters_adv_stats intraday CSV
3. clusters_adv_stats daily rollup CSV
4. bid_decision_log CSV (existing rows)
5. PostgreSQL settings CURRENT_SNAPSHOT CSV (explicitly labeled non-historical)
6. production revision timeline CSV from git history

It MUST NOT duplicate ER-020 external WB/store outcome datasets.

### REQ-PRIMARY-ARTIFACT

The extractor MUST produce:

- `ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip`
- matching `.sha256` sidecar
- stdout JSON with `ZIP_ABSOLUTE_PATH`, `ZIP_SHA256`, `LOCAL_ARTIFACT_HANDOFF`

### REQ-GAPS

`DATA_GAPS.md` MUST document missing coverage per dataset and selector scope.
