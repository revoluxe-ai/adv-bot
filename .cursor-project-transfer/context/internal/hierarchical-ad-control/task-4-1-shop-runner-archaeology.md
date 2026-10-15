---
cursor:
  subagentId: "bc-420909be-aefe-5d5a-8239-12327bd4dbd6"
---

# Task 4.1 — Runtime shop-runner integration archaeology

**Repo:** `/agent/repos/adv-bot` (stage). **Change:** `openspec/changes/hierarchical-ad-control-settings` task 4.1. **Read-only; no code edits.**

---

## 1. Shop-runner tick / evaluation entrypoints

### Production entry chain

| Step | Path | Symbol | Signature / role |
|------|------|--------|------------------|
| Process entry | `new_wb_shop_update_run.py` | `run_process()` | → `DIManager` / `AppContainer` → `run_process_func.run()` |
| Multi-shop loop | `app/modules/shop_runner/run_process_func.py` | `run()` | Creates `TasksManager`, `PlanFactReader`, `_run_shops_loop` |
| Per-shop task | `run_process_func.py` | `run_shop_task(shop_id, client_session, redis_manager, tasks_manager, plan_fact_reader)` | → `_run_shop_task` |
| Shop orchestration | `app/modules/shop_runner/wb_shop.py` | `WBShop.run(self) -> None` | `asyncio.TaskGroup` of `CoroutinesManager` while-coroutines |
| Coroutine host | `app/modules/shop_runner/service_manager/manager.py` | `class CoroutinesManager` | One instance per shop; `@while_coroutine_decorator` loops |

### Per-shop evaluation loops (representative)

| Coroutine | Decorator interval | Method | What it evaluates |
|-----------|-------------------|--------|-----------------|
| Auto settings / V3 | `@while_coroutine_decorator(5 * 60)` | `adv_settings_auto_update(self, only_bot_active: bool = False) -> None` | Loads `ComplexAdv` list → schedules `process_adv_v3` (and CardAbHold pipelines) via `run_tasks` |
| V3 tick (per campaign) | (called from above) | `process_adv_v3(complex_adv, *, wb_shop_data_manager, max_last_period: int = 2) -> None` in `orchestrator.py` | `DataUpdateManager.load` → pipeline → `ApplyManager` (writes) |
| Shop-wide unmanaged collect | `@while_coroutine_decorator(5 * 60, 1)` | `collect_shop_wide_campaign_advertising(self) -> None` | → `run_shop_wide_unmanaged_tick(...)` |
| Managed full adv stat | `@while_coroutine_decorator(5 * 60, 1)` | `update_full_adv_stat(self, only_bot_active: bool = False) -> None` | CH `full_adv_wb_stat` for loader `all_adv_ids` |
| Plan/fact | (separate coroutine) | `update_plan_fact_stats` | `PlanFactController` / `ComplexAdv` batch |
| Stats freshness | `StatsFreshnessManager.evaluate(complex_adv)` / `StatsFreshnessGuard.evaluate_batch` | Per-`ComplexAdv` freshness gate |

**`ComplexAdv`:** `app/modules/shop_runner/service_manager/wb_shop_data_manager/dto/complex_adv/complex_adv.py` — `class ComplexAdv`. Key: `shop_id`, `adv_id`, `all_adv_ids: set[int]`, `adv_setting_original_id`, `get_keywords()`, `bot_active`, `is_part_auto_setting_active`.

**`adv_settings_auto_update` flow (lines ~563–661 `manager.py`):**

1. Gate: `settings.AUTO_SETTING_ACTIVE`
2. `advs = await self._wb_shop_data_manager.get_complex_advs(only_bot_active=..., load_extras=False)`
3. Filter `bot_active`, `is_part_auto_setting_active`
4. CardAbHold branches → `process_ab_setup` / `process_ab_hold` / `process_ab_setup_then_epoch`
5. Else `CardAbHoldMode.OFF` → `functools.partial(process_adv_v3, adv, wb_shop_data_manager=self._wb_shop_data_manager)`
6. `await run_tasks(handlers, max_workers=..., tasks_manager=self._tasks_manager)`

**Legacy V2 `AdvControlSystem.process_adv`:** not referenced from `manager.py` today; V3 path is canonical for auto-update.

### Natural read-only hook for hierarchical ad-control diagnostics (no WB writes)

**Recommended primary seam (per-campaign, read-only):**

