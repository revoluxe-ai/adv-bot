---
cursor:
  subagentId: "bc-5813c385-4ad8-59c3-8996-95add1dbee79"
---

# Task 4.1 — test matrix (pre-implementation)

**Repo / baseline:** `/agent/repos/adv-bot` @ `a2e8453e773411eab989b08fa1358f2195c2dee4`  
**Change:** `hierarchical-ad-control-settings` task **4.1 Runtime shop-runner integration**  
**Authority:** `openspec/decisions/drr-cpo-price-semantics/decision.md` (§2–§9), Slice A domain in `app/modules/ad_control_settings/domain/`

## Current state @ stage

| Area | Status |
|------|--------|
| Slice A pure domain + Slice B persistence/dry-run | Implemented; unit tests under `tests/unit/ad_control_settings/`, `tests/unit/wb_sky_control_plane/test_ad_control_*` |
| V1 order-value reason codes (`DIRECT_ATTRIBUTION_*`, `SHOP_ORDER_GMV_*`, …) | **Not** in `AdControlReasonCode` yet — task 4.1 implementation + tests add them |
| Shop-runner wiring | **No** `ad_control` / hierarchical imports under `app/modules/shop_runner/` |
| `AdControlDiagnosticsBuilder` | Still blocks CPO on `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` — 4.1 should switch campaign path to order-value per ADR |

## Test layering (TDD order)

1. **Pure application/domain (no I/O)** — lock formulas + fail-closed mapping (`tests/unit/ad_control_settings/`).
2. **Attribution authority boundary** — DIRECT vs LINKED, coverage, `derived_metrics` alignment (`tests/unit/attribution_facts/`).
3. **Product / enrollment** — inherit vs override vs disabled; `NOT_ENROLLED` (`tests/unit/ad_control_settings/`, `tests/unit/product_control/` smoke only).
4. **Shop-runner orchestration (mocked ports)** — tick loads context, builds diagnostics/proposals, **never** Apply/WB (`tests/unit/shop_runner/`, `tests/unit/app/modules/shop_runner/`).
5. **Safety regression** — AST/import guard + runtime mocks (pattern: `tests/unit/wb_sky_control_plane/test_a1_safety_regression.py`).
6. **Integration (optional, post-unit)** — `tests/integration/ad_control_settings/` only if PG-backed repository loader is exercised; not required for first green unit matrix.

Conventions observed: module docstring; `pytest.mark.unit` or `pytestmark = pytest.mark.unit`; `@pytest.mark.asyncio` for port/async services; scenario files named `test_slice_*_scenario_evidence.py`; shared JSON under `tests/unit/<pkg>/fixtures/` (`attribution_facts` precedent).

---

## Canonical formula tests (golden, parametrized)

| ID | Formula | Fixture inputs (minimal) | Locked outputs |
|----|---------|--------------------------|----------------|
| F-SHOP-DRR | `shop_actual_drr = total_shop_ad_spend / whole_shop_order_gmv` (same window) | GMV `1_000_000`, spend `90_000` | actual DRR `9%` (or decimal 0.09 per type choice) |
| F-SHOP-HDR | `allowed = GMV × target_drr/100`; `headroom = allowed − spend` | GMV `1_000_000`, target `8%`, spend `90_000` | allowed `80_000`, headroom `−10_000` |
| F-SHOP-BND | below / exact / above target | spend `70_000` / `80_000` / `90_000` @ GMV `1M`, target `8%` | headroom `+10_000` / `0` / `−10_000` |
| F-CAMP-DRR | `campaign_actual_drr = campaign_spend / DIRECT_attributed_GMV` | spend `12_000`, DIRECT GMV `100_000` | `12%` |
| F-EOV | `expected_order_value = Σ DIRECT GMV / Σ DIRECT orders` (aggregate multi-nm first) | nm1: GMV `600`, orders `1`; nm2: GMV `400`, orders `1` | EOV `500` |
| F-CPO | `target_cpo = EOV × effective_target_drr/100` | EOV `1200`, effective target `10%` | `120.00` (0.01 RUB HALF_UP) |
| F-MULTI | multi-nm must not average per-nm DRR | two DIRECT rows; **wrong** path = mean of per-nm ratios | assert single ratio from summed numerators/denominators |

---

## SHOP failure-domain matrix

