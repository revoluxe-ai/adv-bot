# Decision: Attribution facts collector ownership

## Status

Proposed

## Context

WB promotion GET `/adv/v3/fullstats` provides `days→apps→nms` with per-`nmId`
orders and GMV. Production path maps API days to `DayStats` without `apps`
(`app/core/mp/wb/api/adapter/promotion_client/fullstats/mapper.py`; `DayStats.apps`
commented out). `full_adv_wb_stat` stores campaign-day aggregates only.

AI Package multi-window analysis and strict audits require persisted DIRECT/LINKED
facts with as-of membership. Without a reusable ADR, nm preservation could land in
export scripts, collapsed mapper, or prompt-only JSON — violating
`grain-preservation` and `shop-data-source-strategy`.

Accepted decisions bound spend (`full_adv_wb_stat`), export read-only
(`ai-package-v1-exporter-ownership`), and honest attribution gaps
(`strict-single-nmid-audit-evidence`) but do not assign collector ownership.

## Decision

1. **Domain owner** — `app/modules/attribution_facts/` owns transport-independent
   contract types, classification, reconciliation pure functions, coverage
   semantics, and `AttributionFactsReader` port. AI Package and MCP MUST consume
   the port, not CH SQL directly.

2. **Collector owner** — Attribution observation ingest MUST live in
   `app/modules/attribution_facts/ingest/` (or `collector/`) invoked from the
   existing shop-runner fullstats fetch seam. It MUST preserve raw `apps/nms`
   **before** `FullAdvStat` / `DayStats` collapse. The collapsed mapper MUST NOT
   be the sole source of nm facts.

3. **Physical adv_id grain** — Observations MUST be keyed by WB `advertId`
   (physical adv_id). Auto and Search remain separate adv_ids; leg role is a join
   attribute, not a duplicate fact key.

4. **Membership snapshot precedence** (as-of `event_date`):
   1. `default_db.campaign_settings_history` — latest snapshot with
      `observed_at` ≤ end of event day for `adv_setting_id`; `promoted_nm_ids`
      from normalized `payload_json.nmids`.
   2. `default_db.shop_campaign_inventory.nm_ids` — only when history does not
      cover the date; coverage MUST be `PARTIAL` and `reason_codes` MUST include
      `ATTRIBUTION_RELATION_UNKNOWN` or partial membership code.
   3. Collect-time WB `nm_settings` ids — stored in observation provenance when
      persisting; not a substitute for historical as-of without history row.

5. **Historical classification** — DIRECT/LINKED MUST use as-of membership for
   `event_date`, not current PG `AdvSetting.nmids` alone. Missing/empty/ambiguous
   membership → class `UNKNOWN`; DIRECT/LINKED economics fail closed.

6. **Spend authority** — Canonical spend remains `default_db.full_adv_wb_stat`
   (campaign-day). Attribution module MUST join spend; MUST NOT write authoritative
   spend duplicates into attribution fact tables.

7. **Versioning** — Append observations; dedupe by `(fact_key, observation_id)`.
   Latest projection selects max `(source_revision, ingested_at)`. Corrections MUST
   replace prior latest, never sum old+new for the same fact key.

8. **Reconciliation** — Before marking day `COMPLETE`, ingest MUST verify nm sums
   match campaign-day totals from the same fullstats payload. Failure →
   `RECONCILIATION_FAILED`, UNATTRIBUTED bucket or fail-closed per spec.

9. **Coverage** — Four dimensions independent (`coverage-provenance`).
   `package_cutoff_date` MUST NOT imply attribution completeness.
   DIRECT/LINKED numeric metrics require `COMPLETE` + reconciliation PASS.

10. **Fail-closed** — Emit reason codes including `ATTRIBUTION_SOURCE_MISSING`,
    `ATTRIBUTION_SOURCE_PARTIAL`, `ATTRIBUTION_RELATION_UNKNOWN`,
    `ATTRIBUTION_CAMPAIGN_LEG_AMBIGUOUS`, `ATTRIBUTION_ORDER_IDENTITY_AMBIGUOUS`,
    `ATTRIBUTION_VERSION_AMBIGUOUS`, `ATTRIBUTION_SCOPE_MISMATCH`,
    `ATTRIBUTION_UNSUPPORTED`. Missing attribution ≠ zero.

11. **V1 linked semantics** — LINKED = factual non-promoted `ordered_nm_id` in WB
    attributed nm breakdown. No separate linked-assortment graph is required.

12. **Pair aggregation** — Summing Auto+Search legs for one ComplexAdv MUST be
    opt-in and fail-closed without overlap proof (`ATTRIBUTION_SCOPE_MISMATCH`).

## Applies to

- Change `attribution-facts-contract` and apply slices A–D
- Shop-runner fullstats collect seam (read/write attribution observations only)
- `AnalysisAggregationService` / AI Package attribution metrics
- Future archive promotion to `openspec/decisions/`

## Allowed

- New CH observation table + latest projection (Slice C; migration control plane)
- Unit tests with in-memory reader fake (Slice A)
- Bounded use of `shop_campaign_inventory` when history gap documented
- Diagnostic nm-level spend on observation row (not CPO numerator)
- Scripts evidence collectors as reference only; not production SoT

## Forbidden

- Using collapsed `DayStats` / `full_adv_wb_stat` orders as nm attribution SoT
- Inferring LINKED from campaign-day totals without nm breakdown
- LINKED→DIRECT fallback
- Supplier orders / funnel `wb_common_stat` as adv attribution source
- Placing attribution ZIP encoding in shop-runner or ai_package export assembler
- AI as production-write authority; Apply from attribution module
- Merging Auto+Search adv rows into one synthetic adv_id
- Summing revision observations for the same fact key
- Treating package cutoff as source completeness

## Examples

Good: ingest stores nm row `(adv_id=123, date, app_type, ordered_nm_id)` with
observation hash; classifier uses history snapshot for that date; CPO joins spend
from `full_adv_wb_stat` once.

Bad: classify DIRECT by matching single `main nmid` heuristic; add associated
orders from campaign-day total minus direct; persist attribution only in AI ZIP.

## Related specs

- `openspec/changes/attribution-facts-contract/specs/attribution-facts-contract/spec.md`
- `openspec/specs/grain-preservation/spec.md`
- `openspec/specs/coverage-provenance/spec.md`

## Related changes

- `attribution-facts-contract` (this change)
- Consumer: `ai-package-multi-window-analysis` (blocked until facts COMPLETE)

## Review checklist

- [x] Existing decisions searched and cited
- [x] New decision proposed for collector/nm preservation gap
- [x] Implementation layer matches decision
- [ ] Promoted to `openspec/decisions/` on archive (future)
