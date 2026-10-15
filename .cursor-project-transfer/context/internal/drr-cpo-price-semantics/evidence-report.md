---
cursor:
  subagentId: "bc-3858ca46-2c84-5b6f-9c93-b00b1b3bd445"
---

# drr-cpo-price-semantics — evidence report

## Owner V1 amendment (supersedes control semantics below)

**Authoritative:** `openspec/decisions/drr-cpo-price-semantics/decision.md` on branch
`cursor/drr-cpo-price-semantics-22ef`.

- `PRICE_SEMANTICS_ACCEPTED = YES`, qualifier `V1_ORDER_VALUE_BASIS`
- `ORDER_VALUE_SEMANTICS_ACCEPTED = YES`
- V1 campaign `TARGET_CPO_RUB` = DIRECT order value × DRR%; **not** catalog price
- Shop DRR = shop spend / whole-shop ORDER_GMV (supplier orders family); campaign DRR = spend / DIRECT attributed GMV
- Sections below remain **historical evidence scan** (pre-Owner correction).

---

**Evidence baseline (Owner):** `065509c111e96aff88255db479001b9c3da3a0d0`  
**Cloud checkout HEAD (note):** `f2b96e7b1271ad532a2113305f4337b02b723cec` — **not** an ancestor of baseline; `app/modules/ad_control_settings/` present only at baseline, absent on current tree. All hierarchical Slice A citations use `git show 065509c:…`.

---

## CHANGE

`drr-cpo-price-semantics` (architecture / evidence only). No code, migration, MCP, or merge into `hierarchical-ad-control-settings`.

---

## ARCHITECTURE_STATUS

- **Accepted foundations:** `product-control-context` (DrrProfile, ProductCpoResolver, pricing ports), `attribution-facts-contract` (derived CPO/DRR), `product-pricing-and-cpo-ownership` (**explicit `PRICE_SEMANTICS_ACCEPTED = NO`**), `hierarchical-ad-control-settings` Slice A at baseline (DRR triple, headroom contract, `PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED`).
- **Runtime:** DRR-derived CPO and hierarchical CPO actuation remain **blocked**; legacy `AdvSetting` rub CPO + V3 bid/CPO math remain production paths.
- **Outcome:** Sufficient evidence to frame Owner decisions; **insufficient** to set `PRICE_SEMANTICS_ACCEPTED = YES`.

---

## ECONOMIC_FIELD_INVENTORY

