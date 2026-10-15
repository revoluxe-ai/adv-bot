---
cursor:
  subagentId: "bc-b6d7ca2b-966e-5d2d-94fc-2b92a12223d0"
---

# product-control-context — planning inventory (adv-bot)

Evidence paths: `app/modules/common_slaves/wildberries/models/models.py` (WBCard, WBCategory, AdvSetting), `complex_adv.py` (`main_nmid`), `shop-wide-common-sales-ownership`, `strict-single-nmid-audit-evidence`, `AutoShelfBidControlSettings` (nmid-keyed precedent), `campaign_settings_contract`, `wb_sky_control_plane` ChangeSet `SalesPolicyPayload`.

## Cardinality (proved)

| Relation | Finding |
|----------|---------|
| Campaign → nmID | **1:N** — `AdvSetting.nmids` JSONB list; WB legacy `Adv.nmids` from `autoParams.nms` / united `nms`; connect-existing-advs tests include campaigns with multiple `nm_settings`. |
| Product → campaign | **1:N** — same nmID can match multiple WB adverts; coordinator builds `nmid_to_adv_ids: dict[int, set[int]]` from `main_nmid` only. |
| ComplexAdv legs | **1 auto + 0..1 search** — `_search_adv_id` → second `AdvSetting` row; `all_adv_ids` = {auto adv_id, search adv_id}. |
| WBCard ↔ AdvSetting | **ORM 1:N** (`AdvSetting.wb_cards`) + optional `WBCard.adv_setting_id` (nullable); no write-path evidence that FK is authoritative for bindings. |
| WBCard identity | **Global unique `nmid`** (not per shop); `wb_cabinet_id` nullable — shop-wide ADR: WBCard loader not all-shop assortment SoT. |

## main_nmid

- **Convention only**: `ComplexAdv.main_nmid` = `sorted(nmids)[0]`; AI keyword scope uses same rule (`_resolve_main_nmid`).
- **Not durable SoT**; multi-nmid campaigns: auto-shelf increment **skips** (`single_nmid_guard_multiple`); scripts flag `multi_nmid_advsetting_shared_campaign_spend_not_allocated`.
- **Fail-closed** for product control when `len(nmids)!=1` or economics disagree across members → `AMBIGUOUS_PRODUCT_MEMBERSHIP` / unsupported effective state (align `strict-single-nmid-audit-evidence`).

## Economics today

- **Configured CPO (rub)**: `AdvSetting.target_price_for_order`, `max_price_for_order` (+ plan gate via `resolve_target_cost` / promo overlay).
- **Funnel facts**: `default_db.wb_common_stat` grain `(nmid, date)` — shop-wide writer + campaign-scoped reads via adv nmids.
- **DRR**: no runtime fields; AI Package defines `SKU_DRR` / `TARGET_CPO_IDENTITY` (`reference revenue per order * target DRR`) as **identity-only**, not implemented.
- **EVIDENCE_GAP**: single authoritative **reference revenue per order** owner for DRR→CPO derivation (not fully specified in code).

## Proposed boundaries (planning)

- **ProductControlSettings** — mutable control keyed `(shop_id, nmid)`; DRR fields first; enrollment flag (no behavior change until set).
- **ShopControlSettings** — keyed `shop_id` / `wb_cabinet_id`; shop DRR defaults.
- **CategoryControlSettings** — keyed `(wb_cabinet_id, wbcategory.id)`; defer until taxonomy stable.
- **CampaignProductBinding** — read-model: `shop_id`, `adv_setting_id`, `physical_adv_id`, `leg_role` (AUTO/SEARCH), `nmid`, `membership_role`, `effective_*`, `provenance` (PG snapshot / WB meta); materialize later.
- **ProductEconomicsResolver** — port: CH common stat + catalog facts; explicit gaps, no guess.
- **EffectiveControlResolver** — SKU > SHOP > LEGACY (AdvSetting CPO); later CATEGORY between SKU and SHOP.
- **Campaign adapter** — maps resolved `target_cpo_rub` / `max_cpo_rub` into existing runtime (`target_pay_for_order` path) with legacy fallback.

## Migration (strangler)

1. Domain types + ports + ADRs (no PG).
2. Read-only binding projection from `AdvSetting`/`ComplexAdv`.
3. PG tables + enrollment.
4. DRR slice + CPO derivation behind flag.
5. Shop-runner adapter (per-shop enroll).
6. UI/Excel/ChangeSet/AI Package consumers.
7. Retire campaign-owned economics only after proof.

## ADRs required before apply

- Product control aggregate ownership & keys (`shop_id` + `nmid`).
- Binding model vs `main_nmid` convention.
- Economics resolver inputs & fail-closed ambiguity.
- Relationship to nmid-only `AutoShelfBidControlSettings` (global unique nmid).

## Materialized (2026-10-07 Owner GO)

OpenSpec change: `openspec/changes/product-control-context/`  
Decisions: `decisions/product-control-aggregate-ownership`, `campaign-product-binding-ownership`, `product-pricing-and-cpo-ownership` (Proposed; pricing EVIDENCE_GAP).
