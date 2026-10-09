# Design — attribution-facts-contract

## Architecture Decision References

| Decision | Role |
|---|---|
| `openspec/decisions/shop-data-source-strategy/decision.md` | Accumulated PG/CH read path; grain preservation; four completeness dimensions; no silent metric substitution |
| `openspec/specs/grain-preservation/spec.md` | Physical Auto/Search adv_id rows; no silent leg merge |
| `openspec/decisions/ai-package-v1-exporter-ownership/decision.md` | Consumers read via dedicated modules; export MUST NOT own collectors |
| `openspec/decisions/strict-single-nmid-audit-evidence/decision.md` | Direct vs associated evidence; single canonical physical spend; honest GAP |
| `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` | Supplier orders MUST NOT substitute adv attribution |
| Proposed: `decisions/attribution-facts-collector-ownership/decision.md` | Collector placement, nm preservation, membership precedence, versioning |

Canonical specs consumed: `coverage-provenance`, `grain-preservation`.

## Ownership & Placement

| Concern | Owner | Layer |
|---|---|---|
| Attribution domain contract | `app/modules/attribution_facts/` | Pure domain + ports |
| Raw fullstats nm preservation | Shop-runner collect seam OR dedicated collector in `attribution_facts` ingest (ADR) | Write path adjacent to existing fullstats fetch |
| Membership as-of resolver | `attribution_facts` (reads CH history + bounded inventory fallback) | Read-only derivation |
| Campaign-day spend | Existing `full_adv_wb_stat` writer | **Not** attribution module |
| CH observation persistence | `attribution_facts` repository (Slice C) | CH insert; migration separate GO |
| AI Package / analysis consumption | `ai_package_v1` analysis layer via `AttributionFactsReader` | Read-only port |
| Derived CPO/DRR in windows | `AnalysisAggregationService` (future apply) | Uses reader + spend join |

Checklist:

- [x] Context-first decision lookup performed.
- [x] Relevant accepted decisions cited by path.
- [x] New decision proposed: `attribution-facts-collector-ownership`.
- [x] Implementation layer matches decision (domain module + collector seam; not LLM/MCP).

## Canonical grain and key

**Grain:** `shop_id × physical_adv_id × event_date × app_type × ordered_nm_id`.

**Fact key fields:**

- `shop_id`, `source_family=WB_PROMOTION_FULLSTATS_NM_DAY`, `physical_adv_id`,
  `event_date`, `app_type`, `ordered_nm_id`, `observation_id` (content hash).

**Explicitly excluded from key:**

- `advertised_nm_id` — not authoritative on nm rows; multi-nm campaigns use promoted **set**.
- `order_id` / `click_id` — not in WB fullstats nm tree (MISSING).
- `campaign_leg_role` — join attribute via `adv_id` → ComplexAdv; avoids duplicate keys.

**Double-count prevention:**

- Facts stored per **physical** adv_id (Auto ≠ Search).
- Revisions: append observation → latest projection replaces; never add revisions.
- CPO/DRR numerators: one spend read per `(physical_adv_id, event_date)` from `full_adv_wb_stat`.
- ComplexAdv pair totals: opt-in aggregate only with overlap proof; else `ATTRIBUTION_SCOPE_MISMATCH`.

## Classification

| Class | Rule |
|---|---|
| DIRECT | `ordered_nm_id ∈ promoted_nm_ids` from covering `MembershipSnapshot` |
| LINKED | snapshot covers date, promoted set non-empty, nm row exists, `ordered_nm_id ∉ promoted_nm_ids` |
| UNKNOWN | membership missing/empty/ambiguous |
| UNATTRIBUTED | day-level reconciliation gap (synthetic); not a per-nm class |
| UNSUPPORTED | consumer requests unsupported metrics (e.g. buyouts at nm grain) |

No LINKED→DIRECT fallback. Missing facts ≠ zero.

## Membership authority

Precedence (normative):

1. `default_db.campaign_settings_history` — latest `observed_at` ≤ end of `event_date` per `adv_setting_id`; parse `nmids` from `payload_json`.
2. `default_db.shop_campaign_inventory.nm_ids` — fallback when history does not cover date (weaker; marks coverage PARTIAL if used).
3. WB `nm_settings` at observation persist time — embedded in observation provenance.

Map `physical_adv_id` → `adv_setting_id` via PG inventory / history columns (`adv_id`, `search_adv_id`).

## Raw vs derived

**Raw (on grain):** `attributed_orders`, `attributed_gmv_rub`, optional `attributed_atc`, `attributed_units_shks`, optional diagnostic `attributed_nm_spend_rub` (not CPO numerator).

**Derived (window scope):** `CPO_FACT_DIRECT`, `CPO_FACT_LINKED`, `DRR_FACT_DIRECT`, `DRR_FACT_LINKED` using joined campaign-day spend.

**Unsupported V1:** `attributed_buyouts`, `attributed_buyout_gmv_rub`.

## Versioning and corrections

- Append-only observations with `observation_id`, `source_revision`, `ingested_at`.
- Latest projection: `argMax` by `(source_revision, ingested_at)` per fact key.
- Late WB restatement → new observation; replay rebuilds windows from latest-per-day.

## Coverage model

Independent axes per `coverage-provenance`: `collection_outcome`, `coverage`,
`reason_codes[]`, `freshness`.

Attribution `coverage_status`: `COMPLETE` | `PARTIAL` | `NO_DATA` | `UNSUPPORTED` | `UNKNOWN`.

`package_cutoff_date` MUST NOT imply `COMPLETE`. Require `source_complete_through`
per scope.

## Reconciliation

Per `(physical_adv_id, event_date)` when `COMPLETE`:

- Σ nm `attributed_orders` = campaign-day `orders`
- Σ nm `attributed_gmv_rub` ≈ day `sum_price_orders` (ε in spec)
- Σ DIRECT + Σ LINKED + UNATTRIBUTED = day orders (when UNATTRIBUTED bucket used)

MUST NOT reconcile to supplier orders or `wb_common_stat`.

## Reader port

```text
AttributionFactsReader.query(scope, window) → AttributionQueryResult
  facts: Sequence[AttributionCommerceFact]
  coverage: AttributionCoverage
  reconciliation: Sequence[AttributionDayReconciliation]
```

Spend via separate `CampaignDaySpendReader` or embedded join metadata — not duplicated in fact rows as authority.

## Physical storage (logical first)

- Observation log + latest projection (CH MergeTree candidate in Slice C).
- DDL is not the domain contract.

## Out of scope (design)

Dynamic DRR, shop-wide DRR controller, MCP transport, Apply, unrelated collectors, deploy.
