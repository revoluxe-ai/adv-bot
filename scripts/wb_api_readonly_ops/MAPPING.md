# Family → existing WB API stack (INC-RO-01 + INC-RO-06)

No new URLs. Gaps are reported, not invented.

| Family | Preflight (smallest) | Collect (bounded) | Module |
|--------|----------------------|-------------------|--------|
| orders_or_sales_reports_read | `ReportsManager.get_supplier_orders(date_from=2026-07-04)` one page; `next_page_followed=NO`; period model `DATE_FROM_CURSOR` | same Stage A depth (no cursor follow) | `app/core/mp/wb/api` reports / statistics-api |
| ads | `PromotionCountAdapter.get_cabinet_adv_ids` via `PromotionManager._client` | `PromotionManager.get_adverts_v2_by_ids` (capped ids) | `app/core/mp/wb/api` promotion |
| cards | `ProductsManager.get_cards_list` cursor.limit=1 | same, limit=100 first page | products |
| analytics | `WBDataManager.get_sales_funnel_products_history` for 1 nmid (from cards) yesterday→today | same for up to N nmids | analytics + promotion fullstats optional later |
| norms | `PromotionManager.get_supplier_subjects(payment_type=cpm)` | subjects + note GAP for `/adv/v0/config` and content directories (no adapter) | promotion product_cards adapter |

## ORDERS identity (INC-RO-06) — anti-substitution

`ORDERS_OR_SALES_REPORTS_READ` = statistics-api GET `/api/v1/supplier/orders`
(and optional `/sales`) only.

**MUST NOT** satisfy ORDERS via:

- analytics sales-funnel / nm-report / search-report product orders
- promotion fullstats / normquery (поле `orders` у РК)
- marketplace FBS/DBS/FBW assembly order APIs
- finance sales-reports

Period: API is `dateFrom` + cursor `lastChangeDate`. Stage A attests
`DATE_FROM_CURSOR` / first page / `next_page_followed=NO`. Do **not** claim
classic exact start+end. Do **not** silent-substitute yesterday→today for this
family (analytics may still use yesterday→today for its own probe).

## Known GAPs (honest, not DoD to invent)

- Norms&limits `GET /adv/v0/config` — generated client only, no domain adapter
- Content directories (categories/subjects/characteristics) — generated only, no adapter
- ORDERS Stage B pagination / CLEAN_DUMP — Future Increment (not INC-RO-06)

## Access

1. `get_access_for_wb_cabinet(shop_id)` — access plane proof
2. `WBManagerHubFactory.get_wb_manager_hub(shop_id)` — AuthClientHandler → managers
