## Why

AI Package multi-window analysis, Dynamic DRR / target CPO, and strict read-only
audits need **authoritative DIRECT vs LINKED** advertising attribution
(orders, GMV, CPO, DRR). Today WB promotion fullstats exposes nm-level
attribution in raw API trees, but the production mapper collapses `apps/nms` to
campaign-day `DayStats`, so ClickHouse `full_adv_wb_stat` cannot support
class-split economics. Consumers currently fail closed (`BLOCKED_BY_ATTRIBUTION_FACTS`).

## What Changes

- Introduce transport-independent **Attribution Commerce Facts** at grain
  `shop_id × physical_adv_id × event_date × app_type × ordered_nm_id`.
- **DIRECT** = `ordered_nm_id` ∈ as-of `promoted_nm_ids` for the physical adv
  and date; **LINKED** = attributed nm outside that set when membership is
  authoritative; **UNKNOWN** when membership missing/empty/ambiguous. No separate
  linked-assortment graph in V1.
- **Spend** remains canonical on existing `full_adv_wb_stat` (campaign-day);
  attribution facts MUST NOT duplicate spend ownership.
- Collector preserves raw fullstats `apps→nms` before collapsed mapper; membership
  resolver uses `campaign_settings_history` as-of precedence (ADR).
- `AttributionFactsReader` port for AI Package / AnalysisAggregationService /
  future MCP (transport not in this change).
- Derived metrics: `CPO_FACT_DIRECT`, `CPO_FACT_LINKED`, `DRR_FACT_DIRECT`,
  `DRR_FACT_LINKED` with fail-closed coverage and reconciliation gates.
- Buyout attribution **unsupported** in V1 (no factual nm-level source).

## Capabilities

### New Capabilities

- `attribution-facts-contract`: domain contract, collector ownership, observation
  store design, classification, reconciliation, coverage, reader port.

### Modified Capabilities

- (Future apply) `ai-package-v1-exporter` / multi-window analysis: consume reader
  port; remove `BLOCKED_BY_ATTRIBUTION_FACTS` when coverage `COMPLETE`.
- No delta to canonical specs in this planning hop beyond new change spec.

## Impact

- New module namespace `app/modules/attribution_facts/` (apply slices A–D).
- Shop-runner fullstats ingest seam (Slice B): preserve nm breakdown path.
- New CH observation table (Slice C): migration in separate control-plane GO.
- **Not in scope:** Dynamic DRR implementation, shop-wide DRR controller, MCP
  transport, ChangeSet Apply, production deploy.

## Out of scope

- Dynamic DRR / target CPO runtime
- Shop-wide capacity controller
- MCP read interface transport changes
- ChangeSet Apply Authority
- Supplier orders / `wb_common_stat` as attribution denominators
- Linked-assortment catalog beyond factual WB associated conversions
- Production deployment and WB writes

## Risk

- Historical membership gaps → prolonged `UNKNOWN` / fail-closed economics until
  `campaign_settings_history` backfill sufficient.
- Auto+Search pair rollups may double-count without explicit overlap proof.
- Mapper change must not break existing `full_adv_wb_stat` campaign-day writer.

## Rollback idea

Planning: remove change directory. Post-apply: disable collector observation
writes; consumers revert to `BLOCKED_BY_ATTRIBUTION_FACTS`; CH observations
retained read-only.
