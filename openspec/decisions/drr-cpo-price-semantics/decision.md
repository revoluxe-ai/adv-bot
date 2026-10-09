# Decision: drr-cpo-price-semantics

## Status

**Proposed** — architecture / evidence only. `PRICE_SEMANTICS_ACCEPTED = NO` until Owner
closes gaps below.

## Context

WB Sky must eventually convert **configured target DRR** + conversion facts + a
**canonical unit economic basis** into **bounded campaign CPO actuation**. Accepted
foundation (`product-pricing-and-cpo-ownership`, `product-control-context`,
`attribution-facts-contract`) deliberately **blocks** price-dependent production
actuation until this decision closes price meaning, DRR denominator alignment, and
freshness policy.

This decision is **independent** of: `hierarchical-ad-control-settings`,
`wb-sky-mcp-read-interface`, `campaign-settings-history`, shop-wide collection.

## 1. Inventory — price / revenue fields (evidence-backed)

| Label (this ADR) | Exists today? | SOURCE | DOCUMENTED SEMANTICS | TIME | SCOPE | H vs C | WB Sky controls? |
|------------------|---------------|--------|----------------------|------|-------|--------|------------------|
| **PROMO_ORDER_GMV** (`sum_price`) | YES | WB promotion fullstats → `attribution_facts` `gmv_rub` / `attributed_gmv_rub` | «Сумма заказов, ₽» in promotion stats; reconciled to campaign-day `sum_price` | Calendar `event_date` | `adv_id` × nm × app | Historical factual | NO (read) |
| **AD_SPEND** | YES | `full_adv_wb_stat` / fullstats `sum` | Authoritative spend numerator for CPO/DRR facts | Per adv/day | Physical adv leg | Historical | NO (read) |
| **ATTRIBUTED_ORDERS** | YES | fullstats nm `orders` | Attributed order count (not buyout) | Per adv/day/nm | DIRECT/LINKED/UNKNOWN | Historical | NO |
| **LIST_DISCOUNTED_UNIT** | PARTIAL | Script `a1_sale_price_snapshot.py` → WB `/api/v2/list/goods/filter` sizes `price`, `discountedPrice`, `clubDiscountedPrice` | Candidate **display/list** economics; multi-size aggregation **undefined** | Snapshot `observed_at` | SKU (`nmid`) | Current snapshot | NO (read script only) |
| **SUPPLIER_SALE_LINE** (`finishedPrice`, `spp`) | YES (model) | `Sale` data class | Supplier sale row fields; **not** wired to control | Sale event | Line item | Historical | NO |
| **CARD_FUNNEL_ORDERS_SUM** | YES | `wb_common_stat` / CH `orders_sum` | Card funnel revenue aggregate | Daily nm | Shop card | Historical | NO |
| **BUYOUTS_SUM_RUB** | YES | `wb_common_stat.buyouts_sum_rub` | Redeemed/buyout rub aggregate | Daily nm | Shop card | Historical | NO |
| **PLAN_PAY_PER_ORDER** | YES | `AdvSetting.target_price_for_order`, `max_price_for_order` | Legacy **campaign** pay-for-order plan (руб./заказ), **not** DRR% and **not** list price | Current PG row | Per `AdvSetting` | Current config | YES (Apply bounded) |
| **PREDICTED_ORDER_CPO** | YES | `calc_pay_for_order` from conv×CPM | Model CPO at bid point | Tick / ladder | Keyword/campaign | Current compute | NO (shop-runner) |
| **FACT_PAY_FOR_ORDER** | YES | `spend / orders` (campaign stat, `common_advs_stat`) | Observed cost per **campaign-reported order** | Windowed | Campaign | Historical | NO |
| **EFFECTIVE_CONTROL_PRICE** | PORT ONLY | `ProductPricingReader` → `EffectiveProductPrice` | Intended **unit** basis for DRR→CPO; **no production adapter** | `observed_at` + staleness policy TBD | `(shop_id, nmid)` | Current | NO (blocked) |
| **HISTORICAL_SALES_ECONOMICS** | PORT ONLY | `ProductSalesEconomicsReader` (`orders_sum_rub`) | Analytics capacity; **explicitly forbidden** as control price | Period | Product | Historical | NO |

**FACT:** Attribution V1 does **not** support attributed buyouts (`ATTRIBUTION_UNSUPPORTED`).

## 2. Canonical economic terms (do not collapse)

