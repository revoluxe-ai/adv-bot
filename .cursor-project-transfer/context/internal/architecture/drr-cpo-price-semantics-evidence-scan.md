---
cursor:
  subagentId: "bc-2534e606-e640-565d-87de-cbfaff827059"
---

# Evidence scan: `drr-cpo-price-semantics`

**Repo:** `/agent/repos/adv-bot`  
**Scan date:** 2026-10-09  
**Decision artifact:** No file or OpenSpec change named `drr-cpo-price-semantics` exists yet (`EVIDENCE_GAP` — this scan is input for that decision).

---

## Executive: three different “DRR / CPO” families

| Family | Meaning in code | Price / GMV role |
|--------|-----------------|------------------|
| **Product-control DRR** | `target_drr_percent` / `max_drr_percent` → **plan CPO (RUB)** via `price × DRR% / 100` | Requires **effective unit price** (port only; not implemented) |
| **Attribution / AI DRR_FACT_*** | `spend_rub / attributed_gmv_rub` (ratio, not %) | GMV = WB promotion fullstats `sum_price` at nm/day |
| **Legacy campaign CPO / PFO** | **Pay-for-order** (руб./заказ): plan `AdvSetting.*_price_for_order`, fact `spend/orders`, predicted `calc_pay_for_order` | **Not** tied to product list price; uses ad spend ÷ orders |

Do not conflate these when accepting price semantics.

---

## 1. Price / revenue concepts (advertising, sales, attribution, CPO)

### WB promotion / campaign stats (advertising)

- **`sum` / `spend` (руб.)** — ad spend  
  - **SOURCE:** WB fullstats / `full_adv_wb_stat` (CH), Pydantic `DayStats.sum`, `SmallFullAdvStatPerDay.spend`  
  - **SEMANTICS:** «Затраты, ₽»  
  - **TIME:** per calendar `event_date` / day  
  - **SCOPE:** physical `adv_id` leg  
  - **Historical vs current:** historical factual; refreshed by collectors  
  - **WB Sky control:** read-only on analysis path; spend SoT not duplicated in attribution facts  

```37:48:app/modules/full_stat_adv_updater/types/full_adv_stat.py
class DayStats(BaseModel):
    date: datetime = Field(..., description="Дата, за которую представлены данные")
    ...
    sum: float = Field(..., description="Затраты, ₽")
    ...
    sum_price: float = Field(..., description="Сумма заказов, ₽")
```

- **`sum_price` / order sum (руб.)** — attributed/order value in **promotion** stats  
  - **SOURCE:** same fullstats tree; attribution ingest maps `sum_price`/`sumPrice` → `gmv_rub`  
  - **SEMANTICS:** «Сумма заказов, ₽» (WB promotion, not seller payout)  
  - **TIME:** calendar day  
  - **SCOPE:** campaign-day total or nm/app grain  

```113:123:app/modules/attribution_facts/ingest/raw_fullstats.py
                rows.append(
                    RawNmContributionRow(
                        ...
                        gmv_rub=_read_decimal_optional(nm, "sum_price", "sumPrice"),
```

- **Campaign CPO (non-attribution)** — `spend / orders`  
  - **SOURCE:** `CAMPAIGN_WB_STAT_CPO` in AI package (`aggregate.py`); `SmallFullAdvStatPerDay.mean_pay_for_order`  
  - **SEMANTICS:** cost per **campaign-stat order**, not product price  

```71:74:app/modules/full_stat_adv_updater/types/full_adv_stat.py
    @property
    def mean_pay_for_order(self) -> float:
        orders = max(self.orders, 1)
        return self.spend / orders
```

- **Predicted keyword/campaign CPO (V3)** — `calc_pay_for_order(orders_per_1000_rub)` where `orders_per_1000_rub = conv × 1e6 / CPM`  
  - **SOURCE:** `orders_per_1000_rub.py`, `v3_point_order_cpo.order_cpo_at_ch_point`  
  - **SEMANTICS:** «Себестоимость одного заказа (руб.)» from CH conversion × bid  
  - **TIME:** point-in-time on bid ladder; RK cart→order uses **7d** `wb_common_stat`  
  - **WB Sky:** no (shop-runner math)  

