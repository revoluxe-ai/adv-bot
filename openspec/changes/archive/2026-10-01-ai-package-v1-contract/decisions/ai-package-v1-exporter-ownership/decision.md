# Decision: AI Package v1 exporter ownership and read boundary

## Status

Proposed

## Context

Accepted `openspec/decisions/shop-data-source-strategy/decision.md` defines
invariants for reading accumulated PG/CH but explicitly excludes ZIP format and
exporter implementation. Change `ai-package-v1-contract` needs a reusable rule
for where read-only export lives and which layers MUST NOT own it, so collectors
and shop-runner updaters are not extended with ZIP or AI packaging concerns.

## Decision

1. AI Package v1 export orchestration and manifest/ZIP encoding MUST live in a
   dedicated read-only module namespace under `app/modules/ai_package_v1/` (exact
   subpackages per change design), invoked by an optional `scripts/` Job entry.
2. Export path MUST be `READ_ONLY_NO_MUTATION`: no WB API, no collector triggers,
   no shop-runner orchestrator (`WBShopDataManager`, `_get_min_bids`,
   `backfill_min_bids_for_adv`), no `bot_active` / mode default / paid-free
   transition writes, no CH/PG INSERT or DDL from export.
3. ClickHouse reads for export MUST use query text that qualifies
   `default_db.<object>` per
   `openspec/decisions/clickhouse-sql-database-qualification/decision.md`.
4. Shop-runner services (`full_wb_adv_stat`, updaters, CommonSaleStatUpdater) MAY
   be referenced as patterns; export MUST NOT add ZIP/manifest logic into those
   modules — shared SQL MAY be extracted only into `ai_package_v1` or shared
   `sql/` with export-owned tests.
5. Telegram/GUI MUST NOT be the v1 export entrypoint; operator/Job/CLI only.

## Applies to

- Change `ai-package-v1-contract` and future apply/verify for AI Package v1 export
- Contract tests under `tests/unit/ai_package_v1/` (and integration fixtures)

## Allowed

- New read-only readers wrapping `get_clickhouse_client` and PG read sessions
- Named `PgExportShopScopeReader` under `app/modules/ai_package_v1/scope/` using
  `get_async_session_maker(read_only=True)` and AdvSetting/WBCabinet join query
  aligned with `WBShopDataManager.__get_advs(..., only_bot_active=False)` **without**
  importing or calling `WBShopDataManager`
- In-process `ComplexAdv` / scope DTO construction from ORM rows (no Redis keywords)
- Script entry `scripts/ai_package_v1_export.py` (or ops Job wrapper) calling
  export service
- Deterministic validator in `app/modules/ai_package_v1/` or `tests/` helpers

## Forbidden

- WB API calls from export or validator default path
- Importing, constructing, or invoking `WBShopDataManager` (including indirect
  delegation for scope/min-bids/keywords)
- Calling `_get_min_bids`, `backfill_min_bids_for_adv`, or WBManager promotion
  clients from export package
- Using `snapshot_data_updater.providers.postgres_provider` bot_active-only warmup
  filter as export campaign scope
- Triggering shop cycle, collectors, backfill, CSV poller from ZIP build
- Placing export orchestration inside `shop_runner` updater/write services
- Using funnel or campaign orders as shop product orders/sales source
- DDL/migrations solely for export in this change (use existing tables only)
- Telegram handlers or GUI flows as required export surface

## Examples

Хорошо:

- `ExportService.export(shop_id, period)` reads CH/PG, writes ZIP to stdout/path.
- Contract test spies WB layer — zero calls.

Плохо:

- Export method on `CommonSaleStatUpdater` that also builds ZIP.
- Export triggers `new_wb_shop_update_run` to “fill gaps” via WB.

## Related specs

- `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-exporter/spec.md`
- `openspec/changes/ai-package-v1-contract/specs/ai-package-v1-contract-tests/spec.md`
- Canonical: `openspec/specs/data-source-selection`, `coverage-provenance`,
  `grain-preservation`

## Related changes

- `ai-package-v1-contract` (this change)
- Strategy archive: `openspec/changes/archive/2026-09-26-ai-package-data-source-strategy`

## Review checklist

- [x] Existing decisions searched (`shop-data-source-strategy`, CH qualification)
- [x] Relevant decisions cited
- [x] New decision proposed because ZIP/exporter placement not in strategy ADR
- [x] Implementation layer matches decision (dedicated read-only module)
