## Why

Сейчас shop-runner собирает common-sales (`wb_common_stat`) только по `main_nmid` активных рекламных ComplexAdv. SKU вне кампаний и не-reklamный ассортимент не покрываются, хотя downstream read-only метрики ожидают полный current assortment. Нужен bounded runtime MVP в существующем shop-runner без второго процесса и без смешения с campaign advertising inventory.

## What Changes

- MODIFIED: **existing** `CoroutinesManager.update_common_sale_stat` becomes the **single** shop-wide coordinator — one frozen A/E/U partition per tick, disjoint E/U collect routes via shared updater.
- ADDED: discovery current non-trash assortment (A) через Content API `get_cards_list` pagination; explicit fail на null/partial pages.
- ADDED: regular recollection — **every tick** refresh all E and all U nmIDs over 7 MSK-day window (CH read-latest never skips collect).
- ADDED: last-attempt coverage evidence in Redis; completeness from this tick's API + assortment proof, not CH row existence alone.
- ADDED: structured tick logs with explicit counter semantics (`existing_covered_count=|E|`, `uncovered_count=|U|` SKU counts).
- ADDED: bounded no-ad TaskGroup survival — exhaustive `WBShop.run` registry + `taskgroup_no_ad_supervisor` at task factory (18 loader-path coroutines) + coordinator `_resolve_legacy_assigned_nmids` (E=∅, exempt); auth/other-stop preserved; returned-fact validation before CH insert.
- PRESERVED: public coroutine signature, shared funnel adapter, batch size 20, retry/limit semantics, DTO normalization, `ClickHouseCommonStatManager.insert` writer unchanged.
- OUT OF SCOPE: second coroutine, campaign discovery/inventory, `full_adv_wb_stat`, Store DRR numerator, history backfill >7 MSK days, new CH table, independent scripts/Job executor, WB advertising writes.

## Capabilities

### New Capabilities

- `shop-wide-common-sales-collection`: runtime shop-wide сбор factual common-sales для current non-trash SKU через single coordinator coroutine, partition A/E/U, regular recollection, honest last-attempt coverage, no-campaign TaskGroup survival, logging и acceptance matrix.

### Modified Capabilities

- _(none — новое product behavior; существующие canonical specs не меняют REQUIREMENTS на уровне Free/Paid или campaign lifecycle)_

## Impact

- **Runtime**: shop-runner `WBShop` TaskGroup — **same** `update_common_sale_stat` registration, expanded coordinator body; `taskgroup_no_ad_supervisor` wraps 18 registry coroutines at `create_task` factory.
- **Read paths**: Content API pagination; CH argMax for downstream read-latest only.
- **Write paths**: только существующий append/versioned insert в `wb_common_stat` — no DDL change in MVP.
- **Sibling dependency**: campaign boundary reconciled (`CAMPAIGN_CHANGE_RECONCILED=YES` per sibling receipt).
- **Risk**: large shops (500+ SKU) — full refresh every tick; pagination latency and API limits; partial API null must not write fake zeros.
- **Rollback**: revert coordinator body to legacy E-only; remove supervisor registry; CH rows append-only.
