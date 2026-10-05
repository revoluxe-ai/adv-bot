# AI_PACKAGE_KEYWORD_HISTORY_INVENTORY_REPORT

Evidence task: `WB-SKY-KEYWORD-HISTORY-INVENTORY-20261005-0054-R2`  
Execution worker: `WB-SKY-KEYWORD-HISTORY-OWNER-20261005-0057`  
Collected: 2026-10-05

```text
WORKTREE:
C:\Users\vkita\my_code\meta-repo\ai-package-keyword-performance-history

BRANCH:
ai-package-keyword-performance-history

BASE_HEAD:
37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0
(verified via git rev-parse HEAD in worktree)

EXISTING_AI_PACKAGE_EXPORTER:
Module: app/modules/ai_package_v1/export/export_service.py — ExportService.export(shop_id, period)
read-only orchestrator; datasets today: campaign_full_stat (CH full_adv_wb_stat),
complex_adv_funnel (CH wb_common_stat), campaign_settings_snapshot (PG via
CampaignSettingsAssembler), shop_product_orders_sales (explicit unassigned card).
ZIP: app/modules/ai_package_v1/zip_transport/encode.py encode_package().
Authority: openspec/decisions/ai-package-v1-exporter-ownership/decision.md (Accepted).
Integration pattern for new dataset: same as campaign_settings_snapshot — new reader/assembler,
DomainPayload + manifest card in ExportService._export_with_scope (lines 226–257).
Gap: scripts/ai_package_v1_export.py referenced in ADR not present in worktree; only
tests/unit/ai_package_v1/test_export_settings_integration.py calls ExportService + encode_package.

DAILY_KEYWORD_SOURCE:
Primary persisted query-level daily facts: default_db.clusters_adv_stats →
default_db.mv_clusters_daily_agg (AggregatingMergeTree argMaxState by adv_id, nmid, norm_query, date).
Evidence: tests/support/destructive_ch_reset.py:252–283 (MV definition from clusters_adv_stats).
Bot/UI path: KeywordDailyHistoryManager + get_keyword_daily_history.sql (mv_clusters_daily_agg +
clusters_adv_stats for position). Script reference (not ExportService): scripts/adv_bot_historical_state_extractor.py
export_keyword_daily() — argMax(*, timestamp) per (adv_id, nmid, norm_query, date) from clusters_adv_stats
(lines 1000–1018), preserves physical adv_id grain.
Alternate historical table: default_db.advkeyword_new (scripts/ch_a1_compact_export.py:540–564) —
grain date × adv_id × text; spend via argMaxMerge(spend_state).
Write path: clusters_adv_stat_updater → NormqueryStatsDTO → RowStatDTO.spend from WB
(getattr(st, "spend", None)) — app/modules/shop_runner/.../convertor.py:42.
Export authority fork: prefer adv_bot_historical_state_extractor grain (physical adv_id) over UI SQL rollup.

EARLIEST_DATE_DISCOVERY:
Code-proven: MIN(date) on mv_clusters_daily_agg filtered by adv_ids, nmids, norm_query —
get_keyword_earliest_date.sql:12–16; KeywordDailyHistoryManager.get_earliest_date:89–105.
UI pagination uses datetime.now().date() — date_pagination.py:21,37 (server local calendar, not documented TZ).
Broader UI boundary: CommonStatDataManager.get_earliest_stat_date — max(min funnel, min campaign)
with expanded adv_id set (rebind + siblings + CH cluster adv_ids) — common_stat_data_manager.py:253–268.
Live retention / first_available in production CH: NOT OBSERVED (no DB reads); no TTL in repo DDL
for clusters_adv_stats (test DDL only). Cannot claim 2y vs 4mo retention.

DAILY_GRAIN:
Owner decision (D-001): shop × logical resource × physical adv_id × leg where proven × nmid ×
normalized query × date — strict; no silent aggregation.
CH MV native grain: adv_id × nmid × norm_query × date (destructive_ch_reset.py:268).
ExportScopeAdv grain: shop_id, auto_adv_id, search_adv_id, main_nmid — no AdvSetting.id (PG PK),
no leg enum on rows — scope/dto.py:8–24.
KeywordDailyHistoryManager SQL collapses inner (adv_id,nmid,norm_query,date) → outer GROUP BY date only
(get_keyword_daily_history.sql:37–43,57–67) — FORBIDDEN as canonical export path (UI aggregation).
Query filter: norm_query = %(text)s with text = keyword_setting.text (manager:162) — collision risk
documented: update_cluster_bids_manager.py:659–664 (kw.text vs cluster_stat.text / norm_query).

AVAILABLE_METRICS:
From mv_clusters_daily_agg / UI daily SQL: views, clicks, add_to_cart, orders, cpm (weighted),
spend (derived in UI SQL), avg_pos (from clusters_adv_stats avgIf(avr_pos>0)).
From clusters_adv_stats raw (historical extractor): views, clicks, carts, orders, spend (column),
cpm, avr_pos, ctr, cpc.
From advkeyword_new (A1 script): views, clicks, spend (state merge).
Derived in KeywordDailyStat DTO: ctr, conv_views_to_cart, conv_cart_to_order, conv_views_to_order,
pay_for_order (CPO) — dto/keyword_daily_stat.py:32–65.
Not in existing AI export: window aggregates, change deltas, coverage.json, DATA_MAP.

QUERY_SPEND_SEMANTICS:
Owner decision (D-003): conservative factual-only export.
Three code paths (planning must reconcile, not re-ask Owner):
1) UI/history SQL: spend = sum(cpm0 * views0) / 1000.0 — get_keyword_daily_history.sql:20–21
   (DERIVED — NOT factual export).
2) Raw daily rollup: argMax(spend, timestamp) from clusters_adv_stats — adv_bot_historical_state_extractor.py:1011
   (FACTUAL when WB populates spend on ingest — convertor.py:42).
3) A1 compact export manifest: query_level_spend from mv_clusters_daily_agg status
   "UNAVAILABLE_NOT_DERIVED" — ch_a1_compact_export.py:633–636.
MV path does not expose spend_state; ingest may leave spend NULL while views/cpm exist.
Contract: spend_rub factual from clusters_adv_stats when non-null + proven lineage; else null/UNAVAILABLE;
CPO only when spend FACTUAL/DERIVED_VALID per DATA_MAP; never UI CPM×views as factual.

POSITION_SOURCE:
Canonical persisted (non-Telegram): clusters_adv_stats.avr_pos (MergeTree snapshots, WB normquery stats
via updater); keyword_position_from_api (ReplacingMergeTree versioned — stamp SQL + ch_a1 export);
keyword_stamp (today slice + join to keyword_position_from_api — get_keywords_stat.sql:9–33);
wbitemposition (promo/base/cpm/adv_type, timestamp grain — ch_a1_compact_export.py:574–578).
FORBIDDEN canonical source: app/utils/graphic_positions_creator/graphic_positions_creator.py:79–88
(nearest-day fill + random jitter for chart), get_position_history.sql:13–14 (zero → max_pos substitution).

POSITION_SEMANTICS:
Owner decision (D-004): preserve observed source position_type; no organic claim unless proven.
clusters_adv_stats.avr_pos: WB normquery cluster average position (advertising/search cluster stat context).
keyword_position_from_api.avr_position: WB analytics keyword position API lineage.
get_position_history labels output as organic-style UI series but uses clusters_adv_stats with zero→max_pos
(position_history_manager SQL — not organic-specific, FORBIDDEN for export).
Position direction: lower avg_pos = better (graphic creator invert_yaxis:114); MUST document in DATA_MAP.
Missing handling in UI daily history: coalesce(..., 0.0) AS avg_pos — get_keyword_daily_history.sql:65
(violates missing ≠ zero — export MUST NOT follow).

POSITION_HISTORY_AVAILABLE:
Code-proven read paths exist for daily position (clusters_adv_stats, keyword_position_from_api) and
multi-day series (PositionHistoryManager, KeywordDailyHistoryManager position_by_day CTE).
Full shop-wide position history export: not in ExportService; partial in scripts only.
Live depth: NOT OBSERVED.

BID_HISTORY_AVAILABLE:
default_db.bid_decision_log — read SQL in app/modules/keyword_bid_from_log, predict_keywords_target_place,
raise_card_analyze; populated/refreshed by scripts/fill_bid_decision.py from clusters_adv_stats (derived pipeline).
scripts/ch_a1_compact_export.py exports bot_bid_decision_history.jsonl.
Join keys: adv_id, nmid, norm_query — compatible with cluster stats when proven.
Owner decision (D-009): derived log ≠ executed bid history; label as DECISION not ACTION.
Availability in prod: code-capable; fill job presence not verified without DB.

DECISION_HISTORY_AVAILABLE:
bid_decision_log fields include cpm_curr/prev, pos_*, final_bid, decision_source, decision_time
(fill_bid_decision.py:45–66). V3 UI decision trace is Telegram presentation — not export authority.
keyword_stamp: observation snapshots (CPM/position-related), not labeled DECISION/ACTION separation.

REBIND_HISTORY_SUPPORT:
Owner decision (D-005): rebind sets prove membership only; no guessed transition dates/intervals.
Redis sets via RebindWbAdvIdsHistory — rebind_wb_adv_ids_history.py:19–63;
get_rebound_wb_adv_ids(adv_setting.id) returns historical auto/auction adv_ids.
KeywordDailyHistoryManager._collect_adv_ids:140–150 includes rebound IDs in CH filters.
ExportScopeAdv / collect_scoped_adv_ids does NOT include rebound IDs — scope_collect.py:10–17
(GAP: AI export must extend scope for full keyword history).
common_stat_data_manager dedupes auto∩auction to avoid double-count:188–189.

AUTO_SEARCH_IDENTITY:
Owner + existing v1: ExportScopeAdv separate auto_adv_id/search_adv_id; assert_no_synthetic_merge in
export_service.py:176–185; grain-preservation spec (openspec/specs/grain-preservation/spec.md).
Keyword daily UI SQL merges all adv_ids — forbidden for export.
get_clusters_stats.sql aggregates by nmid × text across adv_ids — not export authority.

CURRENT_STATE_SOURCE:
mv_clusters_last_state — last_avg_pos, last_cpm, last_ts per nmid × text (destructive_ch_reset.py:285–307).
get_clusters_stats.sql last_state CTE:61–69.
CalculatedKeywordsManager / KeywordStat — runtime ranking for bot, not export DTO.
bid_decision_log get_latest_keyword_bids.sql — latest cpm_curr per adv_id × norm_query.
No keyword_current_state dataset in AI package today (greenfield D-008).

EXISTING_DAILY_HISTORY_IMPLEMENTATION:
KeywordDailyHistoryManager (CH, paginated 7-day default) — keyword_daily_history/.
Telegram: keyword_daily_history_message.py, KeywordsDailyStatsScreen → CommonStatDataManager (14-day pages).
Scripts: adv_bot_historical_state_extractor export_keyword_daily / export_keyword_intraday.
Not wired to ExportService.

EXISTING_WINDOWS_IMPLEMENTATION:
None matching Owner catalog (1d/3d/7d/…/all_available, MTD/QTD/YTD, prev comparable).
Partial: get_clusters_stats.sql agg_stats 7-day block:75–85; date_pagination page_size 7/14;
ExportPeriod only start/end inclusive — export_period.py:8–15.
Window metrics + keyword_changes dataset: greenfield (D-007).

VOLUME_ESTIMATE:
NOT QUANTIFIED (no CH/PG reads). Structure: intraday clusters_adv_stats is multi-row per day per key;
daily export should prefer MV or argMax daily rollup. Full-history JSONL may require chunking by year/resource
(Owner §20); cardinality scales with |scope adv_ids| × |nmids| × |queries| × |days|.

PROPOSED_DATASETS:
Integrate under ExportService (alongside campaign_settings_snapshot):
keyword_performance/keyword_daily.jsonl — adv_id grain from historical extractor pattern;
keyword_windows.jsonl; keyword_current_state.jsonl; keyword_changes.jsonl;
keyword_positions.jsonl (optional split for position_type/source);
coverage.json + DATA_MAP.json (new root; manifest today is manifest.json only — domain/manifest.py).

PROPOSED_DATA_MAP_ADDITIONS:
New root DATA_MAP.json per Owner §18 / D-006. Reuse ai_package_v1 coverage enums —
domain/coverage_rules.py + openspec/specs/coverage-provenance/spec.md. Document: grain, join keys
(shop_id, auto_adv_id, search_adv_id, adv_id, nmid, norm_query), QUERY_SPEND_STATUS, position_type,
missing vs zero, rebound adv_id provenance, calendar vs rolling windows, ExportPeriod vs all_available bounds.

PROPOSED_WINDOWS:
Deterministic window engine in ai_package_v1 (new module); inputs = keyword_daily facts +
first_available/last_available from CH MIN/MAX queries per scope; emit partial coverage when history
shorter than window. Owner catalog D-007.

COVERAGE_MODEL:
Reuse v1 four dimensions (collection_outcome, coverage, reason_codes, freshness) —
coverage-provenance spec + coverage_rules.py. Extend with Owner fields: requested/returned/observed/
missing/confirmed_zero/unsupported/failed, first_available/last_available, observed_days/missing_days for windows.
Missing row ≠ zero — must not follow UI coalesce(avg_pos,0) or graphic zero→max_pos.
Expose unsupported/failed/ambiguous joins explicitly (D-006).

KNOWN_GAPS:
- OpenSpec change scaffold created; planning artifacts pending.
- No production CLI script for v1 export in repo (ADR names scripts/ai_package_v1_export.py).
- No DATA_MAP.json / keyword datasets in ExportService.
- No analytical windows / keyword_changes implementation.
- ExportScopeAdv lacks AdvSetting.id → rebound Redis history not on AI export path (D-005 gap).
- norm_query vs keyword_setting.text collision; no shared normalizer in export path.
- Live CH retention and bid_decision_log completeness unknown without reads (D-013).
- Time boundary: UI uses server local date; ch_freshness_reader UTC EOD — design resolves (D-011).

OWNER_DECISIONS_REQUIRED:
None — Owner prompt and owner-contract.md D-001..D-013 record normative semantics.
Planning resolves evidence-backed source selection (spend column vs MV, timezone from CH date + UTC export)
without re-asking resolved product decisions.

GO_TO_IMPLEMENTATION_PLANNING:
YES
(Rich code evidence, clear ExportService seam; Owner decisions explicit in owner-contract.md.)
```

