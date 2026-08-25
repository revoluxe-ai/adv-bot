# Design: Adv-bot historical state extractor

## Architecture Decision References

- No new reusable ADR required: script is READ_ONLY ops tooling under `scripts/`,
  reusing existing CH/PG access patterns from forensic collectors.
- Domain tables: `default_db.plan_fact_stats`, `default_db.clusters_adv_stats`,
  `default_db.bid_decision_log`; PG `advsetting`, `keywordsetting` (CURRENT only).

## Ownership & Placement

| Concern | Placement |
|---------|-----------|
| CLI entrypoint | `scripts/adv_bot_historical_state_extractor.py` |
| CH/PG transport | reuse `scripts/ch_a1_evidence.py` helpers |
| PG settings field list | reuse subset from `scripts/a1_baseline_v0_collect.py` |
| Unit tests | `tests/unit/scripts/test_adv_bot_historical_state_extractor.py` |
| REGISTRY / Job integration | **deferred** — parallel scripts worktree |

## Read paths

1. **plan_fact_stats** — SELECT historical rows for resolved `adv_id` set and date window (MSK bounds via `--timezone`).
2. **clusters_adv_stats** — intraday raw rows; daily rollup via `argMax`/`max(timestamp)` per (adv_id, nmid, norm_query, date).
3. **bid_decision_log** — existing rows only; no fill/backfill.
4. **PostgreSQL** — CURRENT_SNAPSHOT of `advsetting` + `keywordsetting` for shop (labeled, not historical).
5. **prod revision timeline** — local `git log` on `origin/stage` / `origin/master` / `origin/scripts` in period (READ_ONLY).

## Safety

- Fail closed on any write SQL token in generated queries.
- Secret scan before ZIP (reuse `ch_a1_evidence.secret_scan`).
- No Redis, no WB API, no kubectl secret dump.

## Output pack

```
manifest.json
coverage.json
plan_fact_intraday_raw.csv
keyword_intraday_raw.csv
keyword_daily_raw.csv
bid_decision_raw.csv
current_settings_snapshot.csv
prod_revision_timeline.csv
DATA_GAPS.md
README.md
sql/…
```

Primary: `ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip` + `.sha256`

## Checklist

- [x] context-first decision lookup performed (no conflicting ADR)
- [x] relevant decisions cited (N/A — scripts read-only tooling)
- [x] new decision proposed if missing (not required)
- [x] implementation layer matches decision (scripts only)
