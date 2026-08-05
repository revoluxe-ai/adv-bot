## Why

Адаптер и wire ORDERS через generated Reports уже сданы (INC-RO-06), но боевой
сбор через новые клиенты ещё не доказан на prod: sales Stage A в семье может
оставаться выключенным, а readiness держится на unit без live Job archive с
реальными данными. Нужен один ограниченный increment: ORDERS+sales Stage A на
уже подключённых клиентах + smoke/tests + успешный prod Job collect с
получением реальных ORDERS/sales в локальном archive.

## Evolution Context

```text
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
CARD_PATH: openspec/evolution/wb-safe-readonly-collect.md
INCREMENT_ID: INC-RO-07
CURRENT_INCREMENT: Successful prod K8s Job collect + Owner receives real ORDERS/sales data proving generated Reports clients collect
CONTRIBUTION_TO_NORTH_STAR: Live proof that new Reports clients deliver real collect data via Job, not unit mocks
FORWARD_COMPATIBILITY_CONSTRAINTS:
- no invent URL; только existing generated Reports + wb/api adapters
- API только из Owner-bot Job; Cursor = plan/run/cp
- Stage A: dateFrom + first page; next_page_followed=NO
- L0 archive остаётся расширяемым к будущему CLEAN_DUMP
OUT_OF_SCOPE:
- Stage B pagination; Web PASS / READ_ONLY_PREFLIGHT_PASS
- swagger sync (INC-RO-02); API Master (INC-RO-03); token hardening (INC-RO-05)
- finance/write; Cursor→prod WB calls
- закрытие increment при пустых ORDERS+sales (даже при «зелёном» Job)
FUTURE_INCREMENTS (context only, not owed DoD):
- INC-RO-02…05 as on card
```

## What Changes

**Intent:** доказать live, что generated Reports клиенты реально собирают
данные: успешный prod Kubernetes Job `--mode collect` → локальный archive с
ненулевыми ORDERS и/или sales rows (не только unit mocks).

**Current behavior:** preflight/collect уже зовёт ORDERS first через Reports
adapter (`get_supplier_orders`, Stage A first page). Supplier sales GET в семье
описан как optional «when enabled», но операторский путь может не комбинировать
sales с ORDERS. Job collect мог проходить без DoD «реальные rows через новые
клиенты».

**Desired behavior:** семья `ORDERS_OR_SALES_REPORTS_READ` в Stage A MUST
включать supplier orders GET и supplier sales GET (оба first page, тот же
`dateFrom`/attestation). Targeted unit + smoke покрывают этот путь. Один
успешный prod Job `--mode collect` через `/opsx-scripts` сдаёт report +
Owner-local archive с **ненулевыми** rows ORDERS и/или sales и обновляет
ledger. PARTIAL по *другим* семьям допустим. Пустой ORDERS+sales **не**
закрывает change — повтор с другим окном/`shop_id` до появления данных.

**Scope in:**
- включить/зафиксировать sales GET Stage A в ORDERS family runner на existing
  Reports stack;
- unit/smoke под ORDERS+sales;
- один prod Job collect + получение реальных данных + ledger.

**Scope out:** см. Evolution Context `OUT_OF_SCOPE` / Future Increments.

**Risk:** пустое пилотное окно / токен / infra — Job может быть зелёным без
rows; DoD требует реальных данных, не «attempt only». Ошибочно расширить scope
до pagination/Web PASS.

**Rollback idea:** откатить wire sales в family runner и связанные тесты;
ledger notes откатить к предыдущему evidence; сгенерированный Reports client
не трогать (INC-RO-06 уже сдан).

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `wb-api-read-only-preflight`: сделать supplier sales GET обязательным в Stage A
  для `ORDERS_OR_SALES_REPORTS_READ` (orders+sales, first page); зафиксировать
  targeted/smoke и DoD Job-evidence: успешный prod collect Job + non-empty
  ORDERS/sales в archive как proof wired Reports stack (без Stage B / Web PASS).

## Impact

- Scripts entrypoint `wb_api_readonly_ops` (ORDERS family path) и его unit/smoke.
- Existing `app/core/mp/wb/api` Reports adapters/managers — только вызов уже
  доступного sales GET, без нового raw client и без mass swagger regen.
- `/opsx-scripts` Job + `scripts/REGISTRY.md` ledger как evidence plane.
- Architecture placement уже закрыт accepted decisions
  `openspec/decisions/scripts-wb-api-ops-stack/decision.md` и
  `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`;
  новый reusable decision не требуется, если change не меняет ownership/layering.
- Не затрагивает Free/Paid automation core, ставки, ApplyManager, finance/write.
