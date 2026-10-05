# Decision: AI Package keyword performance history — ownership and read boundary

## Status

Proposed

## Context

Accepted `openspec/decisions/ai-package-v1-exporter-ownership/decision.md`
places AI Package export in `app/modules/ai_package_v1/` with READ_ONLY_NO_MUTATION.
Keyword/query daily history exists in ClickHouse (`clusters_adv_stats`) and bot/UI
paths (`KeywordDailyHistoryManager`, Telegram graph) but not in AI Package v1.
Owner Contract D-001..D-013 requires canonical export grain, conservative spend,
rebind scope expansion, DATA_MAP/coverage, and forbids UI/Telegram presentation
as canonical source. Reusable placement rules for keyword export scope reader,
forbidden sources, and rebound Redis read seam are not covered by existing ADRs.

## Decision

1. Keyword performance export orchestration, window engine, DATA_MAP builder, and
   CH/PG/Redis **read** adapters MUST live under
   `app/modules/ai_package_v1/keyword_performance/` (exact subpackages per design).
2. Integration MUST wire through existing `ExportService` only — no second exporter,
   no shop-runner updater ownership, no script-only canonical path.
3. Keyword scope expansion MUST use a **keyword-specific scope reader**
   (`KeywordExportScopeReader`) that extends inventory with:
   - PG anchor `AdvSetting.id` (PK) per inventory row;
   - current auto/search `adv_id`s;
   - Redis rebound membership via `get_rebound_wb_adv_ids(adv_setting_id)` (**read
     only**);
   - deduped expanded `adv_id` set for CH filters.
   Public `ExportScopeAdv` DTO MUST NOT gain new required fields; keyword scope is
   an internal seam consumed by keyword readers only.
4. Canonical daily facts MUST read from `default_db.clusters_adv_stats` with
   **row-coherent** latest snapshot selection at grain
   `(adv_id, nmid, norm_query, date)` — full metric tuple from the winning
   `timestamp` row; per-field nullable `argMax` forbidden; snapshot conflicts
   → `AMBIGUOUS` fail-closed. DDL (`destructive_ch_reset.py:62-81`) has no
   `ingest_sequence`. `KeywordDailyHistoryManager` / `get_keyword_daily_history.sql`
   UI rollup (GROUP BY date only) is **forbidden** as export source.
5. Forbidden canonical sources: `graphic_positions_creator`, `get_position_history.sql`
   zero→max_pos substitution, any Telegram presentation jitter/nearest-day fill.
6. Export path MUST remain READ_ONLY_NO_MUTATION: no WB API, no Redis writes, no PG
   writes, no control-plane apply, no `bid_decision_log` fill/backfill triggers.
7. `bid_decision_log` MAY be read when join keys proven; MUST be labeled
   `DECISION` not `ACTION` (Owner D-009). Export MUST probe read-only availability
   before attach; empty/unavailable → explicit `UNSUPPORTED` coverage.
8. Keyword scope MUST validate requested-shop PG ownership for every
   `(adv_id, adv_setting_id)` assignment **and** run a global adv_id overlap probe
   across all shops (requested-shop-only inventory MUST NOT be claimed as global
   isolation proof). Rebound overlap without authoritative mapping →
   `AMBIGUOUS_OWNERSHIP` / `FOREIGN_SHOP_ADV_ID` fail-closed (no duplicate logical
   emission). Coverage records `ownership_evidence_scope:
   REQUESTED_SHOP_PG_PLUS_GLOBAL_ADV_ID_OVERLAP`.
9. `raw_query` MUST be null with `RAW_QUERY_UNAVAILABLE` when no distinct
   source-proven raw column; MUST NOT fabricate from `norm_query` or unproven PG text.
10. `ExportService` MUST default-build `KeywordPerformanceAssembler` (same pattern as
    `CampaignSettingsAssembler`); unit tests inject fakes explicitly.
11. All keyword date queries MUST respect `package_cutoff_date` and
    `package_cutoff_instant` derived from `generated_at` UTC where source temporal
    semantics allow (`clusters_adv_stats.timestamp`, `bid_decision_log.decision_time`,
    `keyword_position_from_api.version` as UTC epoch ms — proven writer
    `click_house_manager.update_positions:88`). Position bounds/read SQL MUST apply
    `version <= cutoff_instant_ms` via
    `toUInt64(toUnixTimestamp64Milli(toDateTime64({package_cutoff_instant}, 3, 'UTC')))`.
    Unproven legacy rows without writer lineage → date-only fallback +
    `UNKNOWN_VERSION_TIME_SEMANTICS`; do not blanket-label current writer path
    `SAME_DAY_INSTANT_UNSUPPORTED`. `source_calendar_timezone` documented as UNKNOWN.
12. Campaign `keyword_current_state` MUST NOT use `mv_clusters_last_state`
    (nmid×text) as campaign authority; strict `(adv_id, nmid, norm_query)` daily
    reader only for campaign rows. Rows MUST carry `campaign_slot_role`; rebound
    physical adv_ids are `REBOUND_HISTORICAL` evidence, not current active campaign
    identity.

## Applies to

- Change `ai-package-keyword-performance-history`
- `ExportService` keyword dataset integration
- Contract tests under `tests/unit/ai_package_v1/keyword_performance/`

## Allowed

- New read-only CH SQL under `app/modules/ai_package_v1/keyword_performance/sql/`
- Constructor-injected fake CH/Redis/PG seams in unit tests
- Redis `get_rebound_wb_adv_ids` read on export path
- PG `AdvSetting.id` lookup via existing inventory query pattern
- Optional physical JSONL chunk files with unified logical DATA_MAP semantics
- Root `DATA_MAP.json` + `coverage.json` payloads in manifest

## Forbidden

- Second exporter or parallel ZIP builder outside `ai_package_v1`
- Extending public `ExportScopeAdv` with breaking fields for all v1 consumers
- Using UI daily history SQL, `get_clusters_stats.sql` cross-adv_id rollup, or
  Telegram graph as canonical export source
- `spend = CPM × views / 1000` as factual export when D-003 not satisfied
- Redis rebound set interpreted as temporal transition dates
- WBShopDataManager, snapshot_data_updater writes, collectors on export path
- Default `ExportService()` omitting keyword datasets (None assembler → DISABLED)
- Silent disable of keyword export without explicit fake injection in unit tests
- Per-field nullable `argMax` on daily rollup
- Emitting `norm_query` as `raw_query` without proven distinct raw column
- Assigning `mv_clusters_last_state` metrics to campaign rows without strict grain

## Examples

Хорошо:

- `ExportService()` default-builds `KeywordPerformanceAssembler`; unit tests inject
  fake assembler/readers explicitly (settings-assembler pattern).
- `KeywordExportScopeReader` returns expanded adv_ids including rebound history.

Плохо:

- New `scripts/keyword_ai_export.py` as sole authority bypassing ExportService.
- Reusing `get_keyword_daily_history.sql` GROUP BY date for AI Package daily rows.

## Related specs

- `openspec/changes/ai-package-keyword-performance-history/specs/ai-package-keyword-performance-history/spec.md`
- `openspec/specs/ai-package-v1-exporter/spec.md`
- `openspec/specs/grain-preservation/spec.md`
- `openspec/specs/coverage-provenance/spec.md`

## Related changes

- `ai-package-keyword-performance-history`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`ai-package-v1-exporter-ownership`, CH qualification)
- [x] new decision proposed because keyword placement/forbidden sources not in registry
- [x] implementation layer matches decision (`ai_package_v1/keyword_performance/`)