| Case | Shop GMV | Shop spend | Window / basis | Sufficiency | Expected blocker(s) | Notes |
|------|----------|------------|----------------|-------------|----------------------|-------|
| S1 below target | complete | complete, spend &lt; allowed | aligned | SUFFICIENT | none (headroom &gt; 0) | F-SHOP-BND |
| S2 exact target | complete | spend = allowed | aligned | SUFFICIENT | none (headroom = 0) | |
| S3 above target | complete | spend &gt; allowed | aligned | SUFFICIENT | none (headroom &lt; 0); CPO **decrease** eligibility only if feature enabled | no allocator ranking |
| S4 zero GMV | `0` | any | aligned | SUFFICIENT | fail-closed (no divide-by-zero actuation) | map to shop GMV / measurement blocker per impl |
| S5 absent GMV | `None` / missing port | complete | aligned | — | `SHOP_ORDER_GMV_INCOMPLETE` | |
| S6 incomplete GMV | partial window / `source_complete_through` &lt; window.end | complete | aligned | INCOMPLETE | `SHOP_ORDER_GMV_INCOMPLETE` | mirror `evaluate_window_coverage` |
| S7 incomplete spend | complete | `None` / partial | aligned | — | `SHOP_SPEND_INCOMPLETE` | |
| S8 stale facts | complete | complete | aligned | `STALE` | `ACTUAL_DRR_STALE` + no control action | extends `test_stale_actual_drr_blocks_control_action` |
| S9 incompatible windows | GMV window A, spend window B | mismatched ids/dates | — | — | `CPO_INPUTS_INCOMPLETE` or dedicated window mismatch code | cross-cutting C-WIN |
| S10 unsupported revenue basis | buyout / funnel / `wb_common_stat` | any | — | — | `REVENUE_BASIS_UNSUPPORTED` | assert reader family ≠ `ORDERS_OR_SALES_REPORTS_READ` rejected |

---

## CAMPAIGN failure-domain matrix

| Case | DIRECT facts | LINKED facts | Spend | Coverage | Enrollment / mode | Expected blocker(s) |
|------|--------------|--------------|-------|----------|-------------------|----------------------|
| C1 valid DIRECT | complete sums | — | complete | COMPLETE | ENROLLED, INHERIT | OK; `target_cpo` from F-CPO |
| C2 multi-nm DIRECT | 2+ nm rows | — | complete | COMPLETE | ENROLLED | EOV from aggregated sums (F-MULTI) |
| C3 zero DIRECT orders | GMV &gt; 0, orders `0` | — | complete | COMPLETE | ENROLLED | `ORDER_VALUE_UNAVAILABLE` |
| C4 missing attribution | no DIRECT rows | optional LINKED | complete | — | ENROLLED | `DIRECT_ATTRIBUTION_MISSING` |
| C5 insufficient DIRECT | any metric `None` in DIRECT row | — | complete | COMPLETE | ENROLLED | `DIRECT_ATTRIBUTION_INSUFFICIENT` |
| C6 stale attribution | complete | — | complete | COMPLETE | ENROLLED | `ATTRIBUTION_FACT_STALE` and/or `ACTUAL_DRR_STALE` |
| C7 incomplete window | partial recon grid | — | complete | not COMPLETE | ENROLLED | `ATTRIBUTION_WINDOW_INCOMPLETE` |
| C8 LINKED ignored | small DIRECT | large LINKED | complete | COMPLETE | ENROLLED | actuation uses DIRECT only; LINKED may appear in diagnostics, **not** in CPO denominator |
| C9 catalog price absent | complete DIRECT | — | complete | COMPLETE | ENROLLED | **must not** block; **must not** call `ProductCpoResolver` for proposal |
| C10 inherited target DRR | complete | — | complete | COMPLETE | campaign INHERIT, shop 15% | effective target 15% |
| C11 campaign override | complete | — | complete | COMPLETE | OVERRIDE 8%, shop 15% | effective target 8% |
| C12 campaign disabled | complete | — | complete | COMPLETE | `DISABLED` | `FEATURE_DISABLED_AT_CAMPAIGN`; no proposal |
| C13 NOT_ENROLLED | complete | — | complete | COMPLETE | `NOT_ENROLLED` | `NOT_ENROLLED_FAIL_CLOSED` (existing `test_resolver_drr_inheritance`) |

---

## Cross-cutting invariants (dedicated tests)

| ID | Invariant | Assertion strategy |
|----|-----------|-------------------|
| C-ALLOC | no hidden allocation | `HeadroomAllocator` not invoked; no ranked budget split; proposal list empty or single-campaign diagnostic only |
| C-WB | no WB writes | `unittest.mock` / AST: no `WBPromotion*`, `apply_adv_excel`, cluster bid writers in hierarchical module |
| C-APPLY | no Apply calls | `ApplyManager`, `apply_changeset`, `validate_ad_control_changeset` not called from shop-runner tick (dry-run validator only if explicit read-only tooling path) |
| C-FUNNEL | no funnel-GMV authority leak | shop DRR port never queries `wb_common_stat` / `load_*_orders_per_cart` (patch + assert not called; mirror `test_unmanaged_campaign_collector` style) |
| C-MIX | no DIRECT+LINKED mixing | with both classes present, economics function receives only DIRECT aggregates for CPO/DRR actuation |
| C-WIN | no mismatched-window arithmetic | GMV window ≠ spend window ⇒ blocked before any ratio |

