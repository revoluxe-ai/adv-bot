## Context

INC-RO-06 уже сдал generated Reports client + domain adapter/manager
(`get_supplier_orders` / `get_supplier_sales`) и wire ORDERS first в
`wb_api_readonly_ops`. Текущий family runner зовёт только orders Stage A;
sales GET в стеке есть, но в семье не комбинируется. Unit-покрытие ORDERS
есть; DoD конца change — успешный **prod** Job collect + **реальные**
ORDERS/sales данные у Owner, доказывающие сбор через новые клиенты.

Stakeholders: Owner (Job + ledger), operator scripts lane (`/opsx-scripts`).
Constraints: `READ_ONLY_NO_MUTATION`, Job-only API, no invent URL, Stage A
first page only.

## Evolution Context

- **Title (STAR_ID):** Безопасный постоянный сбор WB API-данных
  (`wb-safe-readonly-collect`)
- **INCREMENT_ID:** `INC-RO-07`
- **CURRENT_INCREMENT:** Successful prod K8s Job collect + Owner receives real
  ORDERS/sales data proving generated Reports clients collect
- **CONTRIBUTION_TO_NORTH_STAR:** Live proof that new Reports clients deliver
  real collect data via Job, not unit mocks
- **LINKED_CHANGES (card):** `wb-readonly-job-smoke-reports` (уже на карточке)

Как design уважает forward-compat без Future Increments:

- Calls только через existing Reports adapters/managers (не raw HTTP, не
  swagger regen / API Master).
- Period: тот же `dateFrom` + first page для orders и sales;
  `next_page_followed=NO` — Stage B pagination не открываем.
- L0 archive/report path остаётся расширяемым; Web CLEAN_DUMP / PASS не
  объявляем.
- Evidence plane = prod `/opsx-scripts` Job + локальный archive с реальными
  rows + ledger; не Cursor→prod WB.

## Goals / Non-Goals

**Goals:**

- В Stage A семья `ORDERS_OR_SALES_REPORTS_READ` выполняет оба GET: supplier
  orders и supplier sales (один `dateFrom`, по одной first page).
- Targeted unit (+ узкий smoke) подтверждают комбинированный payload /
  attestation / gaps.
- Один успешный prod Kubernetes Job `--mode collect` через `/opsx-scripts`
  даёт report + Owner-local archive с ненулевыми rows ORDERS и/или sales и
  обновляет ledger.
- PARTIAL по *другим* семьям (norms и т.п.) допустим.

**Non-Goals:**

- Stage B cursor pagination / CLEAN_DUMP / `READ_ONLY_PREFLIGHT_PASS`
- Swagger sync, API Master map, token hardening
- Новый Reports client version / invent URL
- Finance/write; Cursor→prod API
- Требование «все семьи OK» как DoD
- Закрытие increment при пустых ORDERS+sales (даже при terminal Job success)

## Architecture Decision References

- `openspec/decisions/scripts-wb-api-ops-stack/decision.md` — Job-only
  execution, existing `wb/api`, finite retries, secret-strip L0,
  `READ_ONLY_NO_MUTATION`
- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` —
  identity ORDERS = statistics-api supplier orders/sales; Stage A first page;
  запрет funnel/FBS/fullstats substitute
- Change-local lookup: `decisions/REUSE.md` — **Architecture Decision Missing**
  нет; новый proposed decision не нужен

## Ownership & Placement

| Layer | Role |
|-------|------|
| **Owner** | `scripts/wb_api_readonly_ops` — orchestration семьи, Stage A combine orders+sales, report/attestation fields |
| **Allowed** | Existing `ReportsManager` / adapter / `WbDataManager.get_supplier_*`; unit tests under `tests/unit/scripts/wb_api_readonly_ops/`; ledger via `/opsx-scripts` |
| **Forbidden** | Raw HTTP / invent statistics URL; calling funnel/search-report/fullstats/FBS as ORDERS; Cursor→prod WB; pagination follow in Stage A; mass swagger regen |

Rationale: identity и stack ownership уже accepted; этот change только
включает уже разрешённый sales surface в family runner и доказывает prod Job
path с реальными данными.

## Decisions

1. **Sales обязателен в Stage A, не feature-flag «optional»**  
   Почему: proposal DoD = ORDERS+sales; optional оставлял gap «client wired,
   family не зовёт».  
   Альтернатива: оставить optional — отвергнута (не доказывает contribution).

2. **Один family result, два source-блока в payload**  
   Orders и sales в одном `FamilyResult` с attestation
   (`date_from`, `next_page_followed=NO`, `period_parameter_model`) и раздельными
   counts/gaps. Статус семьи: failure orders → FAILED; sales fail при OK
   orders → PARTIAL+gap (сохранить orders evidence).  
   Альтернатива: две отдельные семьи — отвергнута (ломает identity alias и
   preflight-first order).

3. **Не трогать generated Reports `vN` / generator mapping**  
   `get_supplier_sales` уже в adapter/manager. Apply = wire + tests + Job.  
   Альтернатива: regen client «на всякий случай» — out of scope / INC-RO-02.

4. **Evidence: успешный prod `/opsx-scripts` collect Job + real rows**  
   Apply завершает code/tests; Job evidence — Owner `RUN GO` на prod contour;
   archive MUST содержать ненулевые ORDERS и/или sales. Unit-only / empty
   ORDERS+sales не закрывают INC-RO-07.  
   Альтернатива: «Job terminal достаточно» — отвергнута Owner DoD.

5. **PARTIAL других семей не блокирует DoD; empty ORDERS+sales — блокирует**  
   DoD смотрит на ORDERS+sales real data + prod Job + ledger.

## Risks / Trade-offs

- [Пустая first page ORDERS+sales] → PARTIAL в report OK как honesty, но
  change **не** DELIVERED → сменить `dateFrom`/`shop_id` и повторить Job.
- [Sales API error при OK orders] → PARTIAL + sales gap; для close DoD нужны
  ненулевые rows хотя бы в одной из двух лент (orders или sales).
- [Job image/token/infra fail] → не крутить Cursor→WB; scripts/devops lane.
- [Scope creep в pagination/Web PASS] → verify drift = NO_GO.
- [Dirty tree блокирует PUSH/RUN] → Job после clean/push tip.

## Migration Plan

1. Wire sales Stage A в ORDERS family runner + unit/smoke green.
2. `/opsx-scripts` PLAN_RUN → RUN GO (Owner) `--mode collect` на Dilera /
   `shop_id` аргументом (prod K8s).
3. Скопировать known outputs; убедиться в ненулевых ORDERS и/или sales;
   обновить `scripts/REGISTRY.md` по evidence.
4. Evolution `LINKED_CHANGES` уже указывает на этот change — при archive не
   забыть History.

**Rollback:** revert family runner + tests; ledger notes откатить; Reports
client не откатывать.

## Open Questions

- (закрыто) Job mode для evidence: **`collect`**.
- (закрыто) sales-only failure при OK orders: family status **PARTIAL**.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (не требуется — см. REUSE.md)
- [x] implementation layer matches decision