```19:23:app/modules/wb_adv_updater/calculated_keywords_manager/orders_per_1000_rub.py
def calc_pay_for_order(orders_per_1000_rub: float) -> float | None:
    """Себестоимость одного заказа (руб.). CPO = 1000 / orders_per_1000_rub."""
```

### Plan / execution CPO on `AdvSetting` (seller-configured targets)

- **`target_price_for_order` (float)** — plan target pay-for-order (руб.)  
- **`max_price_for_order` (int)** — plan ceiling pay-for-order (руб.)  
- **`plan_for_sales_for_day` (int)** — daily order plan count  
  - **SOURCE:** PG `AdvSetting`  
  - **SEMANTICS:** legacy **campaign** CPO targets (not DRR%); mapped to `PlanData.target_pay_for_order` / `max_pay_for_order`  
  - **TIME:** current settings snapshot; CH `plan_fact_stats` stores historical plan columns per tick  
  - **WB Sky control:** **yes** — bounded mutations via `wb_sky_control_plane` Apply (`mutation_policy` includes `max_price_for_order`)  

```598:609:app/modules/common_slaves/wildberries/models/models.py
    plan_for_sales_for_day = mapped_column(Integer, nullable=True, default=None)
    target_price_for_order = mapped_column(Float, nullable=True, default=None)
    max_price_for_order: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    substitute_fact_cpo_for_max: Mapped[bool] = mapped_column(
        ...
        comment=(
            "V3 Raise MAX: in-memory max=fact CPO when fact>db max (per tick, no persist)"
        ),
    )
```

```105:119:app/modules/plan_fact/provider.py
    def get_plan_data(adv: AdvSetting) -> PlanData | None:
        plan_orders = adv.plan_for_sales_for_day
        max_pay_for_order: int | None = adv.max_price_for_order
        target_pay_for_order = adv.target_price_for_order
        ...
            return PlanData(
                orders=plan_orders,
                target_pay_for_order=target_pay_for_order,
                max_pay_for_order=max_pay_for_order,
            )
```

- **Effective plan (promo bonus overlay)** — scales target/max when `raise_plan_on_promobonuses` + promo fraction  
  - **SOURCE:** `promo_plan_multiplier.build_effective_promo_plan` via `PlanFactProvider.get_effective_promo_plan`  
  - **SEMANTICS:** runtime-only higher CPO ceilings when promo wallet usable  
  - **WB Sky:** flag on `AdvSetting`; writes via legacy/Telegram/sales_plan_settings paths today; future ChangeSet  

### Fact CPO (campaign “fact pay for order”)

- **`fact_pay_for_order` / `FactData.pay_for_order`**  
  - **SOURCE:** `CommonAdvsStatData.mean_price_for_order` → CH `plan_fact_stats.fact_pay_for_order`; incremental path `FactSalesDeltaManager`  
  - **SEMANTICS:** `spend_for_inner_advs / max(base_common_orders, 1)` over recent window (not GMV/price)  
  - **TIME:** rolling last_days (`max_last_period`, default 2) + predict_orders from `FactMethods`  
  - **SCOPE:** complex adv (auto+auction spend, orders from `orders_source_for_auto_mode`)  
  - **Historical vs current:** fact is historical spend/orders; plan from current PG  

```141:143:app/modules/common_advs_stat/data_manager.py
        mean_price_for_order = (
            spend_for_inner_advs_for_days / max(base_common_orders, 1)
        )
```

- **`resolve_target_cost`** — dynamic **resolve** threshold: target CPO if plan orders met, else max CPO  
  - **SOURCE:** `cost_resolver.py`  
  - **SEMANTICS:** execution threshold, not DRR-derived  

```40:43:app/shared/domains/wb/utils/cost_resolver.py
        if float(ctx.fact.predict_orders) >= float(ctx.plan.orders):
            return ctx.plan.target_pay_for_order
        return ctx.plan.max_pay_for_order
```

### Shop-wide sales funnel (`wb_common_stat`)

