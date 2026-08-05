## Why

Адаптер и wire ORDERS через generated Reports уже сданы (INC-RO-06), но sales
Stage A в семье `ORDERS_OR_SALES_REPORTS_READ` мог оставаться выключенным:
операторский путь зовёт только orders. Нужен ограниченный change: **создать**
обязательный ORDERS+sales Stage A на уже подключённых клиентах + unit/local
smoke. Live prod Job / локальный archive / ledger — **не** owed этого change;
их владеет `/opsx-scripts` (+ evolution INC-RO-07), не `/opsx-apply`.

## Evolution Context

```text
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
CARD_PATH: openspec/evolution/wb-safe-readonly-collect.md
INCREMENT_ID: INC-RO-07
CURRENT_INCREMENT: Successful prod K8s Job collect + Owner receives real ORDERS/sales data proving generated Reports clients collect
CONTRIBUTION_TO_NORTH_STAR: Wire ORDERS+sales Stage A on generated Reports stack so scripts-lane Job can collect real data (unit-proven; live Job not owed here)
FORWARD_COMPATIBILITY_CONSTRAINTS:
- no invent URL; только existing generated Reports + wb/api adapters
- API только из Owner-bot Job; Cursor = plan/run/cp (не apply)
- Stage A: dateFrom + first page; next_page_followed=NO
- L0 archive остаётся расширяемым к будущему CLEAN_DUMP
OUT_OF_SCOPE:
- Stage B pagination; Web PASS / READ_ONLY_PREFLIGHT_PASS
- swagger sync (INC-RO-02); API Master (INC-RO-03); token hardening (INC-RO-05)
- finance/write; Cursor→prod WB calls
- prod Job evidence / `/opsx-scripts` RUN / kubectl cp / Owner-local archive delivery
- ledger update from cluster Job (scripts lane)
- закрытие evolution INC-RO-07 live-proof DoD внутри этого change
FUTURE_INCREMENTS (context only, not owed DoD):
- INC-RO-02…05 as on card
- live Job+archive proof for INC-RO-07 via /opsx-scripts (not apply tasks)
```

## What Changes

**Intent:** сделать supplier sales GET обязательным в Stage A семьи
`ORDERS_OR_SALES_REPORTS_READ` на existing Reports stack и закрыть это
unit/local smoke. Не включать тестирование скрипта через `/opsx-scripts` в
apply DoD.

**Current behavior:** preflight/collect уже зовёт ORDERS first через Reports
adapter (`get_supplier_orders`, Stage A first page). Supplier sales GET в семье
описан как optional «when enabled», но операторский путь может не комбинировать
sales с ORDERS.

**Desired behavior:** семья `ORDERS_OR_SALES_REPORTS_READ` в Stage A MUST
включать supplier orders GET и supplier sales GET (оба first page, тот же
`dateFrom`/attestation). Targeted unit + узкий local smoke (без live WB)
покрывают этот путь. Prod Job / archive / ledger — вне scope change apply.

**Scope in:**
- включить/зафиксировать sales GET Stage A в ORDERS family runner на existing
  Reports stack;
- unit + узкий local smoke под ORDERS+sales.

**Scope out:** см. Evolution Context `OUT_OF_SCOPE` / Future Increments
(включая весь `/opsx-scripts` Job evidence plane).

**Risk:** ошибочно вернуть Job/cp в apply tasks; ошибочно расширить scope
до pagination/Web PASS.

**Rollback idea:** откатить wire sales в family runner и связанные тесты;
сгенерированный Reports client не трогать (INC-RO-06 уже сдан).

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `wb-api-read-only-preflight`: сделать supplier sales GET обязательным в Stage A
  для `ORDERS_OR_SALES_REPORTS_READ` (orders+sales, first page); targeted unit
  без live WB. Job/archive evidence **не** requirement этого change.

## Impact

- Scripts entrypoint `wb_api_readonly_ops` (ORDERS family path) и его unit/smoke.
- Existing `app/core/mp/wb/api` Reports adapters/managers — только вызов уже
  доступного sales GET, без нового raw client и без mass swagger regen.
- `/opsx-scripts` Job + ledger — **не** impact/owed этого change (отдельная
  scripts lane для evolution live-proof).
- Architecture placement уже закрыт accepted decisions
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md` и
  `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`;
  новый reusable decision не требуется, если change не меняет ownership/layering.
- Не затрагивает Free/Paid automation core, ставки, ApplyManager, finance/write.