---

## Fail-closed reason coverage checklist

| Reason | Primary test file (recommended) | Matrix row |
|--------|----------------------------------|------------|
| `DIRECT_ATTRIBUTION_MISSING` | `test_campaign_v1_economics_fail_closed.py` | C4 |
| `DIRECT_ATTRIBUTION_INSUFFICIENT` | same | C5 |
| `ATTRIBUTION_WINDOW_INCOMPLETE` | same + `attribution_facts/test_v1_hierarchical_actuation_boundary.py` | C7 |
| `ATTRIBUTION_FACT_STALE` | same | C6 |
| `ORDER_VALUE_UNAVAILABLE` | `test_campaign_order_value_and_target_cpo.py` | C3 |
| `SHOP_ORDER_GMV_INCOMPLETE` | `test_shop_factual_drr_and_headroom.py` | S5–S6 |
| `SHOP_SPEND_INCOMPLETE` | same | S7 |
| `REVENUE_BASIS_UNSUPPORTED` | `test_shop_factual_drr_and_headroom.py` | S10 |
| `CPO_INPUTS_INCOMPLETE` | `test_v1_economics_composer_fail_closed.py` | S9, partial ports |
| `NOT_ENROLLED_FAIL_CLOSED` | extend `test_resolver_drr_inheritance.py` + shop-runner tick | C13 |
| `ACTUAL_DRR_STALE` | extend `test_registry_and_headroom.py` + shop factual path | S8 |

---

## Recommended test file paths

### New — `tests/unit/ad_control_settings/`

| Path | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures (see below); no autouse CH/Redis |
| `fixtures/shop_factual_golden.json` | Optional static GMV/spend windows for parametrized headroom |
| `fixtures/direct_multi_nm_attribution.json` | Optional; can stay Python builders only |
| `test_shop_factual_drr_and_headroom.py` | F-SHOP-*; S1–S10; ports for `ORDERS_OR_SALES` GMV + shop spend |
| `test_campaign_order_value_and_target_cpo.py` | F-EOV, F-CPO, F-CAMP-DRR; rounding; C1–C3, C9–C11 |
| `test_campaign_v1_economics_fail_closed.py` | C4–C8, C12; reason code assertions |
| `test_v1_economics_composer_fail_closed.py` | End-to-end compose shop + campaign inputs → single diagnostics/proposal DTO; `CPO_INPUTS_INCOMPLETE` |
| `test_diagnostics_order_value_actuation.py` | `AdControlDiagnosticsBuilder` / successor: order-value proposal replaces catalog block when ADR inputs OK |
| `test_slice_41_scenario_evidence.py` | Owner-style scenarios (A–F parallel to `test_diagnostics_configured_state.py`); traceability IDs in docstring |
| `test_v1_authority_invariants.py` | C-FUNNEL, C-MIX, C-WIN; ProductCpoResolver not used for hierarchical proposal |

### Extend existing (small additions)

| Path | Add |
|------|-----|
| `test_resolver_drr_inheritance.py` | Shop-runner `ResolverContext` loaded from fake repository + `NOT_ENROLLED` |
| `test_registry_and_headroom.py` | Shop headroom when `allowed_spend_rub` derived from GMV×target (not only injected) |
| `test_precedence_product_shop.py` | Campaign disabled + hierarchical eligibility interaction |

### `tests/unit/attribution_facts/`

| Path | Purpose |
|------|---------|
| `test_v1_hierarchical_actuation_boundary.py` | C8: `compute_drr_fact`/`_sum_metric` behavior; LINKED present but V1 actuation reader filters DIRECT; aligns with `test_classification.py` |

### `tests/unit/product_control/`

| Path | Purpose |
|------|---------|
| `test_product_cpo_resolver.py` (or tiny sibling `test_product_cpo_not_hierarchical_authority.py`) | C9: catalog path blocked vs hierarchical order-value path — no silent equivalence |

### `tests/unit/wb_sky_control_plane/`

| Path | Purpose |
|------|---------|
| `test_hierarchical_runtime_no_apply_wiring.py` | Shop-runner hierarchical package must not import apply kernel (import graph / AST) |

### `tests/unit/shop_runner/`

| Path | Purpose |
|------|---------|
| `test_hierarchical_ad_control_tick.py` | Orchestration: enrolled shop tick calls loader + economics composer; C-ALLOC, C-WB, C-APPLY; pattern from `test_shop_wide_tick_orchestration.py` |
| `test_hierarchical_ad_control_managed_path_preservation.py` | Hierarchical tick coexists with managed collection; no duplicate WB stat pulls (optional) |

### `tests/unit/app/modules/shop_runner/`