| FIELD | SOURCE OF TRUTH | SCOPE | TIME | CURRENT vs HIST | GROSS vs NET | ATTRIBUTED vs SHOP | RELIABILITY | LIMITATIONS |
|-------|-----------------|-------|------|-----------------|--------------|-------------------|-------------|-------------|
| `target_price_for_order` / `max_price_for_order` | PG `AdvSetting` | per campaign (`ComplexAdv`) | config (no window) | current setting | rub/user semantics (“себестоимость заказа”) — **not** WB GMV | whole campaign plan | high for legacy runtime | Not DRR-derived; Excel/Telegram writes; promo overlay can scale at runtime |
| `substitute_fact_cpo_for_max` | PG `AdvSetting` | campaign | per tick (V3) | in-memory max←fact CPO | N/A | campaign | feature-flagged | Not canonical product-control CPO |
| `DrrProfile.target_drr_percent` / `max_drr_percent` | future `ShopControlSettings` / `ProductControlSettings` (foundation only today) | shop or `(shop_id,nmid)` | config | current policy | **percent of unstated revenue basis** | product/shop control plane | domain-validated only | No PG persistence in foundation; resolver pure |
| `effective_product_price` / `price_rub` | **port only** `ProductPricingReader` | `(shop_id,nmid)` | point-in-time `observed_at` | current observation | **undefined WB field** | product | **no production adapter** | ADR forbids `wb_common_stat`, `target_price_for_order` as substitute |
| `orders_sum` (funnel) | CH `wb_common_stat` via `post_sales_funnel_products_history` | per `nmid`, day | 7d rolling collect | historical analytics | WB funnel metric; currency noted `unknown` in coverage evidence | shop SKU, not ad-attributed | CH argMax read | **Forbidden** as control price; not ORDERS family |
| `orders`, `buy_outs`, `buyouts_sum_rub` | same funnel → CH | per nmid, day | historical | historical | gross funnel buyout rub | shop | analytics | Not attributed; not reconciliation denom for attribution |
| Supplier order row value (`totalPrice`, `priceWithDisc`, etc.) | statistics-api `GET /api/v1/supplier/orders` (ORDERS family ADR) | shop / nm filter in scripts | event-time MSK day | historical at order time | **ORDER_GMV** (cancel excluded in A1 scripts) | whole-shop or SKU in scripts | evidence scripts only | Not wired to product control; field choice varies by script |
| `attributed_orders` | attribution ingest ← promotion **fullstats** nm day | `shop×physical_adv×day×app×ordered_nm` | event_date | historical facts + latest projection | order count | **ATTRIBUTED** (DIRECT/LINKED) | COMPLETE coverage only for economics | UNKNOWN → no numeric economics |
| `attributed_gmv_rub` | same; mapped from `sum_price` / `sumPrice` on nm rows | same grain | event_date | historical | **ATTRIBUTED_ORDER_GMV** (WB fullstats) | attributed | COMPLETE + reconciliation | Not seller payout; not buyout |
| Campaign-day `orders`, `gmv_rub` | fullstats day totals | per physical_adv, day | event_date | reconciliation | campaign total | attributed aggregate | ingest | Used for reconciliation, not shop DRR |
| `spend_rub` (economics join) | CH `full_adv_wb_stat` (authority) | per physical_adv, day | event_date | historical | gross ad spend | campaign | required all days in window for AI economics | `STORE_DRR_NUMERATOR_STATUS = BLOCKED_BY_CAMPAIGN_COVERAGE` for shop-wide claim from common-sales path |
| `CPO_FACT_*` | `compute_cpo_fact` | window aggregate | window | derived | spend / attributed orders | DIRECT or LINKED | fail-closed | Not target/max CPO |
| `DRR_FACT_*` | `compute_drr_fact` | window aggregate | derived | spend / **attributed_gmv_rub** | DIRECT or LINKED | fail-closed | ratio not % | |
| `ProductCpoResolver` output `target_cpo_rub` / `max_cpo_rub` | pure domain | per product profile + price | instantaneous | **target policy** | `price × drr% / 100` | product | blocked without price | **Assumes** price basis aligns with intended DRR denominator |
| V3 `order_cpo_at_ch_point` / `expected_order_cost_rub` | CH keyword profile + smoothed `orders_per_cart` | campaign/keyword | ~7d smooth | **observed/predicted** | bid → expected order cost | campaign | runtime V3/PFO | Independent of DRR profile |
| `calc_pay_for_order` | bid math | keyword/campaign | derived | observed | 1000 / orders_per_1000_rub | campaign | V2/V3 | CPC/CPM path, not DRR |
| `factual_order_value` (A1) | supplier orders aggregation | store / SKU scripts | daily closed/open MSK | historical ORDER_GMV | gross | whole-shop | evidence | OPEN days partial |
| `SALE_PRICE_REFERENCE` (A1) | `POST …/list/goods/filter` `discountedPrice` | nm | snapshot | **current** list price | MIN size discounted; club ignored | product | candidate evidence | Not accepted as SoT |
| Promo `effective_fraction` | Redis promo state | shop/campaign | cached | current overlay | scales plan CPO columns | campaign | stale→0 | Does not define price semantics |

---

## CURRENT_SHOP_DRR

