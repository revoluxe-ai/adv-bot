# Owner Contract — attribution-facts-contract

## Что хотим получить

Authoritative, persisted **DIRECT** and **LINKED** advertising attribution facts
(orders, GMV, and derived CPO/DRR) keyed by physical WB `adv_id`, with
deterministic as-of membership classification and fail-closed coverage.

## Зачем

Unblock AI Package multi-window economics, future Dynamic DRR / target CPO, and
strict audits without inferring attribution from campaign-day totals or supplier
orders.

## Owner architecture decision (accepted)

**DIRECT:** attributed `ordered_nm_id` ∈ as-of `promoted_nm_ids` for
`(shop_id, physical_adv_id, event_date)`.

**LINKED:** attributed `ordered_nm_id` ∉ that promoted set when membership
snapshot is authoritative and complete.

**No** separate predeclared linked-assortment graph in V1.

If promoted membership is missing, empty, or ambiguous → **UNKNOWN**; DIRECT/LINKED
numeric economics MUST fail closed. No fallback LINKED→DIRECT.

## Что должно остаться неизменным

- Canonical **campaign-day spend** owner: `default_db.full_adv_wb_stat` /
  shop-runner insert path (`openspec/decisions/shop-data-source-strategy`).
- **Physical adv_id** grain; Auto and Search MUST NOT merge silently
  (`openspec/specs/grain-preservation`).
- AI export read-only boundary (`openspec/decisions/ai-package-v1-exporter-ownership`).
- Supplier ORDERS/SALES family identity (`orders-or-sales-reports-read-identity`).
- WB Sky production write authority (collectors accumulate facts; no Apply).

## Контрактные инварианты

- `advertised_nm_id` is **not** part of the canonical fact key.
- Revisions replace via latest projection; never sum old+new observations for the same key.
- Campaign-day spend joined **once** per `(physical_adv_id, event_date)` for CPO/DRR.
- Pair-level Auto+Search aggregation is opt-in and fail-closed without overlap proof.
- Missing attribution is not zero.
- Package cutoff does **not** imply attribution source completeness.
- DIRECT/LINKED numeric metrics require `COMPLETE` coverage and reconciliation PASS.
- Denominator zero → absent metric + `DENOMINATOR_ZERO`.
- No reconciliation to supplier orders or `wb_common_stat` for adv attribution.

## Membership precedence (locked)

1. `campaign_settings_history` as-of snapshot (`payload_json` → `nmids`).
2. `shop_campaign_inventory.nm_ids` — bounded fallback only.
3. Collect-time WB `nm_settings` when persisting observations.

Missing historical membership → `ATTRIBUTION_RELATION_UNKNOWN`.

## Чего сейчас не делаем

- Dynamic DRR implementation
- Shop-wide DRR capacity controller
- MCP transport changes
- ChangeSet Apply
- Unrelated collectors
- Production deployment

## Implementation slices (apply order)

- **A:** Domain + classification/reconciliation + `AttributionFactsReader` port + unit tests.
- **B:** Raw fullstats apps/nms preservation + membership resolver.
- **C:** CH observation store + latest projection + backfill + CH reader.
- **D:** AI Package / `AnalysisAggregationService` consumption.

## Owner source

Planning package `attribution-facts-contract` + Owner GO to materialize OpenSpec
artifacts (this change). Implementation GO is a separate `/opsx-apply` decision.