- **`orders_sum` (руб.)** — sum of order values in common card stat  
- **`buyouts_sum_rub`** — buyout rub total (CH migration `003_add_buyouts_sum_rub_to_wb_common_stat.sql`)  
- **`orders`, `add_to_cart`, `open_card`, `buy_outs`** — counts  
  - **SOURCE:** CH `wb_common_stat` (e.g. `common_stat_manager.py`, `wb_common_stat_period_totals.py`)  
  - **SEMANTICS:** shop-SKU funnel / sales aggregates; **explicitly forbidden** as control price for DRR→CPO  
  - **TIME:** daily `date` + versioned `argMax`  
  - **SCOPE:** `(nmid, date)` shop-wide, not ad-attributed  
  - **WB Sky:** read-only  

```9:16:app/modules/common_advs_stat/wb_common_stat_period_totals.py
    ifNull(sum(orders_sum), 0) AS orders_sum_rub,
    ifNull(sum(buyouts_sum_rub), 0) AS buyouts_sum_rub
```

**Product control port (analytics only):**

```17:24:app/modules/product_control/application/ports/sales_economics.py
class ProductSalesEconomicsSnapshot:
    """Агрегаты продаж за период; не подставляются в ProductCpoResolver."""
    ...
    orders_sum_rub: Decimal | None
```

### Seller order / wallet / SPP (supplier sales API)

- **`spp`, `finishedPrice` (as `price`)** on `Sale`  
  - **SOURCE:** WB supplier sales payload (`app/modules/common_slaves/wildberries/data_classes/sale.py`)  
  - **SEMANTICS:** per-sale SPP % and finished price — **not** wired into `ProductCpoResolver` or V3 plan CPO  
  - **TIME:** per sale event  
  - **EVIDENCE_GAP:** relationship to “effective product price” for DRR→CPO undecided  

```17:23:app/modules/common_slaves/wildberries/data_classes/sale.py
    def spp(self):
        return self._data["spp"]
    @property
    def price(self):
        return self._data["finishedPrice"]
```

- **Wallet / promo / campaign budget** — promo accounting (`promo_accounting.py`, auto-budget journal `WBAutoBudgetTopUp`); affects **plan scaling** and spend FEFO, not unit price for DRR→CPO  
  - **SEMANTICS:** wallet promo stays on live WB `cashbacks[]`; not seller list price  

### List / discount price (candidate for product control)

- **SOURCE (script only):** `scripts/a1_sale_price_snapshot.py` — WB Discounts & Prices `list/goods/filter`, fields `discount`, `clubDiscount`, `sizes[].price`, `discountedPrice`, `clubDiscountedPrice`  
- **SEMANTICS:** docstring «CPO normalization (10% of sale price)» — exploratory  
- **STATUS:** `PRICE_SEMANTICS_ACCEPTED = NO`; not production adapter  

```1:4:scripts/a1_sale_price_snapshot.py
"""READ_ONLY: A1 current sale price snapshot for CPO normalization (10% of sale price).
POST /api/v2/list/goods/filter — WB Discounts & Prices API. Без writes.
```

- **SPP dynamics (analytics script):** `scripts/a1_prokraft_spp_dynamics_collect.py` — median SPP from orders; `SPP_STATUS` OBSERVED vs NO_ORDER_OBSERVATION  

### Attribution GMV / revenue

- **`attributed_gmv_rub`** on facts; **`DRR_FACT_* = spend / GMV`**  
  - **SOURCE:** derived in `derived_metrics.py`; GMV from fullstats `sum_price`  
  - **TIME:** `event_date` calendar; window aggregation for AI package  
  - **Cancellation:** no attribution module handling of order cancellation found (`EVIDENCE_GAP` for WB restatement only via observation append)  

### AI package shop/SKU economics (blocked)

- **`SHOP_DRR`, `SKU_GMV`, `SKU_DRR`** — blocked pending whole-shop proof (`SHOP_DRR_BLOCKERS`, `documents.py`)  
- **Not** the same as product-control DRR%  

### Commission / logistics / net proceeds

- **EVIDENCE_GAP:** no first-class domain types for WB commission, logistics, or seller net proceeds in `app/` tied to CPO/DRR. Funnel stat is gross `orders_sum` / buyouts rub.

---

## 2. ProductControl `DrrProfile`

- **Definition:** frozen dataclass `target_drr_percent`, `max_drr_percent` (Decimal); invariant `max >= target`, non-negative target  

