# Leg CPO Consumer Inventory

Change: `separate-auto-search-cpo`

Purpose: bounded inventory of runtime-reachable factual CPO consumers after implementation. Structural leg identity is Auto=`adv_id`, Search=`search_adv_id`.

## SEARCH — migrated

- V3 keyword orchestration: `resolve_v3_fact_data` projects `search_fact_cpo` into the existing `FactData.pay_for_order`; downstream `AdvState.fact_pay_for_order` is therefore Search-scoped.
- Search common-bid updater reads `ComplexAdv.search_fact_cpo`.
- Bidder V3 safety cap reads `WBAdvDTO.search_fact_cpo`.
- Cluster-bid safety cap replaces aggregate fact CPO with snapshot `search_cpo`.
- A/B Hold deep-overspend keyword protection reads `ComplexAdv.search_fact_cpo`.

## AUTO — migrated

- Auto Shelf Bid Control dynamic metric, cycle fallback and exhausted coverage use `ComplexAdv.auto_fact_cpo`.
- Auto Shelf read/view and Telegram refresh load exact-leg Auto CPO; aggregate fact remains only a compatibility field and is not the factual decision input.
- Auto activity watchdog confirms cost decisions with `auto_fact_cpo`.
- Shared auto campaign cost-activity uses `complex_adv.auto_fact_cpo` whenever a runtime `ComplexAdv` is supplied; production control callers supply it.

## Intentionally aggregate / compatibility

- `ComplexAdv.fact_pay_for_order` remains aggregate plan/fact for backward compatibility and aggregate reporting.
- `plan_fact_stats.fact_pay_for_order`, PlanFactReader and plan/fact storage remain aggregate and are not rewritten by this change.
- `AdvStrategySelector` remains aggregate-level campaign strategy logic.
- Existing campaign-level Fact-sales UI remains aggregate; explicit `CPO Auto` and `CPO Search` are rendered alongside it.
- `rec_system_shelf_mode.is_rec_system_shelf_mode_operational` may use the legacy aggregate-only helper path for read-only UI click-warning when no `ComplexAdv` is supplied; it is not a leg-level write decision.

## Forbidden fallback check

No migrated Search decision reads Auto/common CPO as a substitute for missing Search CPO. No migrated Auto decision reads Search/common CPO as a substitute for missing Auto CPO. Missing exact-leg rows remain `None`.
