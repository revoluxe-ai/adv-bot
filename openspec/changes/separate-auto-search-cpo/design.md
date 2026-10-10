## Context

Существующий `plan_fact_stats.fact_pay_for_order` является aggregate-фактом комплекса: incremental snapshot собирает рекламный spend по `ComplexAdv.all_adv_ids` и сохраняет результат под anchor Auto id. Этот факт нужен aggregate plan/fact и не удаляется.

При этом ClickHouse `full_adv_wb_stat` уже хранит статистику отдельно по каждому `adv_id`; `CommonAdvsStatDataManager` уже читает Auto и Search раздельно для paid UI. Проблема находится не в отсутствии данных, а в том, что leg-level consumers получают aggregate `fact_pay_for_order`.

Change cross-cutting: затрагивает read-model экономики, runtime DTO, Search/V3 consumers, Auto shelf/activity consumers и paid UI. Нового WB write-path, таблицы, Redis SoT или миграции не вводится.

## Goals / Non-Goals

**Goals:**
- сохранить aggregate CPO для aggregate plan/fact;
- ввести один shared leg-CPO read contract для Auto и Search;
- передавать Auto CPO только Auto consumers, Search CPO только Search consumers;
- показать оба leg CPO в paid UI из той же семантики;
- fail closed на missing leg CPO без cross-leg fallback;
- закрыть runtime-reachable CPO consumers paired regression tests.

**Non-Goals:**
- не менять Target/Max/resolve CPO;
- не менять attribution WB;
- не менять campaign linking, budgets, billing и Free/Paid guards;
- не переписывать алгоритмы выбора ставок, кроме замены неверного fact input.

## Architecture Decision References

- `openspec/decisions/billing-fair-leg-metering-write-path/decision.md` — Accepted; structural Auto anchor / linked Search identity, WB type 8/9 forbidden as role authority.
- `openspec/decisions/auto-bid-module-coexistence-write-path/decision.md` — Accepted; Auto bid writer coexistence remains unchanged.
- `openspec/decisions/auto-shelf-exhausted-pause-write-path/decision.md` — Accepted; Auto shelf/activity ownership and Search non-effect remain unchanged.
- `openspec/changes/separate-auto-search-cpo/decisions/leg-cpo-economics-ownership/decision.md` — Proposed; new reusable leg-CPO ownership and cross-leg fallback ban.

## Ownership & Placement

Canonical leg-CPO calculation belongs to a shared read-only economics provider near WB advertising statistics, not to UI and not to any write adapter.

Source data remains `full_adv_wb_stat`, keyed by concrete `adv_id`. The provider returns a typed `LegCpoSnapshot` containing Auto/Search values plus explicit observation-window metadata. It MUST NOT persist state.

`ComplexAdv` is the runtime carrier for `common_fact_cpo` (existing aggregate semantic) plus explicit `auto_fact_cpo` and `search_fact_cpo`. Existing `fact_pay_for_order` remains aggregate for compatibility; leg-level consumers MUST migrate to explicit leg fields.

`WBAdvDTO` exposes explicit Auto/Search CPO accessors backed by the same attached snapshot. Search writers MUST NOT infer Search CPO from `dto.fact.pay_for_order`.

Allowed: shared read provider, runtime DTO projection, Auto/Search consumers, read-only UI rendering.
Forbidden: leg calculations inside Telegram renderers, changing plan-fact storage into leg SoT, cross-leg fallback, WB type-based routing.

## Decisions

### 1. Preserve aggregate plan/fact and add leg read-model beside it

Chosen: do not modify `fact_stat_states` / `plan_fact_stats` schema in this change. Aggregate CPO remains authoritative only for aggregate campaign plan/fact semantics.

Rationale: smallest safe change; current bug is consumer coupling, not absence of per-leg raw data. Rebuilding incremental storage would enlarge migration and rollback risk.

Alternative rejected: split the existing incremental plan/fact tables per leg now. It would solve more than the requested coupling and require new persistence/migration/recovery semantics.

### 2. Observation window is explicit and shared per snapshot

The provider accepts an explicit window instead of hiding a period inside the DTO. For current paid Search/V3/UI flows the initial control window is two calendar days, matching the existing `PlanFactProvider/CommonAdvsStatDataManager` control/UI horizon.

Auto and Search values inside one snapshot MUST use the same start/end dates.

CPO formula: `spend / max(orders, 1)`, preserving the existing denominator floor. A missing Search leg returns `None`; it MUST NOT produce a synthetic zero or a neighboring CPO.

