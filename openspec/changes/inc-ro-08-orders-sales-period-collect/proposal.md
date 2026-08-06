## Why

INC-RO-07 доказал, что Stage A first-page collect по `ORDERS_OR_SALES_REPORTS_READ` через generated Reports реально отдаёт ORDERS/sales rows в Owner-local L0. Для исследования по окну COL-R03 (`2026-07-04..2026-08-02` Europe/Moscow) одной первой страницы недостаточно: нужен period-covered collect с честным follow cursor/`lastChangeDate` при finite ceiling. Без этого research dump остаётся smoke, а не срез за окно.

## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: wb-safe-readonly-collect
STAR_TITLE: Безопасный постоянный сбор WB API-данных
CARD_PATH: openspec/evolution/wb-safe-readonly-collect.md
NORTH_STAR: Operator Job → read-only WB dump by API map → local archive; no write/finance; no Cursor→prod API
INCREMENT_ID: INC-RO-08
CURRENT_INCREMENT: ORDERS_OR_SALES_REPORTS_READ collect with cursor/pagination over 2026-07-04..2026-08-02 Europe/Moscow for Дилера / WB-TEST-CABINET-001 → Owner-local L0 research zip with real rows (not Stage A first page)
CONTRIBUTION_TO_NORTH_STAR: period-covered ORDERS/sales research dump; first-page smoke alone is not enough for research over COL-R03 window
```

**IN_SCOPE (owed):**

- `mode=collect` только для семьи `ORDERS_OR_SALES_REPORTS_READ`
- период `2026-07-04..2026-08-02` Europe/Moscow
- follow cursor/pagination с finite page/time budget и честной attestation stop reason
- bound «Дилера» / `WB-TEST-CABINET-001` только аргументом Job
- Owner-local L0 research archive (+ sha256) + вызов через `/opsx-scripts` (live Job evidence может быть отложена Supervisor policy; capability и план invoke обязаны быть в артефактах)

**FORWARD_COMPATIBILITY_CONSTRAINTS:**

- не объявлять Web PASS / RETURN / `READ_ONLY_PREFLIGHT_PASS` из этого increment
- reuse generated Reports + accepted `orders-or-sales-reports-read-identity` (честная dateFrom/cursor модель)
- finite ceiling; no invent URL / raw HTTP client

**OUT_OF_SCOPE:**

- COL-R03-009 RETURN / `contract_preflight` / Web COLLECTOR
- Stage B CLEAN_DUMP / accept gates
- другие семьи как DoD
- swagger sync; token hardening; Cursor→prod API; finance/mutation

**FUTURE_INCREMENTS (context only, not owed):**

- INC-RO-04 map-driven permanent + Web CLEAN_DUMP / RETURN
- INC-RO-02 swagger sync on proven gap
- INC-RO-05 read-only token hardening

## What Changes

- Расширяется collect path семьи `ORDERS_OR_SALES_REPORTS_READ`: вместо Stage A «одна first page / `next_page_followed=NO`» появляется period collect с follow pagination/`lastChangeDate` до покрытия окна при finite page/time budget.
- В structured report / attestation фиксируются: period model (dateFrom + cursor, не classic exact start+end), `next_page_followed`, stop reason (period covered | ceiling hit | empty page | error), counts ORDERS и/или sales.
- Stage A / preflight first-page семантика **сохраняется** как отдельный режим поведения; INC-RO-08 не подменяет Stage A pagination-follow.
- L0 research zip остаётся Owner-local (payload + report, secret-strip); Web PASS/RETURN не вводится.
- Живой Job через `/opsx-scripts` планируется как evidence path increment; Supervisor может отложить live run — это не блокирует apply-ready артефактов.

## Capabilities

### New Capabilities

- (нет) — новая capability не вводится; расширяется существующий operator read-only collect контракт.

### Modified Capabilities

- `wb-api-read-only-preflight`: добавить требования period collect + cursor/pagination follow для `ORDERS_OR_SALES_REPORTS_READ` (finite ceiling, honest attestation, L0 archive semantics); Stage A first-page требования остаются в силе для Stage A/preflight.

## Impact

- **Intent:** один — INC-RO-08 period-covered ORDERS/sales research collect.
- **Current behavior:** Stage A collect/preflight — `dateFrom` на старт окна, одна страница, `next_page_followed=NO` (INC-RO-06/07).
- **Desired behavior:** collect mode семьи ORDERS умеет follow cursor до покрытия `2026-07-04..2026-08-02` Europe/Moscow или честного stop по ceiling/empty/error; L0 zip с реальными rows.
- **Affected surfaces:** `scripts/wb_api_readonly_ops` (orchestration), narrow Reports adapter/manager в `app/core/mp/wb/api`, structured report/attestation, `/opsx-scripts` Job plan for Dilera bound.
- **Decisions (accepted, cite):**
  - `openspec/decisions/scripts-wb-api-ops-stack/decision.md`
  - `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
- **Risk:** бесконечный pagination без ceiling; silent claim exact start+end; подмена семьи; объявление Web PASS.
- **Rollback idea:** оставить Stage A first-page path как default/safe; period+cursor path отключается флагом/режимом без удаления generated Reports.
- **Out of scope:** см. Evolution Context OUT_OF_SCOPE + FUTURE_INCREMENTS.
