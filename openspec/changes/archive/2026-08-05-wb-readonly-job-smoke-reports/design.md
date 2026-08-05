## Context

INC-RO-06 уже сдал generated Reports client + domain adapter/manager
(`get_supplier_orders` / `get_supplier_sales`) и wire ORDERS first в
`wb_api_readonly_ops`. Текущий family runner зовёт только orders Stage A;
sales GET в стеке есть, но в семье не комбинируется.

Этот change owed: **создать** комбинированный Stage A ORDERS+sales + unit.
Live Job / Owner archive / ledger — ownership `/opsx-scripts` (и evolution
INC-RO-07), не `/opsx-apply`.

Stakeholders: implementer (wire+tests); Owner/scripts lane отдельно для Job.
Constraints: `READ_ONLY_NO_MUTATION`, no invent URL, Stage A first page only;
Cursor→prod WB запрещён в apply.

## Evolution Context

- **Title (STAR_ID):** Безопасный постоянный сбор WB API-данных
  (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** `INC-RO-07`
- **CURRENT_INCREMENT:** Successful prod K8s Job collect + Owner receives real
  ORDERS/sales data proving generated Reports clients collect
- **CONTRIBUTION_TO_NORTH_STAR:** Wire ORDERS+sales Stage A on generated
  Reports stack (unit-proven); live Job proof remains scripts/evolution lane
- **LINKED_CHANGES (card):** `wb-readonly-job-smoke-reports` (уже на карточке)

Как design уважает forward-compat без Future Increments:

- Calls только через existing Reports adapters/managers (не raw HTTP, не
  swagger regen / API Master).
- Period: тот же `dateFrom` + first page для orders и sales;
  `next_page_followed=NO` — Stage B pagination не открываем.
- L0 archive/report path остаётся расширяемым; Web CLEAN_DUMP / PASS не
  объявляем.
- Apply **не** владеет evidence plane Job/cp/ledger.

## Goals / Non-Goals

**Goals:**

- В Stage A семья `ORDERS_OR_SALES_REPORTS_READ` выполняет оба GET: supplier
  orders и supplier sales (один `dateFrom`, по одной first page).
- Targeted unit (+ узкий local smoke без live WB) подтверждают комбинированный
  payload / attestation / gaps.

**Non-Goals:**

- Stage B cursor pagination / CLEAN_DUMP / `READ_ONLY_PREFLIGHT_PASS`
- Swagger sync, API Master map, token hardening
- Новый Reports client version / invent URL
- Finance/write; Cursor→prod API
- Prod `/opsx-scripts` Job, kubectl cp, Owner-local archive delivery, ledger
  update from cluster — **не** apply DoD
- Закрытие evolution INC-RO-07 live-proof внутри этого change
- Требование «все семьи OK» как DoD

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — Job-only
  execution, existing `wb/api`, finite retries, secret-strip L0,
  `READ_ONLY_NO_MUTATION` (Job path exists; this change does not own running it)
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  identity ORDERS = statistics-api supplier orders/sales; Stage A first page;
  запрет funnel/FBS/fullstats substitute
- Change-local lookup: `decisions/REUSE.md` — **Architecture Decision Missing**
  нет; новый proposed decision не нужен

## Ownership & Placement

| Layer | Role |
|-------|------|
| **Owner (this change)** | `scripts/wb_api_readonly_ops` — orchestration семьи, Stage A combine orders+sales, report/attestation fields |
| **Allowed** | Existing `ReportsManager` / adapter / `WbDataManager.get_supplier_*`; unit tests under `tests/unit/scripts/wb_api_readonly_ops/` |
| **Not owed here** | `/opsx-scripts` RUN, Job template hold/cp, cluster ledger updates, Owner-local zip delivery |
| **Forbidden** | Raw HTTP / invent statistics URL; calling funnel/search-report/fullstats/FBS as ORDERS; Cursor→prod WB; pagination follow in Stage A; mass swagger regen |

Rationale: identity и stack ownership уже accepted; этот change только
включает уже разрешённый sales surface в family runner. Live proof — отдельный
process owner.

## Decisions

1. **Sales обязателен в Stage A, не feature-flag «optional»**  
   Почему: proposal = ORDERS+sales wire; optional оставлял gap «client wired,
   family не зовёт».  
   Альтернатива: оставить optional — отвергнута.

2. **Один family result, два source-блока в payload**  
   Orders и sales в одном `FamilyResult` с attestation
   (`date_from`, `next_page_followed=NO`, `period_parameter_model`) и раздельными
   counts/gaps. Статус семьи: failure orders → FAILED; sales fail при OK
   orders → PARTIAL+gap (сохранить orders evidence).  
   Альтернатива: две отдельные семьи — отвергнута (ломает identity alias и
   preflight-first order).

3. **Не трогать generated Reports `vN` / generator mapping**  
   `get_supplier_sales` уже в adapter/manager. Apply = wire + unit/local smoke.  
   Альтернатива: regen client «на всякий случай» — out of scope / INC-RO-02.

4. **Job/scripts evidence вне owed apply**  
   Prod collect Job, local archive copy, ledger из cluster — `/opsx-scripts`
   (+ evolution DoD), не tasks `/opsx-apply`. Change не требует Job green для
   archive этого planning scope.  
   Альтернатива: держать § Job evidence в tasks — отвергнута (смешивает
   owners; см. pipeline analysis).

5. **PARTIAL других семей / empty pages — honesty, не Job DoD этого change**  
   Unit фиксирует честный PARTIAL на empty; live non-empty rows — scripts lane.

## Risks / Trade-offs

- [Scope creep вернуть Job в apply] → update/verify drift = NO_GO.
- [Scope creep в pagination/Web PASS] → verify drift = NO_GO.
- [Evolution INC-RO-07 live DoD ≠ change apply complete] → явно: wire может
  быть сдан, пока Job/archive ещё на scripts lane (не путать owners).

## Migration Plan

1. Wire sales Stage A в ORDERS family runner + unit/local smoke green.
2. (Отдельно, не apply) Owner `/opsx-scripts` для live INC-RO-07 evidence —
   вне owed tasks этого change.
3. Evolution `LINKED_CHANGES` уже указывает на этот change — при archive не
   забыть History; не утверждать live Job DoD только потому что wire сдан.

**Rollback:** revert family runner + tests; Reports client не откатывать.

## Open Questions

- (закрыто) sales-only failure при OK orders: family status **PARTIAL**.
- (закрыто) Job evidence в apply tasks: **нет** — scripts lane.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (не требуется — см. REUSE.md)
- [x] implementation layer matches decision