- **`process_adv_v3`** (`app/modules/shop_runner/service_manager/services/auto_updater_v3/orchestrator.py`) **after** `tick_data = await data_mgr.load(...)` and **before** `ApplyManager` / bootstrap actions.
- Rationale: already has `ComplexAdv`, loaded plan/fact/CH context, tick report collector; owner-contract forbids actuation in Slice 4.1; `AdControlDiagnosticsBuilder.build` is explicitly read-only.

**Secondary seam (shop tick, fan-out):**

- **`CoroutinesManager.adv_settings_auto_update`** — after `get_complex_advs`, loop campaigns to build `ResolverContext` + diagnostics once per shop tick (shop-level `ActualDrrObservation` may need a new reader port).

**Avoid for diagnostics-only:**

- `ApplyManager`, V3 pipeline executors, bidder, `update_cluster_bids` — production write paths.

**Ambiguity / blocker:** OpenSpec task 4.1 does not name the coroutine. Shop-level DRR vs per-`CampaignRef` diagnostics requires a product decision (`advert_id` = physical leg per `CampaignRef`).

---

## 2. `ad_control_settings` imports from `shop_runner`

```text
grep ad_control_settings app/modules/shop_runner → **no matches**
grep ad_control_settings under shop_runner path → **none**
```

**Confirmed:** zero imports of `app.modules.ad_control_settings` from `app/modules/shop_runner/**`.

---

## 3. `shop_campaign_inventory` loading

There is **no** symbol named `load_shop_campaign_inventory`. CH access is split by use case:

| Module | Function / class | Return type | Callers (production) |
|--------|------------------|-------------|----------------------|
| `app/modules/shop_runner/shop_wide_collection/inventory_route_read.py` | `async def load_inventory_route_snapshots(client, *, shop_id: str, adv_ids: Sequence[int]) -> dict[int, InventoryRouteSnapshot]` | Route epoch per adv | `unmanaged_orchestrator.py`, `route_transition_reconcile.py` |
| `app/modules/shop_runner/shop_wide_collection/inventory_upsert.py` | `async def upsert_discovered_shop_campaign_inventory(...) -> tuple[ShopCampaignInventoryWrite, ...]` | Written rows | `unmanaged_orchestrator.py` |
| `app/modules/attribution_facts/membership/inventory_ch_adapter.py` | `class ShopCampaignInventoryNmAdapter` — `async def nm_ids_for_adv(shop_id, physical_adv_id) -> tuple[int, ...] \| None` | nm_ids | Attribution ingest seam (`tick_wiring.py` wires adapter) |
| `app/modules/attribution_facts/ports/shop_campaign_inventory.py` | `ShopCampaignInventoryNmPort` (Protocol) | — | `membership/resolver.py`, `ingest/seam.py`, `ingest/shop_runner_hooks.py` |

**Not** `shop_campaign_inventory`: `app/modules/ai_package_v1/scope/pg_adv_setting_inventory_reader.py` — `PgAdvSettingInventoryReader.load_inventory(shop_id) -> list[AdvSetting]` (PG AdvSetting, AI Package scope).

**Ambiguity:** Task 4.1 “load inventory” likely means either CH `shop_campaign_inventory` (discovery/route/nm_ids) or PG managed campaigns via `get_complex_advs` — not a single loader today.

---

## 4. `full_adv_wb_stat` spend for a shop + date window

**Table:** `default_db.full_adv_wb_stat`. Queries are **always scoped by `adv_id IN %(adv_ids)s`**, not `shop_id` alone.

| Location | Function | Parameters | Aggregation |
|----------|----------|------------|-------------|
| `app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py` | `async def get_daily_stats_by_last_days(adv_ids: list[int], start_date: datetime, end_date: datetime) -> list[SmallFullAdvStatPerDay]` | Date window + adv id list | argMax per `(adv_id, date)`, then **SUM by date** across legs |
| Same file | `async def get_stats_by_last_days(adv_ids, start_date, end_date) -> SmallFullAdvStat` | Same | **Single window total** SUM spend/views/... across legs/days |
| `app/modules/shop_runner/shop_wide_collection/full_adv_read_latest.py` | read-latest per `(adv_id, date)` | adv_ids | Row-level, not shop rollup |
| `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater/click_house_control_spend_sum.py` | `async def get_sum_spend_for_complex_adv(adv_ids: list[int]) -> float` | adv_ids only (no date filter in SQL) | SUM spend by date groups — **legacy / odd GROUP BY date** |
| V3 calibration | `calibration_views_cache.py` | `all_adv_ids` window | SUM(views) from `full_adv_wb_stat` |
| AI Package | `app/modules/ai_package_v1/readers/ch_campaign_stat_reader.py` | campaign-scoped | Not whole-shop |

