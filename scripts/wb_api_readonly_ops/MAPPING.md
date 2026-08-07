# Family → existing WB API stack (INC-RO-01 + INC-RO-06)

No new URLs. Gaps are reported, not invented.

| Family | Preflight (smallest) | Collect (bounded) | Module |
|--------|----------------------|-------------------|--------|
| orders_or_sales_reports_read | `ReportsManager.get_supplier_orders(date_from=2026-07-04)` one page; `next_page_followed=NO`; period model `DATE_FROM_CURSOR` | same Stage A depth (no cursor follow) | `app/core/mp/wb/api` reports / statistics-api |
| ads | `PromotionCountAdapter.get_cabinet_adv_ids` via `PromotionManager._client` | `PromotionManager.get_adverts_v2_by_ids` (capped ids) | `app/core/mp/wb/api` promotion |
| cards | `ProductsManager.get_cards_list` cursor.limit=1 | same, limit=100 first page | products |
| analytics | `WBDataManager.get_sales_funnel_products_history` for 1 nmid (from cards) yesterday→today | same for up to N nmids | analytics + promotion fullstats optional later |
| norms | `PromotionManager.get_supplier_subjects(payment_type=cpm)` | subjects + note GAP for `/adv/v0/config` and content directories (no adapter) | promotion product_cards adapter |

## COL-R04-001 contract_preflight (primary Lab ZIP)

| Flag | Primary | Notes |
|------|---------|-------|
| `--contract COL-R04-001 --artifact-class contract_preflight` | `COL-R04-001_OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04.zip` + `.sha256` | r04 authority under `authority/COL-R04-001/`; `GET_OR_DOCUMENTED_POST_AS_READ`; cabinet B1 must be NEW (r03/r03b bytes ≠ PASS); mass collection forbidden |

Control-plane: Local Cursor must **not** call production cabinet/API. Credentialed
execution = Owner-bot / cluster Job only. `shop_id` is Job/CLI binding only —
never inside return ZIP.

## COL-R03-009 contract_preflight (primary RETURN)

Delta specs: `wb-readonly-contract-preflight-return`,
`wb-api-read-only-preflight` (contract CLI).
Decision: change-local `wb-readonly-contract-return-vs-l0` (+ accepted
`scripts-wb-api-ops-stack`).

| Artifact class | Primary | Side |
|----------------|---------|------|
| `contract_preflight` + `--contract COL-R03-009` | `…_COL-R03-009_RETURN.zip` + `.sha256` | L0 only with `--emit-l0-side` (opt-in) |
| `l0_research` / no contract | `wb_readonly_research.zip` | n/a — **not** Web COLLECTOR handoff |
| `clean_dump` | requires `READ_ONLY_PREFLIGHT_PASS=YES` accept file before API | Web PASS **not** claimed by Job |

Mapping gate (honest, no invent URL):

| Alias | Gate |
|-------|------|
| API-PROMOTION-CAMPAIGNS | PASS_MAP — GET `/adv/v1/promotion/count` (existing adapter) |
| API-ORDERS-SALES | REFUSED + exact blockers (contemporaneous attestation not claimed PASS_MAP here) |
| API-PROMOTION-STATISTICS | REFUSED + exact blockers |
| API-CONTENT-CARDS | REFUSED — no GET-only cards list |

`api_preflight=REFUSED` still packages RETURN. L0 research zip MUST NOT be
primary under COL-R03-009. Job MUST NOT assert Web `READ_ONLY_PREFLIGHT_PASS`.

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
- Full contemporaneous PASS_CANDIDATE for all four COL-R03-009 aliases — Owner
  follow-up; packager ships honest REFUSED RETURN today

## Access

1. `get_access_for_wb_cabinet(shop_id)` — access plane proof (L0 path)
2. `WBManagerHubFactory.get_wb_manager_hub(shop_id)` — AuthClientHandler → managers
3. Contract RETURN path: attestation packager; shop_id never inside RETURN zip
