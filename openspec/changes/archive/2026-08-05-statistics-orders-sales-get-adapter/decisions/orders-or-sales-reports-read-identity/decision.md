# Decision: Identity of ORDERS_OR_SALES_REPORTS_READ

## Status

Accepted

<!-- Promoted to openspec/decisions/orders-or-sales-reports-read-identity/ on archive 2026-08-05 -->

## Context

Operator read-only preflight/collect и будущий COL-R03 Stage A требуют семью
`ORDERS_OR_SALES_REPORTS_READ`. В продукте уже есть другие источники «заказов»:
analytics sales-funnel, search-report product orders, promotion fullstats
(поле `orders`), FBS assembly orders. Их легко ошибочно подставить как
закрытие семьи. Accepted decision
`openspec/decisions/scripts-wb-api-ops-stack/decision.md` задаёт ownership
scripts→`wb/api` и `READ_ONLY_NO_MUTATION`, но **не** фиксирует identity этой
семьи данных. Нужен reusable domain invariant до реализации INC-RO-06 и
последующих COL-R03 increments.

## Decision

Семья `ORDERS_OR_SALES_REPORTS_READ` MUST означать только read ленты/отчёта
заказов и/или продаж поставщика через **statistics-api** endpoints:

- `GET /api/v1/supplier/orders`
- и/или `GET /api/v1/supplier/sales`

на host `statistics-api.wildberries.ru` (или sandbox-эквивалент), по контракту
из локального swagger inventory Reports (`12-reports`), без invent URL.

Доступ MUST идти через слой `app/core/mp/wb/api` (adapter/manager), в духе
`scripts-wb-api-ops-stack`. Orchestration (порядок семей, Stage A first page,
period attestation) может жить в `scripts/wb_api_readonly_ops`, но **не**
переопределять identity семьи.

Period semantics для этой семьи MUST описываться честно относительно API
(`dateFrom` / cursor `lastChangeDate`): нельзя заявлять classic exact
`start+end`, если параметр end в контракте API отсутствует.

## Applies to

- Capability `wb-api-read-only-preflight` и связанные operator Job scripts
- Mapping / preflight / collect для alias `ORDERS_OR_SALES_REPORTS_READ` /
  `API-ORDERS-SALES`
- Будущие COL-R03 / map-driven collect increments, пока они используют ту же
  семью
- Любой новый код, который утверждает «закрыли orders/sales reports» для
  audit/COLLECTOR

## Allowed

- Полная генерация OpenAPI-клиента Reports из inventory `12-reports.yaml`
  (`generated/…/vN` + swagger + `spec.lock`)
- Domain adapter + manager, которые **пробрасывают только** GET supplier
  orders/sales (узкий public surface); остальной generated API не экспонировать
  в operator/readonly path
- Wire семьи в `wb_api_readonly_ops` как первой в preflight
- Stage A: один first-page GET с `dateFrom` на начало окна; `next_page_followed=NO`
- Явная attestation модели периода (`DATE_FROM` / cursor), включая honest
  REFUSED/`REQUIRED_PERIOD_UNSUPPORTED`, если контракт COL-R03 требует
  невозможное для API
- Unit tests с fake/httpx mock без live prod

## Forbidden

- Подмена семьи через:
  - analytics sales-funnel / nm-report / search-report (в т.ч. POST-read
    `…/search-report/product/orders`)
  - promotion fullstats / normquery stats (метрика `orders` у РК)
  - marketplace FBS/DBS/FBW assembly order APIs
  - finance sales-reports
- Invent URL / raw HTTP в обход generated Reports-клиента из swagger inventory
- Проброс в readonly_ops произвольных методов полного Reports-клиента сверх
  orders/sales
- Silent `yesterday→today` как «контрактный период» ORDERS family
- Follow pagination/`lastChangeDate` в Stage A preflight под видом одной
  first page
- Объявление Web `READ_ONLY_PREFLIGHT_PASS` из этого ops-класса

## Examples

Good:

- `wb_api_readonly_ops` вызывает manager → statistics-api GET
  `/api/v1/supplier/orders?dateFrom=2026-07-04…`, одна страница, gap/attestation
  про cursor period записаны честно

Bad:

- Preflight помечает ORDERS_OR_SALES = OK после
  `get_sales_funnel_products_history` или fullstats с полем `orders`
- «Orders» закрыты через `GET /api/v3/orders` (FBS assembly)

## Related specs

- `openspec/specs/wb-api-read-only-preflight/spec.md` (delta в этом change)
- Frozen COL-R03-009 (context): aggregate promotion/analytics orders MUST NOT
  satisfy ORDERS_OR_SALES_REPORTS_READ

## Related changes

- `openspec/changes/statistics-orders-sales-get-adapter` (INC-RO-06)
- Accepted baseline: `openspec/decisions/scripts-wb-api-ops-stack/decision.md`
- Archived: `wb-readonly-api-preflight` (INC-RO-01; семьи без ORDERS)

## Review checklist

- [x] existing decisions searched (`scripts-wb-api-ops-stack` — ownership/stack;
      не покрывает identity ORDERS family)
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing for this
      domain invariant
- [x] implementation layer matches decision (apply INC-RO-06: generated
      reports client + narrow adapter/manager in `app/core/mp/wb/api`;
      ORDERS family first in `scripts/wb_api_readonly_ops`; no funnel
      substitution)