## Code evidence index

| Topic | Path | Lines (approx) |
|-------|------|------------------|
| ExportService authority | `app/modules/ai_package_v1/export/export_service.py` | 69–257 |
| UI daily SQL (forbidden rollup) | `app/modules/keyword_daily_history/sql/get_keyword_daily_history.sql` | 13–68 |
| Rebound adv_ids | `app/modules/rebind_wb_adv_ids_history/rebind_wb_adv_ids_history.py` | 19–63 |
| Graphic jitter (forbidden) | `app/utils/graphic_positions_creator/graphic_positions_creator.py` | 79–88 |
| Zero→max_pos (forbidden) | `app/modules/position_history/sql/get_position_history.sql` | 13–14 |
| A1 spend UNAVAILABLE | `scripts/ch_a1_compact_export.py` | 633–636 |
| Historical daily grain | `scripts/adv_bot_historical_state_extractor.py` | 1000–1018 |
| CH MV DDL | `tests/support/destructive_ch_reset.py` | 252–307 |
| ADR exporter ownership | `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | — |
| norm_query collision | `app/modules/update_cluster_bids_manager/update_cluster_bids_manager.py` | 659–664 |
| Scope without rebound | `app/modules/ai_package_v1/export/scope_collect.py` | 10–17 |

## Receipt cross-reference

Source inventory run: `C:\Users\vkita\my_code\cursor-sdk-task-runner\runs\WB-SKY-KEYWORD-HISTORY-INVENTORY-20261005-0054-R2\result.json`

Corrections applied vs raw inventory assistant output:

- `BASE_HEAD` verified to `37d0ec5fce9acae46eb0b35dda7c0fea7b9845a0` (was "Local committed stage" without SHA).
- `OWNER_DECISIONS_REQUIRED` cleared — decisions captured in `owner-contract.md` D-001..D-013.
- Strict adv_id+leg grain, full history independent of ExportPeriod, conservative spend, rebind membership-only,
  DATA_MAP/coverage for failed joins — marked as Owner-normative, not open questions.