**Shop-wide spend:** compose `adv_ids` from union of `ComplexAdv.all_adv_ids` for the shop (managed loader) and/or inventory discovery set, then call `get_stats_by_last_days` / `get_daily_stats_by_last_days`.

---

## 5. `ReportsManager.get_supplier_orders`

| Item | Detail |
|------|--------|
| File | `app/core/mp/wb/api/domain_managers/reports/reports_manager.py` |
| Class | `ReportsManager` |
| Signature | `async def get_supplier_orders(self, *, date_from: str, flag: int \| None = 0) -> list[OrdersItem]` |
| Delegation | `SupplierOrdersSalesAdapter.get_supplier_orders` → generated `get_api_v1_supplier_orders` |
| Pagination | **Single HTTP page only.** Adapter docstring: *«Список OrdersItem одной страницы ответа (Stage A: без follow cursor)»* |
| Cursor | API contract: next page uses `dateFrom` = full `lastChangeDate` of last row (`get_api_v1_supplier_orders.py` comments). **Not implemented in app production path.** |

**`OrdersItem`** (`app/core/mp/wb/api/generated/reports/v1/reports_client/models/orders_item.py`):

- `price_with_disc` (JSON `priceWithDisc`)
- `srid`, `is_cancel`, `date`, `last_change_date` (`lastChangeDate`), `g_number` (`gNumber`)

**Multi-page collector:**

- **Production `app/`:** none — only scripts and tests.
- **Scripts:** `scripts/wb_api_readonly_ops/collect/orders_sales.py` → `_paginate_supplier_rows` with `extract_last_change_date`, `should_fetch_next_page`, cursor `date_from = new_cursor`.

```python
# scripts/wb_api_readonly_ops/collect/orders_sales.py (_paginate_supplier_rows)
while pages < max_pages:
    budget.consume()
    page = list(await fetch(date_from) or [])
    ...
    new_cursor = extract_last_change_date(page[-1])
    if duplicate or not should_fetch_next_page(...):
        break
    date_from = new_cursor
```

**`WBDataManager`:** `app/core/mp/wb/api/managers/wb_data_manager/wb_data_manager.py` — `async def get_supplier_orders(self, *, date_from: str, flag: int | None = 0) -> list[OrdersItem]` forwards to `ReportsManager`.

---

## 6. `AttributionFactsReader` public API

| Item | Path |
|------|------|
| Protocol | `app/modules/attribution_facts/ports/reader.py` — `class AttributionFactsReader(Protocol)` |
| Method | `async def query(self, scope: AttributionScope, window: DateWindow) -> AttributionQueryResult` |
| CH impl | `app/modules/attribution_facts/readers/ch_attribution_facts_reader.py` — `class ChAttributionFactsReader` |
| Test fake | `app/modules/attribution_facts/testing/in_memory_reader.py` — `class InMemoryAttributionFactsReader` |

**Scope / window models:** `app/modules/attribution_facts/domain/models.py`

- `AttributionScope(shop_id: str, physical_adv_ids: frozenset[int] = ...)`
- `DateWindow(start: date, end: date)` inclusive
- `AttributionQueryResult(facts, coverage, reconciliations)`

**DIRECT vs LINKED:**

- Stored per row: `AttributionCommerceFact.attribution_class: AttributionClass` (`app/modules/attribution_facts/domain/enums.py`: `DIRECT`, `LINKED`, …).
- **Reader does not filter by class** — returns all classes; consumers filter (e.g. `app/modules/ai_package_v1/analysis/attribution_evidence.py` — `_sum_class(facts, AttributionClass.DIRECT, ...)`).
- Classification pure logic: `app/modules/attribution_facts/domain/classification.py`.

**Coverage / reconciliation / freshness:**

- `ChAttributionFactsReader.query` loads facts + `attribution_day_reconciliation`, then `assess_reconciliation_grid`, `evaluate_window_coverage` (`domain/coverage.py`, `domain/window_reconciliation_coverage.py`).
- `AttributionCoverage`: `status`, `reason_codes`, `source_complete_through`, `effective_covered_range_*`, `package_cutoff_date`.
- Status enum: `AttributionCoverageStatus` in `domain/enums.py`.