```33:42:app/modules/product_control/domain/models.py
class DrrProfile:
    """
    Атомарный DRR-профиль: оба поля обязательны на хранении.
    Инвариант: ``max_drr_percent >= target_drr_percent``.
    """
    target_drr_percent: Decimal
    max_drr_percent: Decimal
```

- **Computation / storage:**  
  - **Not stored in PG yet** — future `ShopControlSettings` / `ProductControlSettings` (`product-control-aggregate-ownership`, `product-control-settings-persistence` concept)  
  - **Resolution:** `EffectiveControlResolver` picks shop vs product **whole profile** (`INHERIT_SHOP`, `OVERRIDE_ENABLED`) or `LEGACY_TIER` / blocked / not enrolled  
  - **DRR is not computed from spend/GMV** in product control — it is **input %** for CPO derivation  

- **DRR → CPO (only formula location):**

```59:62:app/modules/product_control/domain/product_cpo_resolver.py
    def _cpo_from_percent(price_rub: Decimal, drr_percent: Decimal) -> Decimal:
        raw = price_rub * drr_percent / Decimal("100")
        return raw.quantize(MONEY_QUANT_RUB, rounding=ROUND_HALF_UP)
```

- **WB Sky control:** future ChangeSet ops (`SET_SHOP_DRR_PROFILE`, `SET_PRODUCT_DRR_PROFILE` in evolution doc); **not implemented** in foundation archive  

---

## 3. AdvSetting CPO calculations

| Concept | Fields | Formula / rule |
|---------|--------|----------------|
| Plan | `plan_for_sales_for_day`, `target_price_for_order`, `max_price_for_order` | Loaded into `PlanData`; no auto-DRR% |
| Fact CPO | `fact_pay_for_order` (runtime), CH column | `spend / orders` (common stat path) |
| Resolve | uses plan + `fact.predict_orders` | `resolve_target_cost`: target if plan met else max |
| Promo effective plan | `raise_plan_on_promobonuses`, promo fraction | Scales target/max rub |
| V3 max override | `substitute_fact_cpo_for_max` | In-memory raise max to fact CPO (no persist) |
| Keyword PFO | `CalculatedKeyword.pay_for_order` | `calc_pay_for_order` from conv×CPM |
| Overspend | `cpo_max_boundary` | `fact_pay_for_order > max_pay_for_order` |

**Forbidden as price for product DRR→CPO:** `target_price_for_order` on AdvSetting (`pricing.py` port doc).

**WB Sky:** PG campaign settings policy writer + validators (`target_price_for_order` must not exceed `max_price_for_order`).

---

## 4. Attribution Facts contract

| Element | Detail |
|---------|--------|
| **Grain** | `shop_id × physical_adv_id × event_date × app_type × ordered_nm_id` |
| **GMV** | `attributed_gmv_rub` ← fullstats `sum_price` |
| **Orders** | `attributed_orders` |
| **Spend** | **Not** on fact; join `full_adv_wb_stat.spend_rub` once per adv/day |
| **CPO_FACT_*** | `spend / attributed_orders` (class DIRECT/LINKED) |
| **DRR_FACT_*** | `spend / attributed_gmv_rub` (ratio; name is DRR but math is spend/GMV) |
| **Time basis** | Calendar `event_date`; window sums for AI analysis |
| **Coverage** | COMPLETE + reconciliation PASS required; missing ≠ 0 |
| **Cancellation** | Not specified; corrections via append-only observations / latest projection |
| **Buyouts** | UNSUPPORTED V1 at nm grain |
| **WB Sky** | read-only consumer path; collector ownership separate decision |

Spec: `openspec/specs/attribution-facts-contract/spec.md`  
Code: `app/modules/attribution_facts/domain/*`, ingest `pipeline.py`

---

## 5. V3 CPO / PFO logic

| Module | Role |
|--------|------|
| `v3_point_order_cpo.py` | SSOT predicted order CPO at CH bid point |
| `auto_updater_v3/candidates.py` | MIN/MAX CPO candidates, `order_cpo_at_ch_point` |
| `campaign_pfo_gates.py` | **Headroom** = fraction × `plan.max_pay_for_order` (env ratios) — **CPO headroom, not DRR%** |
| `cpo_max_boundary.py` | Strict compare to max plan CPO |
| Executors | `pay_for_order_gap_enable`, `pay_for_order_over_max_off_on_deep_overspend`, raise/reset phases |

