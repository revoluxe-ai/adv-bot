# Family → existing WB API stack (INC-RO-01)

No new URLs. Gaps are reported, not invented.

| Family | Preflight (smallest) | Collect (bounded) | Module |
|--------|----------------------|-------------------|--------|
| ads | `PromotionCountAdapter.get_cabinet_adv_ids` via `PromotionManager._client` | `PromotionManager.get_adverts_v2_by_ids` (capped ids) | `app/core/mp/wb/api` promotion |
| cards | `ProductsManager.get_cards_list` cursor.limit=1 | same, limit=100 first page | products |
| analytics | `WBDataManager.get_sales_funnel_products_history` for 1 nmid (from cards) yesterday→today | same for up to N nmids | analytics + promotion fullstats optional later |
| norms | `PromotionManager.get_supplier_subjects(payment_type=cpm)` | subjects + note GAP for `/adv/v0/config` and content directories (no adapter) | promotion product_cards adapter |

## Known GAPs (honest, not DoD to invent)

- Norms&limits `GET /adv/v0/config` — generated client only, no domain adapter
- Content directories (categories/subjects/characteristics) — generated only, no adapter

## Access

1. `get_access_for_wb_cabinet(shop_id)` — access plane proof
2. `WBManagerHubFactory.get_wb_manager_hub(shop_id)` — AuthClientHandler → managers