**AI Package seam:** `PortAnalysisAttributionReader.query_leg_window` → `reader.query(scope, window)`.

---

## 7. `context_loader.py` (ad control)

**Path:** `app/modules/ad_control_settings/persistence/context_loader.py`

| Function | Signature | Behavior |
|----------|-----------|----------|
| `load_resolver_shop_features` | `(repository: AdControlSettingsRepository, shop_id: str) -> dict[AdControlFeatureId, ShopFeatureSlot]` | `repository.load_shop_slots(shop_id)` |
| `load_resolver_campaign_features` | `(repository, campaign: CampaignRef) -> dict[AdControlFeatureId, CampaignFeatureSlot]` | `repository.load_campaign_slots(campaign)` — missing rows omitted (INHERIT at resolver) |

**Does not:**

- Load settings **history** / revision timeline (CAS revisions live in `persistence/revision_ledger.py` + row `revision` on PG models — not exposed here).
- Read `shop_campaign_inventory` or CH.
- Build full `ResolverContext` (no `enrollment`, `control_path`, `product_drr` — caller must assemble `ResolverContext` in `domain/resolver_models.py`).

---

## 8. `reason_codes.py`

**File:** `app/modules/ad_control_settings/domain/reason_codes.py` — `class AdControlReasonCode(StrEnum)`:

| Code |
|------|
| `OK` |
| `NOT_ENROLLED_FAIL_CLOSED` |
| `LEGACY_PASSTHROUGH_ACTIVE` |
| `FEATURE_DISABLED_AT_CAMPAIGN` |
| `FEATURE_DISABLED_AT_SHOP` |
| `FEATURE_DISABLED_AT_PRODUCT` |
| `UNSUPPORTED_SCOPE_FOR_FEATURE` |
| `UNKNOWN_FEATURE` |
| `INVALID_CONFIGURATION` |
| `SHOP_ENABLED_MISSING_PAYLOAD` |
| `ACTUAL_DRR_STALE` |
| `ACTUAL_DRR_INSUFFICIENT` |
| `ACTUAL_DRR_UNSUPPORTED` |
| `MEASUREMENT_UNKNOWN` |
| `NO_CONTROL_ACTION_STALE_OR_UNKNOWN` |
| `HEADROOM_ALLOCATOR_NOT_ACCEPTED` |
| `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` |
| `PRODUCT_DRR_ADAPTER_BLOCKED` |

**Usage sites:**

| Code | Production usage |
|------|------------------|
| `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` | `app/modules/ad_control_settings/domain/diagnostics_builder.py:166-169` (hardcoded on `BoundedCpoProposal`); test `tests/unit/ad_control_settings/test_registry_and_headroom.py:146-147` |
| `HEADROOM_ALLOCATOR_NOT_ACCEPTED` | **Defined only** — no Python reference outside `reason_codes.py` (mentioned in `openspec/decisions/drr-cpo-price-semantics/decision.md`) |

---

## 9. `AdControlDiagnosticsBuilder`

**File:** `app/modules/ad_control_settings/domain/diagnostics_builder.py`

| API | Detail |
|-----|--------|
| **Public methods** | **Only** `@staticmethod def build(context: ResolverContext, actual_drr: ActualDrrObservation \| None, *, current_max_cpo_rub, allowed_spend_rub, spend_rub, dry_run_diff_available=False) -> AdControlDiagnosticsReportV1` |
| PRICE_SEMANTICS hardcode | When `configured_target` and `actual_drr` both set: `BoundedCpoProposal(..., decision="NO_PROPOSAL_PRICE_SEMANTICS_NOT_ACCEPTED", reason_codes=(PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED,))`, `proposed_max_cpo_rub=None` |
| Return DTO | `AdControlDiagnosticsReportV1` (`domain/diagnostics.py`) — includes `BoundedCpoProposal` as `proposed_cpo`, plus `ShopHeadroomState`, effective DRR triple, `reason_codes`, `blockers`, `provenance_index`, etc. |
| Related DTOs | `BoundedCpoProposal`, `ShopHeadroomState`, `CampaignHeadroomEligibility` in `domain/headroom.py`; uses `campaign_headroom_eligibility`, `evaluate_shop_headroom_state`, `derive_shop_effective_control_drr` from `domain/headroom_eval.py` |