| Variant | Numerator | Denominator | Where | Status |
|---------|-----------|-------------|-------|--------|
| **A1 store / whole-shop scripts** | sum physical contour `full_adv_wb_stat` spend | `factual_order_value` = Σ non-cancel supplier-order `totalPrice×qty` (MSK day) | `a1_current_performance_drr_snapshot`, `a1_whole_store_daily_drr_collect`, `multi_client_strict_eight_target_directive_audit` | **Evidence / scripts only** |
| **Headroom in same scripts** | n/a | `allowed_spend = gmv × target_drr_fraction`; `headroom = allowed − spend` | same | uses **same ORDER_GMV** as actual DRR |
| **Production shop-runner** | — | — | — | **No** canonical shop actual DRR runtime; `shop-wide-common-sales` ADR **forbids** claiming full Store DRR / unblocking spend numerator (`BLOCKED_BY_CAMPAIGN_COVERAGE`) |
| **hierarchical Slice A (baseline)** | inputs `spend_rub`, `allowed_spend_rub` (ports TBD) | `ActualDrrObservation.actual_drr_percent` from fact port | `evaluate_shop_headroom_state` | **Contract only**; measurement window + denominator **not bound** in code |

**Window / lag / cancellations:** A1 uses MSK closed day = yesterday; cancellations excluded from GMV; open day marked partial. Attribution economics require **every day in window** COMPLETE + reconciliation PASS; package cutoff ≠ COMPLETE.

---

## CURRENT_PRODUCT_DRR

| Variant | Numerator | Denominator | Where |
|---------|-----------|-------------|-------|
| SKU factual scripts | allocated campaign spend to SKU | supplier-order GMV for nm (non-cancel) | `a1_sku_factual_ad_economics_collect` (`funnel_not_used_for_drr`) |
| Product **target** DRR | n/a | n/a | `DrrProfile` percents (configuration, not observed DRR) |
| Product **observed** DRR (control plane) | **EVIDENCE_GAP** | no production port | foundation defers to future runtime |

---

## CURRENT_CAMPAIGN_DRR

| Variant | Numerator | Denominator | Where |
|---------|-----------|-------------|-------|
| `DRR_FACT_DIRECT` | Σ spend (`full_adv_wb_stat`) | Σ DIRECT `attributed_gmv_rub` | `derived_metrics.compute_drr_fact` + AI package |
| `DRR_FACT_LINKED` | same | Σ LINKED `attributed_gmv_rub` | same |
| Strict audit totals | confirmed spend | confirmed orders or GMV from evidence sections | `strict_single_nmid_audit` (ratio `drr`) |
| Legacy UI/bot | **no DRR field** | — | CPO rub only |

Denominator class: **ATTRIBUTED_ORDER_GMV** (fullstats `sum_price`), not buyout, not supplier ORDERS, not `orders_sum` funnel.

---

## CURRENT_CPO_SEMANTICS

| Term | Meaning in repo | Consistent? |
|------|-----------------|-------------|
| **OBSERVED_CPO** | `CPO_FACT_*` = spend/attributed orders; V3/CH point CPO; spend-based “fact CPO” in shelf/auto paths | **No** single name — multiple formulas |
| **TARGET_CPO** | `target_price_for_order` OR `ProductCpoResolver.target_cpo_rub` | **Split brain** until adapter + semantics |
| **MAX_CPO** | `max_price_for_order` OR resolver `max_cpo_rub`; V3 may substitute fact | same |
| **BID / CPC / CPM** | auction mechanics | separate from DRR CPO |
| **COST_PER_ATTRIBUTED_ORDER** | `CPO_FACT_DIRECT` / `LINKED` | attribution only, COMPLETE coverage |

`resolve_target_cost`: if `fact_predict_orders >= plan.orders` → target else max (legacy plan semantics).

---

## CANONICAL_REVENUE_BASIS

| Use case | **NEW_PROPOSAL** (pending Owner) | Evidence today |
|----------|----------------------------------|----------------|
| **Attribution actual DRR/CPO** | **ATTRIBUTED_ORDER_GMV** (fullstats) | **ACCEPTED** spec + code |
| **Shop actual DRR (future controller)** | **ORDER_GMV** (supplier orders, non-cancel, documented field) | **FACT** in A1 scripts only; not accepted ADR |
| **DRR→CPO control translation** | Must match **same economic basis** as configured DRR% | **OWNER_DECISION_REQUIRED** — resolver uses **unit list/effective price** while actual DRR uses **GMV** |

---

## CANONICAL_ATTRIBUTION_BASIS