| Term | Definition in WB Sky |
|------|----------------------|
| **DISPLAY_PRICE** | Seller-facing list/discounted unit from Prices API (multi-size TBD). **Not accepted** as control SoT. |
| **CUSTOMER_PAID_PRICE** | Not modeled end-to-end; supplier `finishedPrice`/`spp` exist but are not control inputs. **EVIDENCE_GAP.** |
| **ORDER_GMV** | Promotion `sum_price` at order-attribution grain → `attributed_gmv_rub`. |
| **ATTRIBUTED_GMV** | Sum of `attributed_gmv_rub` for DIRECT or LINKED class in a window. |
| **BUYOUT_GMV** | `buyouts_sum_rub` at card funnel grain only; **not** in attribution facts V1. |
| **SELLER_REVENUE / NET_MARGIN** | **Absent** as authoritative control quantities. Commission/logistics/net proceeds **not** in control path. |

## 3. DRR semantics (three families — naming collision risk)

### A. Policy DRR (`DrrProfile`) — **NEW_PROPOSAL (math accepted, price input not)**

- **SOURCE:** `DrrProfile.target_drr_percent`, `max_drr_percent` (product-control foundation).
- **Meaning:** Seller **policy** percent used only in `ProductCpoResolver`:
  `CPO_rub = EFFECTIVE_CONTROL_PRICE × DRR% / 100` (0.01 RUB HALF_UP).
- **Denominator implicit in policy:** price must be the **same economic basis** Owner selects for “% of revenue” (not yet chosen).
- **WB Sky control:** future persistence/actuation blocked until `PRICE_SEMANTICS_ACCEPTED`.

### B. Observed DRR facts (`DRR_FACT_*`) — **ACCEPTED_EXISTING_DECISION**

- **SOURCE:** `attribution-facts-contract` + `compute_drr_fact`.
- **Formula:** `DRR_FACT_* = AD_SPEND / ATTRIBUTED_GMV` (ratio; consumers may display as %).
- **Denominator:** `attributed_gmv_rub` from promotion `sum_price` (order-time GMV, not buyout).
- **Basis:** attributed orders/GMV; cancellations/returns **not** re-stated in V1 contract beyond WB restatement/revision rules.
- **Lag/window:** window sum over days with `COMPLETE` coverage + reconciliation PASS; spend joined once per `(adv_id, event_date)`.
- **Aggregation:** per physical `adv_id` by default; Auto+Search pair aggregate opt-in only.
- **Shop-level actual DRR:** **EVIDENCE_GAP** — AI package `store_drr` family is GAP (`BLOCKED_BY_SHOP_DRR_SOURCE`); not authoritative for control.

### C. Legacy “headroom” (V3 PFO) — **ACCEPTED_EXISTING_BEHAVIOR (not DRR%)**

- **SOURCE:** `campaign_pfo_gates.py`.
- **Meaning:** ratio × **`max_price_for_order` plan CPO**, comparing **fact pay-for-order** vs plan.
- **Not** shop DRR%; do not use for DRR denominator proposals.

**PROPOSED_DRR_DENOMINATOR (for observed shop/campaign actual DRR aligned with facts):**
`advertising_spend / ATTRIBUTED_GMV` at the **same scope and window** as policy evaluation, with DIRECT/LINKED emitted only under attribution coverage rules. Buyout-based DRR is **OUT OF SCOPE** until a new factual source is spec-amended.

## 4. CPO semantics (disambiguation)

| Name | Meaning | Source |
|------|---------|--------|
| **target_cpo_rub / max_cpo_rub** | Policy ceiling from DRR% × unit price | `ProductCpoResolver` |
| **CPO_FACT_DIRECT / LINKED** | `spend / attributed_orders` | `compute_cpo_fact` |
| **target_price_for_order / max_price_for_order** | Legacy **plan** pay-per-order (руб.) | `AdvSetting` |
| **fact_pay_for_order** | `spend / orders` (campaign stat) | shop-runner / `AdvState` |
| **predicted pay_for_order** | `calc_pay_for_order` from conv×CPM | V3 bid ladder |
| **keyword bid economics** | Not CPO; bid rub | WB auction |

**PROPOSED_CPO_INPUTS (minimum to map shop DRR policy → campaign CPO proposal):**

1. **Effective `DrrProfile`** at product (or inherited shop) — policy percents.
2. **`EFFECTIVE_CONTROL_PRICE`** per `(shop_id, nmid)` from `ProductPricingReader` with accepted field + aggregation + staleness.
3. **`ProductCpoResolver` output** → canonical `target_cpo_rub`, `max_cpo_rub`.
4. **Future `LegacyCampaignCpoAdapter`** mapping to `AdvSetting` plan fields (decision text only today).
5. **For gating/diagnostics (parallel, not substitutable):** `CPO_FACT_*`, `DRR_FACT_*`, `fact_pay_for_order` on compatible windows.