**Equations:** predicted CPO only from ad performance (conv, CPM, orders_per_cart); **no product list price**.

**Plan headroom example:**

```40:47:app/modules/shop_runner/service_manager/services/auto_updater_v3/campaign_pfo_gates.py
def gap_enable_plan_headroom_floor(max_pay: float) -> float:
    """Нижняя граница зоны skip enable: ``ratio × plan.max_pay_for_order``."""
    return gap_enable_plan_headroom_ratio() * float(max_pay)
```

---

## 6. OpenSpec / decisions (DRR, CPO, price)

| Artifact | Status | Key tokens |
|----------|--------|------------|
| `openspec/decisions/product-pricing-and-cpo-ownership/decision.md` | Accepted | `ProductPricingReader`, `ProductCpoResolver`, `PRICE_SEMANTICS_ACCEPTED = NO` |
| `openspec/decisions/product-control-aggregate-ownership/decision.md` | Accepted | Future DRR on `ShopControlSettings` / `ProductControlSettings`; not on `WBCard` |
| `openspec/specs/product-control-context/spec.md` | Active | DrrProfile invariants, ProductCpoResolver 0.01 RUB |
| `openspec/specs/attribution-facts-contract/spec.md` | Active | CPO_FACT_*, DRR_FACT_*, spend join |
| `openspec/evolution/product-control-context-future-boundaries.md` | Non-normative | `product-control-shop-drr-runtime` gated on price acceptance |
| Archive `2026-10-09-product-control-context` | Closed | `PRICE_SEMANTICS_ACCEPTED: NO` in receipt |
| **`drr-cpo-price-semantics`** | **Missing** | No change/decision file — **EVIDENCE_GAP** |

Event vocabulary: `DRR_CPO_CHANGE` in `decision_experiment_memory/events.py` (semantic memory, not economics).

---

## 7. `hierarchical-ad-control-settings`

- **Repository search:** **zero** matches for `hierarchical`, `hierarchical-ad-control-settings`, or similar.
- **Closest related concepts (do not conflate):**
  - `product-control-settings-persistence` (future shop/product settings PG)
  - `auto_shelf_bid_control_settings` (shelf bidder PG table — unrelated to DRR%)
  - V3 **plan max headroom** (`campaign_pfo_gates.py`) — fraction of **max CPO**, not hierarchical ad settings
  - Audit script DRR: `store_drr_percent = gross_ad_spend / factual_order_value` (`test_multi_client_strict_eight_target_directive_audit.py`) — **shop-level script**, not runtime module

**EVIDENCE_GAP:** if `hierarchical-ad-control-settings` is an external OPSX change name, it is not present in this repo snapshot.

---

## Cross-cutting: WB Sky control matrix

| Data | WB Sky Apply authority? |
|------|-------------------------|
| `AdvSetting` plan CPO fields, budgets, flags | **Yes** (bounded policy v1 writer) |
| `DrrProfile` persistence | **Future** via ChangeSet (not in repo) |
| `ProductPricingReader` / derived CPO to AdvSetting | **Blocked** until price semantics + runtime change |
| Attribution facts / CH spend reads | **No** (read-only) |
| V3 shop-runner tick / plan-fact CH inserts | **No** (legacy shop-runner paths) |

---

## Recommended decision inputs (for `drr-cpo-price-semantics`)

1. Canonical **effective unit price** field(s), multi-size rule, SPP/club/wallet exclusion or inclusion.  
2. Whether **DRR%** in product control is strictly `CPO = price × DRR/100` or must align with **attribution DRR** `spend/GMV` (currently **different definitions**).  
3. Migration boundary: `AdvSetting.target_price_for_order` / `max_price_for_order` vs `DerivedCpoRub` from resolver.  
4. Staleness / missing price → `BLOCKED_BY_PRODUCT_PRICE_SOURCE` (already in resolver).  
5. Explicit non-goals: `wb_common_stat.orders_sum/orders`, campaign `sum_price`, supplier `finishedPrice` until accepted.

---

## Files touched by this scan

- Created: `internal/architecture/drr-cpo-price-semantics-evidence-scan.md`