- **ACCEPTED:** DIRECT / LINKED / UNKNOWN at fullstats nm grain; spend from `full_adv_wb_stat`; no pair aggregate by default.
- **UNSUPPORTED V1:** attributed buyouts (`ATTRIBUTION_UNSUPPORTED`).
- **Forbidden:** supplier ORDERS / `wb_common_stat` as attribution reconciliation denominators.

---

## CANONICAL_PRICE_OBSERVATION

- **ACCEPTED_EXISTING_DECISION:** `ProductPricingReader` is sole control port; fail closed if missing (`BLOCKED_BY_PRODUCT_PRICE_SOURCE`).
- **EVIDENCE_GAP:** concrete WB field, multi-size rule, SPP/wallet/promo, staleness TTL.
- **Candidate (not accepted):** `a1_sale_price_snapshot` → `MIN(discountedPrice)`; transactional fallback → recent `totalPrice` AOV (`a1_transactional_sale_price_fallback`).

---

## PROPOSED_DRR_DENOMINATOR

| Scope | Proposed denominator token | Classification |
|-------|---------------------------|----------------|
| Campaign actual | `ATTRIBUTED_ORDER_GMV` | **FACT** (implemented) |
| Shop actual | `ORDER_GMV` (supplier orders, explicit field policy) | **NEW_PROPOSAL** aligned with A1 evidence |
| Product observed | `ORDER_GMV` at nm or attributed slice | **OWNER_DECISION_REQUIRED** |
| Configured DRR% | Policy percent | **FACT** (`DrrProfile`) — **basis unstated** |

---

## PROPOSED_DRR_TO_CPO_CONTRACT

**Only valid if** `effective_unit_price_rub` is defined on the **same revenue basis** as the DRR% definition Owner intends (e.g. if DRR% = spend / ORDER_GMV, then CPO cap ≈ `ORDER_GMV_per_order × DRR%`, not necessarily current shelf `discountedPrice`).

**ACCEPTED_EXISTING_DECISION (interim formula shape):** `target_cpo_rub = quantize(price × target_drr% / 100)` (`ProductCpoResolver`) — **blocked** until price SoT accepted.

**Fail-closed:** no production CPO actuation from DRR while `PRICE_SEMANTICS_ACCEPTED = NO` (`PRICE_SEMANTICS_NOT_ACCEPTED_CPO_ACTUATION_BLOCKED` in hierarchical Slice A).

---

## FRESHNESS_RULES

| Layer | Rule |
|-------|------|
| Attribution | COMPLETE coverage + per-day reconciliation; `source_complete_through`; open/partial window → no DIRECT/LINKED economics |
| Product price | `EffectiveProductPrice.observed_at` + future staleness policy (**EVIDENCE_GAP**) |
| Promo overlay | Redis stale / untrusted → fraction 0 |
| Shop common-sales | last-attempt Redis evidence; CH pre-existence ≠ skip collect |
| Hierarchical control | `DataSufficiency` must be `SUFFICIENT`; `STALE` / `INSUFFICIENT` / `UNKNOWN` → `NO_CONTROL_ACTION` |

---

## FAIL_CLOSED_RULES

Map to repo + proposed control-plane tokens:

| Blocker | Deterministic trigger |
|---------|----------------------|
| `PRICE_UNKNOWN` | `ProductPriceUnavailable` / `effective_product_price_rub is None` |
| `PRICE_STALE` | future TTL on `ProductPricingReader` (**policy gap**) |
| `DRR_FACT_STALE` | `ACTUAL_DRR_STALE` / `DataSufficiency.STALE` |
| `INSUFFICIENT_ATTRIBUTION` | coverage ≠ COMPLETE; UNKNOWN class rows |
| `ATTRIBUTION_WINDOW_INCOMPLETE` | partial days, reconciliation fail, package cutoff without source proof |
| `REVENUE_BASIS_UNSUPPORTED` | buyout-based control; mixed denominators without Owner basis |
| `CPO_INPUTS_INCOMPLETE` | missing spend day; zero denominator → absent metric (`DENOMINATOR_ZERO`); legacy `resolve_target_cost` → None |