No single equation may mix (2) with `orders_sum` or `target_price_for_order` as price.

## 5. Price volatility — **NEW_PROPOSAL (policy skeleton)**

- **Freshness:** `EffectiveProductPrice.observed_at` MUST be evaluated against an Owner-defined max age; stale → `ProductPriceUnavailable` → `BLOCKED_BY_PRODUCT_PRICE_SOURCE`.
- **Abrupt changes:** DRR-derived CPO MUST recompute from latest accepted snapshot; no silent carry-forward of old price in actuation path.
- **Missing price:** fail closed (existing resolver behavior).
- **Multi-product campaigns:** CPO proposal grain is **`nmid`**; campaign-level aggregation of price **EVIDENCE_GAP** (Owner: min/max/weighted by plan).
- **Historical attribution at old price:** facts remain historical GMV; policy CPO uses **current** price snapshot only — do not back-adjust attributed GMV to today's price.
- **Oscillation:** rate-limit / hysteresis for actuation is **OUT OF SCOPE** for this ADR (future controller); semantics require stable price SoT first.

## 6. Shop DRR → campaign CPO (economic facts only, no allocator)

**Required facts (proposed):**

| Stage | Quantity | Basis |
|-------|----------|--------|
| Shop policy | `shop_target_drr_percent` (from shop `DrrProfile` when enrolled) | Policy |
| Shop observed | `shop_ad_spend / shop_attributed_gmv` | Same GMV semantics as `DRR_FACT_*` aggregated with documented scope |
| Headroom | `shop_target_drr − shop_actual_drr` (or rub equivalent via GMV) | **OWNER_DECISION_REQUIRED** on sign/units |
| Product policy CPO | `ProductCpoResolver` per `nmid` | Price × DRR% |
| Campaign linkage | `CampaignProductBinding` projection | Which nmids participate |
| Campaign observed | `CPO_FACT_*`, `DRR_FACT_*` per adv leg | Attribution contract |

**Do not** allocate headroom by applying shop DRR% uniformly to every campaign without per-scope spend/GMV and product price facts.

## 7. Acceptance labels

| Item | Label |
|------|--------|
| Attribution GMV = promotion `sum_price` | **ACCEPTED_EXISTING_DECISION** |
| CPO_FACT / DRR_FACT formulas | **ACCEPTED_EXISTING_DECISION** |
| ProductCpoResolver formula | **ACCEPTED_EXISTING_DECISION** |
| ProductPricingReader vs SalesEconomics split | **ACCEPTED_EXISTING_DECISION** |
| Effective price WB API field + multi-size rule | **OWNER_DECISION_REQUIRED** |
| SPP/wallet/customer-paid mapping | **EVIDENCE_GAP** |
| Shop actual DRR SoT | **EVIDENCE_GAP** |
| Campaign multi-nm price aggregation | **OWNER_DECISION_REQUIRED** |
| Staleness TTL | **OWNER_DECISION_REQUIRED** |
| Buyout-based DRR/CPO | **EVIDENCE_GAP** (unsupported in attribution V1) |

## 8. Compatibility (read-only assessment)

- **ProductControl `DrrProfile`:** unchanged; awaits price SoT.
- **hierarchical-ad-control-settings:** not in this repo snapshot; any future shop DRR% must use denominators consistent with §3B or remain diagnostics-only until shop SoT exists.
- **Attribution Facts:** canonical for **observed** CPO/DRR; must not be replaced by `wb_common_stat` denominators.
- **ChangeSet / Apply:** continues to own `max_price_for_order` mutations; DRR-derived mapping is future adapter.
- **V3 / AdvSetting:** legacy plan CPO remains until adapter + Owner cutover strategy.
- **Diagnostics / AI package:** may show `DRR_FACT_*`; `store_drr` remains GAP.

## Decision outcome

**PRICE_SEMANTICS_ACCEPTED** remains **NO**.

**IMPLEMENTATION_IMPACT:** No production code in this change. Unblocks future:
`ProductPricingReader` adapter, staleness policy, shop DRR aggregation spec, `LegacyCampaignCpoAdapter`, headroom controller.

## Applies to

- `app/modules/product_control/domain/product_cpo_resolver.py`
- `app/modules/product_control/application/ports/pricing.py`
- `app/modules/attribution_facts/domain/derived_metrics.py`
- `openspec/specs/attribution-facts-contract/spec.md`
- `openspec/decisions/product-pricing-and-cpo-ownership/decision.md`

## Related

- Evidence scan: `.cursor` store `internal/architecture/drr-cpo-price-semantics-evidence-scan.md` (non-authoritative working notes)