Alternative rejected: use `get_additional_cost_per_order_for_adv` as Auto leg CPO. That function intentionally subtracts keyword traffic from Auto and therefore represents recommendation/shelf traffic, not the whole Auto campaign leg requested by Owner.

### 3. Batch reads for shop-runner, reuse already-loaded stats in UI

For orchestration that already has a list of `ComplexAdv`, leg CPO is attached in one batch read grouped by `adv_id`, avoiding per-campaign additional CH queries.

Where `CommonAdvsStatDataManager` already loaded exact Auto/Search stats for UI/DTO construction, the same pure CPO helper is applied to those stats instead of querying again.

No UI-local business formula is allowed: the helper and typed snapshot define the calculation contract.

### 4. Consumer classification is explicit

Search leg consumers to migrate include:
- V3 keyword state/calibration/overspend decisions;
- ordinary Search common-bid updater;
- V3 bidder safety cap;
- cluster-bid safety cap;
- A/B Hold keyword overspend protection.

Auto leg consumers to migrate include:
- Auto Shelf Bid Control fact-CPO input and its view/read model;
- Auto campaign cost/activity confirmation paths that currently combine Auto-specific average cost with aggregate fact CPO.

Aggregate consumers such as campaign-level plan/fact reporting and campaign strategy selection remain on the existing aggregate fact unless repository evidence proves that a specific decision belongs to one leg.

### 5. Missing-data behavior is fail-closed for leg control

If a leg CPO cannot be produced reliably, that leg's CPO-dependent destructive decision MUST NOT borrow aggregate or sibling CPO. Existing non-CPO gates may continue according to their own contracts.

This change does not invent a generic global “keep everything” fallback. Each migrated consumer must distinguish `None` from a valid number and preserve its existing safe missing-data behavior.

### 6. UI projection

The paid keyword/campaign screen will show explicit labels `CPO Auto` and `CPO Search`. If a value is unavailable, render a clear unavailable marker instead of another CPO.

The existing shelf recommendation rows keep their expected per-bid CPO. Where the shelf control screen shows factual campaign economics, factual CPO must be the Auto leg CPO, not aggregate plan/fact CPO.

### 7. Product Acceptance and evidence

`PRODUCT_ACCEPTANCE_REQUIRED: true` because the change alters inputs to paid automation with multiple competing legs.

MEANING_LOCK is resolved by the explicit SWT block in the proposed decision.

The change is not a new temporal state machine; Derived Lifecycle is not required. Lifecycle behavior of existing writers remains unchanged.

SIDE_EFFECT_PROOF is provided by paired orchestration/component regressions proving intended leg input plus forbidden sibling non-effect. Existing WB adapters remain mocked only after the CPO-selection boundary; tests MUST exercise the real selection/wiring path.

## Risks / Trade-offs

- [Hidden aggregate consumer remains] → maintain a bounded inventory of runtime-reachable `fact_pay_for_order` consumers and classify each as aggregate, AUTO or SEARCH before completion.
- [Two-day calendar window differs from incremental aggregate timing] → window is explicit and identical for both legs; aggregate plan/fact remains untouched. A future change may add per-leg incremental snapshots if needed.
- [CH query amplification] → batch exact-leg reads in shop-runner; reuse already-loaded UI stats.
- [Zero orders make CPO numerically equal spend] → preserve current denominator-floor semantics in this change; changing zero-order policy requires a separate product decision.
- [Legacy code paths] → retired/no-op V2 writers are not revived or redesigned; runtime-reachable paid paths are the acceptance boundary.

## Migration Plan

1. Add the shared pure CPO calculator, typed leg snapshot, and batch CH read without changing existing aggregate fields.
2. Attach explicit Auto/Search CPO to runtime DTOs and update read-only UI projection.
3. Switch Search runtime consumers to Search CPO with paired regressions.
4. Switch Auto runtime consumers to Auto CPO with paired regressions.
5. Run targeted and adjacent tests, strict typing, diff checks, then independent verify.
6. Rollback by reverting explicit leg fields/provider wiring and consumer switches; aggregate plan/fact remains unchanged throughout.

No database migration, Redis migration, production backfill, or dual-write period is required.

## Open Questions

None implementation-critical.

## DESIGN_READINESS

```text
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: not_applicable
DURABLE_SOT_RESOLVED: not_applicable
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: not_applicable
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
REASON: none
```

No new durable state is introduced; the canonical persisted sources remain existing WB advertising statistics and aggregate plan/fact stores. This design only changes read-model ownership and consumer routing.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