Attribution codes: `BLOCKED_BY_ATTRIBUTION_FACTS`, `ATTRIBUTION_SOURCE_MISSING`, `DENOMINATOR_ZERO`, etc.

---

## COMPATIBILITY

| Foundation | Compatible? | Notes |
|------------|-------------|-------|
| Product Control `DrrProfile` | Yes | Configured target/max %; CPO resolver blocked on price |
| hierarchical Slice A | Yes | Triple + headroom; explicit price blocker |
| Attribution Facts | Yes | Campaign actual economics |
| ChangeSetV1 / Apply Authority | Neutral | No DRR/price fields in V1 apply scope |
| AdvSetting legacy CPO | Coexists | Canonical owner for **current** runtime rub CPO |
| V3/PFO/CPO runtime | Coexists | Orthogonal bid/conv CPO |

---

## SEMANTIC_CONFLICTS

1. **DRR% vs CPO rub:** `DrrProfile` expresses %; legacy `AdvSetting` stores rub CPO — no automatic bridge in production.
2. **Denominator mismatch risk:** `ProductCpoResolver` uses **unit price**; `DRR_FACT_*` uses **attributed GMV**; shop scripts use **supplier ORDER_GMV** — three distinct bases.
3. **“CPO” overload:** plan target/max rub, attribution fact CPO, V3 expected order cost, bid CPC — same label, different economics.
4. **Shop DRR:** evidence scripts vs ADR prohibition on claiming store DRR from campaign coverage path.
5. **Percent vs ratio:** `DrrProfile` uses percent 0–100; script `store_drr` often 0–1 fraction.

---

## EVIDENCE_GAPS

- Production `ProductPricingReader` implementation and WB field Owner choice.
- Staleness / abrupt price change policy.
- Canonical shop-level **actual DRR** runtime port (numerator/denominator/window).
- Product-level observed DRR.
- Net revenue / commission / logistics — **not represented** for control.
- SPP / wallet / customer-paid price dynamics — script notes only.
- Cloud checkout missing `ad_control_settings` at `f2b96e7` vs baseline `065509c` (use baseline for hierarchical citations).

---

## OWNER_DECISIONS_REQUIRED

1. **Control price observation** — (A) MIN `discountedPrice` (prices API); (B) seller list `price`; (C) transactional AOV from supplier orders; (D) other WB field. *Consequence:* defines `ProductCpoResolver` input and max/target CPO scale.
2. **DRR% denominator for shop/product policy** — align with (1) or with ORDER_GMV / ATTRIBUTED_ORDER_GMV. *Consequence:* whether `price × DRR%` is economically valid.
3. **Campaign control DRR basis** — DIRECT only vs DIRECT+LINKED vs separate caps. *Consequence:* which `DRR_FACT_*` feeds control vs reporting.
4. **Shop headroom denominator** — confirm `ORDER_GMV` (supplier) vs funnel `orders_sum`. *Consequence:* headroom magnitude and eligibility.
5. **Multi-size / multi-nm aggregation** — min price vs weighted AOV vs block (`PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS` already fail-closed).

---

## PRICE_SEMANTICS_ACCEPTED

**NO** (unchanged; Owner decisions remain).

---

## Severity backlog

| ID | Severity | Item |
|----|----------|------|
| S1 | **CRITICAL** | No accepted `effective_product_price` SoT — blocks DRR→CPO runtime |
| S2 | **CRITICAL** | DRR% denominator for shop control not ADR-bound (script vs attribution vs price) |
| S3 | **HIGH** | Dual CPO authorities (`AdvSetting` rub vs `ProductCpoResolver`) |
| S4 | **HIGH** | Shop store DRR not productionized; campaign coverage blocks numerator narrative |
| S5 | **MEDIUM** | Percent vs fraction inconsistency in tooling |
| S6 | **LOW** | `clubDiscountedPrice` / promo deposit semantics undocumented for control |

---

## FINAL_STATUS

**PRICE_SEMANTICS_READY_FOR_OWNER_DECISION**
