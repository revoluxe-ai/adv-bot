# Missing campaign leg coverage

Second HOME-PC acceptance export stopped in `assert_no_synthetic_merge()` with
`silent merge: only one of Auto/Search adv_id present in export` after PG scope
load and ClickHouse `campaign_full_stat` read. No writes occurred.

That guard treated a missing physical leg as a synthetic merge. The repaired
guard rejects only a `campaign_id` outside the permitted physical set
`{auto_adv_id, search_adv_id}`. A missing leg is omitted, not zero-filled.
A non-empty proper subset records `PARTIAL_COLLECTION` and stays off
`FULL` / `COMPLETE`. An empty slice stays `NO_DATA` with coverage `UNKNOWN`.

Rows for both physical ids are still preserved independently.
