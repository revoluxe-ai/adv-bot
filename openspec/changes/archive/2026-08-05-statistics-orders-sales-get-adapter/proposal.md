## Why

COL-R03 / map-driven collect требуют семью `ORDERS_OR_SALES_REPORTS_READ` как
GET statistics-api (`/api/v1/supplier/orders`, при необходимости `…/sales`).
Сейчас в `wb_api_readonly_ops` этой семьи нет: analytics = funnel/search-report
(POST-read) и не закрывает orders; domain adapter на statistics-api отсутствует,
поэтому mapping честно упирается в gap. Нужно закрыть INC-RO-06 до Stage A
packager: adapter + аттестация периода `dateFrom` / first page, без подмены
другими API и без silent `yesterday→today`.

## Evolution Context

```text
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
INCREMENT_ID: INC-RO-06
CURRENT_INCREMENT: Domain adapter GET statistics-api supplier orders (+ sales)
  + честная period attestation (dateFrom, first page, next_page_followed=NO)
  + wire ORDERS_OR_SALES_REPORTS_READ первой в wb_api_readonly_ops preflight;
  unit tests без live prod API.
CONTRIBUTION_TO_NORTH_STAR: Без GET orders/sales family нельзя честно закрыть
  COL-R03 / map-driven collect alias #1; funnel/FBS/search-report не подходят.
FORWARD_COMPATIBILITY_CONSTRAINTS:
- только existing wb/api stack; no invent URL (источник — swagger inventory 12-reports)
- READ_ONLY_NO_MUTATION; для будущего COL-R03 GET_ONLY: POST-read ≠ GET
- ORDERS ≠ funnel / search-report / FBS assembly
OUT_OF_SCOPE (этот change):
- полный COL-R03-009 RETURN packager / 00_STATUS ZIP
- cards GET_ONLY workaround
- Stage B pagination / CLEAN_DUMP / READ_ONLY_PREFLIGHT_PASS
- live Dilera preflight из Cursor
- mass swagger regen / INC-RO-02 auto-refresh
- finance/wallet/payout
FUTURE_INCREMENTS (context only, не DoD):
- COL-R03-009 Stage A packager + gates
- INC-RO-02 swagger auto-refresh
- INC-RO-03 API Master map
- INC-RO-04 Stage B / CLEAN_DUMP
- INC-RO-05 token hardening
```

Только `CURRENT_INCREMENT` — owed scope этого change.

## What Changes

### Intent

Добавить в существующий WB API stack read-only доступ к statistics-api
supplier orders (и sales при необходимости) и включить эту семью первой в
операторский preflight/collect path с честной моделью периода.

### Current behavior

- Preflight/collect покрывают семьи ads / cards / analytics / norms.
- Analytics использует sales-funnel / связанные read-пути; период по умолчанию
  близкий к «вчера→сегодня», не контрактное окно COL-R03.
- Отдельной семьи ORDERS_OR_SALES и domain-доступа к
  `GET …/api/v1/supplier/orders|sales` нет → gap / подмена недопустима.

### Desired behavior

- Через existing stack доступен GET-only read statistics-api supplier orders
  (sales — по необходимости того же family): **полный** generated Reports
  client из swagger inventory + узкий adapter surface только этих методов.
- `wb_api_readonly_ops` в preflight (и collect в рамках той же семьи) включает
  `ORDERS_OR_SALES_REPORTS_READ` **первой** среди семей.
- Period: для Stage A — `dateFrom` на начало окна `2026-07-04` (Europe/Moscow),
  ровно одна first page, без follow по `lastChangeDate`; семантика периода
  явно аттестуется (не маскируется под exact start+end, если API так не умеет).
- Не использовать funnel, search-report product orders, FBS assembly orders
  как ORDERS_OR_SALES.
- Unit-тесты без вызовов prod WB API.

### Scope in

- **Полная генерация** WB Reports OpenAPI-клиента из локального swagger
  inventory (`12-reports.yaml`) в `generated/…/vN` + `spec.lock` (как у
  promotion/products) — не invent URL и не одноразовый raw HTTP.
- Domain adapter / manager **пробрасывает только нужные методы**:
  GET supplier orders и (при необходимости того же family) sales; остальные
  операции generated-клиента в operator/readonly path не экспонировать.
- Wire семьи ORDERS в readonly_ops с порядком «первой» и period attestation.
- Обновление наблюдаемого поведения capability preflight/collect.
- Targeted unit tests.

### Scope out

См. Evolution Context `OUT_OF_SCOPE` и `FUTURE_INCREMENTS`.

### Risk

- Неверная семантика периода (заявить EXACT_RANGE при cursor-`dateFrom`) →
  ложный PASS для будущего COL-R03.
- Случайная подмена analytics/FBS → нарушение domain invariant.
- Generate полного Reports-клиента обязателен; риск — случайно вызвать/
  пробросить лишние reports/finance-adjacent методы в readonly_ops (mitigation:
  узкий adapter surface только orders/sales).

### Rollback idea

Отключить/не вызывать новую семью в entrypoint; оставить gap-статус как до
change; adapter можно оставить неиспользуемым или откатить отдельным revert
без затрагивания paid automation write-path.

## Capabilities

### New Capabilities

- (нет) — поведение входит в расширение существующей operator read-only
  capability, без отдельного product surface.

### Modified Capabilities

- `wb-api-read-only-preflight`: добавить семью `ORDERS_OR_SALES_REPORTS_READ`
  (GET statistics-api supplier orders/sales через existing stack), порядок
  preflight с этой семьёй первой, честная period attestation для
  `dateFrom` / first-page / no next-page follow; запрет подмены funnel /
  search-report / FBS; сохранить `READ_ONLY_NO_MUTATION` и запрет invent URL.

## Impact

- Затрагивает operator scripts read-only preflight/collect и слой
  `app/core/mp/wb/api` (новый read adapter в рамках accepted decision
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md`).
- Не меняет Free/Paid bot UX, ставки, mutation writers, finance.
- Execution path по-прежнему Owner-bot Job / `/opsx-scripts`; Cursor не
  становится runtime для prod API.
- Зависимость от локального swagger inventory Reports как источника контракта
  path/method (не invent URL).