| Path | Purpose |
|------|---------|
| `service_manager/test_hierarchical_ad_control_service.py` | Service-level unit tests with autouse balance/redis mocks pattern from `test_auto_adv_active_control.py` |

### Future integration (not first gate)

| Path | Purpose |
|------|---------|
| `tests/integration/ad_control_settings/test_shop_runner_context_loader_pg.py` | Only if 4.1 loads real PG via existing `tests/integration/ad_control_settings/conftest.py` |

---

## Reusable fixtures (recommended)

### Package: `tests/unit/ad_control_settings/conftest.py`

| Fixture | Returns | Reuse from |
|---------|---------|------------|
| `measurement_window_7d` | `DateWindow` | `attribution_facts` tests (`_START`/`_END` pattern) |
| `campaign_scope` | `AttributionScope` | `test_window_reconciliation_grid.py` |
| `observation_provenance` | `ObservationProvenance` | `_PROV` in attribution tests |
| `resolver_context_enrolled` | `ResolverContext` | `_base_ctx` in `test_diagnostics_configured_state.py` |
| `shop_drr_policy_8_12` | `DrrPolicyParamsV1` | `drr_profile_from_percent` |
| `campaign_ref` | `CampaignRef` | existing ad_control tests |
| `actual_drr_sufficient` / `actual_drr_stale` | `ActualDrrObservation` | `test_registry_and_headroom.py` |
| `direct_fact` | factory `(nmid, gmv, orders, class=DIRECT)` | `AttributionCommerceFact` builders in `test_reconciliation_and_coverage.py` |
| `linked_fact` | factory | `test_classification.py` |
| `spend_ref` | `CampaignDaySpendReference` | derived_metrics tests |
| `complete_coverage_bundle` | facts + recon + `InMemoryAttributionFactsReader` | `InMemoryAttributionFactsReader` + full recon grid from `test_window_reconciliation_grid.test_c_full_matrix_pass` |
| `fake_shop_factual_port` | object implementing shop GMV + spend read for window | **new**; record `revenue_basis` / `window_id` |
| `fake_ad_control_repository` | in-memory shop/campaign slots | mirror row shapes from `test_ad_control_dry_run_repository_parity.py` (`AdControlShopFeatureRow`) without PG |
| `economics_input_golden_below_target` | parametrized dict for F-SHOP-BND | ADR §11 example |

### Reuse without duplication

- `app.modules.attribution_facts.testing.in_memory_reader.InMemoryAttributionFactsReader` — campaign queries (C1–C8).
- `encode_payload_json` / `_drr_profile` helpers — `tests/unit/wb_sky_control_plane/test_ad_control_changeset_validate.py`.
- `ComplexAdv` + `_FakeTaskGroup` — `tests/unit/shop_runner/test_managed_path_preservation.py` for tick wiring.
- `RecordingWbReader` / forbidden import prefixes — adapt from `test_a1_safety_regression.py`.

### Parametrize IDs (pytest)

Use stable ids for traceability: `shop-below-target`, `shop-gmv-incomplete`, `camp-linked-ignored`, `camp-not-enrolled`, etc.

---

## Suggested implementation-facing module cuts (tests target)

| Module (anticipated) | Test home |
|--------------------|-----------|
| `app/modules/ad_control_settings/application/shop_factual_drr.py` (or `runtime/`) | `test_shop_factual_drr_and_headroom.py` |
| `app/modules/ad_control_settings/application/campaign_order_value_cpo.py` | `test_campaign_order_value_and_target_cpo.py` |
| `app/modules/ad_control_settings/application/v1_economics_composer.py` | `test_v1_economics_composer_fail_closed.py` |
| `app/modules/shop_runner/.../hierarchical_ad_control/*` | `test_hierarchical_ad_control_tick.py`, `test_hierarchical_ad_control_service.py` |

Exact paths may shift; keep test package names stable under `tests/unit/ad_control_settings/` and `tests/unit/shop_runner/`.

---

## Commands (post-implementation)

```bash
cd /agent/repos/adv-bot
poetry run pytest -m unit tests/unit/ad_control_settings/ -v
poetry run pytest -m unit tests/unit/attribution_facts/test_v1_hierarchical_actuation_boundary.py -v
poetry run pytest -m unit tests/unit/shop_runner/test_hierarchical_ad_control_tick.py -v
poetry run pyright-strict  # after new public APIs
```

---

## Gaps / decisions for implementer

1. Map **zero shop GMV** to a single reason (`SHOP_ORDER_GMV_INCOMPLETE` vs measurement-specific) — lock in one test.
2. Whether `ATTRIBUTION_FACT_STALE` and `ACTUAL_DRR_STALE` are both emitted or tiered — document in composer tests.
3. Shop-runner **entrypoint** name (V3 tick vs dedicated coroutine) — orchestration test should anchor to the real function once added.