---

## 10. Money quantization (0.01 RUB, ROUND_HALF_UP)

| Symbol | Path |
|--------|------|
| `MONEY_QUANT_RUB = Decimal("0.01")` | `app/modules/product_control/domain/money.py` |
| `ProductCpoResolver._cpo_from_percent` | `app/modules/product_control/domain/product_cpo_resolver.py` — `raw.quantize(MONEY_QUANT_RUB, rounding=ROUND_HALF_UP)` |

**`app/modules/ad_control_settings/**`:** no `quantize` / `MONEY_QUANT` usage yet — use product_control helper or mirror pattern.

Other repo uses: `app/modules/partner_program/partner_stats.py` (`MONEY_QUANT`), `app/shared/domains/wb/utils/promo_plan_multiplier.py`.

---

## 11. Test patterns

### `tests/unit/ad_control_settings/` (7 files)

- `test_registry_and_headroom.py`
- `test_persistence_validation.py`
- `test_diagnostics_configured_state.py`
- `test_precedence_product_shop.py`
- `test_product_adapter.py`
- `test_payload_codec.py`
- `test_resolver_drr_inheritance.py`

Pattern: pure domain / repository with constructed `ResolverContext`, `AdControlDiagnosticsBuilder.build`, no shop_runner.

### `tests/unit/shop_runner/` — representative V3 tick test

**Path:** `tests/unit/test_process_adv_v3_plan_fact_cache.py` (lives under `tests/unit/`, not `shop_runner/` subfolder).

**Mock structure (summary):** Module-level string constants point at orchestrator subgraph (`_ORCH`, `_DM`, `_AM`, …). Autouse fixture patches `abort_ordinary_v3_if_enter_signaled` → `AsyncMock(return_value=False)`. Tests build `MagicMock()` `complex_adv` with `adv_id`, `adv_setting`, flags; `_start_patches` replaces `DataUpdateManager.load` internals, `plan_campaign_no_data_bootstrap_safe`, `persist_v3_tick_report`, `V3TickKeywordLedger.flush_to_db`, CPO loader, etc., with `AsyncMock` / lambdas; assert side effects on plan/fact Redis without real CH.

**Shop-wide tick:** `tests/unit/shop_runner/test_shop_wide_tick_orchestration.py` — patches `asyncio.TaskGroup`, mocks CH query strings for inventory/full_adv, asserts `WBShop.run` task registration.

---

## 12. pyright-strict & unit markers

| Item | Path / rule |
|------|-------------|
| Strict config | `pyrightconfig_strict.json` (subset `include` of `app/...` paths) |
| Runner | `poetry run pyright-strict` → `app/pyright_strict_entry.py:main()` → `pyright --project pyrightconfig_strict.json` |
| Default pyright | `pyrightconfig.json` includes all `app` (covers `ad_control_settings`) |
| **Gap** | `ad_control_settings` is **not** listed in `pyrightconfig_strict.json` `include` — strict gate may skip new integration files until paths added |

**Unit marking (`conftest.py` `pytest_collection_modifyitems`):**

- Paths under `/tests/unit/` → auto `pytest.mark.unit` (unless explicit `integration` / `destructive_local`).
- Also adds `pytest.mark.fast` for unit paths without integration/destructive.
- Elsewhere defaults to `unit`.

---

## Placement flags (implementer)

1. **Greenfield wire:** no existing `ad_control_settings` ↔ `shop_runner` link.
2. **`context_loader`** is PG slots only — runtime must supply `ActualDrrObservation`, enrollment, control path, optional product adapter; inventory/history are separate ports (`attribution_facts` patterns).
3. **Shop spend / GMV inputs** need explicit adv_id universe (managed vs shop-wide inventory).
4. **Orders API** single-page in app; full history only via `scripts/wb_api_readonly_ops` pagination.
5. **Hook choice:** per-campaign (`process_adv_v3` post-load) vs shop batch (`adv_settings_auto_update`) — not specified in OpenSpec task 4.1.
6. **`pyright-strict`** may need `include` entry for new shop_runner integration modules.

---

## Related OpenSpec

- `openspec/changes/hierarchical-ad-control-settings/tasks.md` — task 4.1 unchecked
- `design.md` — ownership `app/modules/ad_control_settings/`; runtime was explicitly out of scope for Slice A/B
- `owner-contract.md` — diagnostics read-only; no actuation in persistence slice
