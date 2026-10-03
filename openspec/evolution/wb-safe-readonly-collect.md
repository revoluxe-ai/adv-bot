# Безопасный постоянный сбор WB API-данных

```text
STAR_ID: wb-safe-readonly-collect
STATUS: ACTIVE
OWNER: Owner
CREATED_AT: 2026-08-04T04:47:00Z
UPDATED_AT: 2026-08-06T11:57:52Z
```

## North Star

Оператор одной командой / Kubernetes Job получает read-only выгрузку данных
Wildberries по `shop_id` из карты возможностей API (актуальные swagger →
allowlist семей эндпоинтов) в архив на локаль — без write/finance и без
прямых вызовов prod API с локального Cursor.

## Capability Scope

- Aliases: COLLECTOR API lane, Dilera pilot, API Master, swagger sync,
  `/opsx-scripts` collect, READ_ONLY_NO_MUTATION, COL-R03 Stage A/B,
  Owner-local L0 archive
- Domains: `scripts/`, existing WB API generated clients/adapters,
  Owner-bot Job runtime (`ops-script-runner`), research archive /
  future Web CLEAN_DUMP
- Included outcomes:
  - INC-RO-01: preflight + best-effort 4-family collect + gap report +
    Owner-local L0 archive (secret-strip) on existing clients
  - INC-RO-06: generated Reports client + narrow GET supplier orders/sales
    adapter + ORDERS_OR_SALES_REPORTS_READ first in wb_api_readonly_ops
    with honest dateFrom / first-page attestation
  - INC-RO-07: successful prod K8s Job collect on wired Reports
    (ORDERS + sales Stage A) + Owner receives real ORDERS/sales data proving
    generated clients collect; unit/smoke + ledger
  - INC-RO-03: API Master map path×method from local swagger (delivered)
  - INC-RO-08: ORDERS/sales period collect with cursor/pagination over
    COL-R03 window → Owner-local L0 research zip (not Stage A first page)
  - Stage B / map-driven permanent collect + Web CLEAN_DUMP / RETURN accept
    (future; includes COL-R03-009 contract_preflight)
  - one-command swagger status/sync при доказанном gap
- Excluded outcomes:
  - finance / wallet / payout
  - WB write / mutation endpoints
  - ownership Web COLLECTOR / PROCESSOR / RHP
  - cabinet DevTools collection
  - local Cursor → prod API execution path

## Evolution Path

### INC-RO-01 — Best-effort collect + L0 archive via Job

```text
STATUS: DELIVERED
LINKED_CHANGES: wb-readonly-api-preflight
```

Outcome:

Scripts-entrypoint + `/opsx-scripts` Job принимает `--shop-id` и
`--mode preflight|collect`. Читает 4 семьи (ads / cards / analytics /
norms) через уже существующие `get_access_for_wb_cabinet` +
`app/core/mp/wb/api` clients/adapters (policy `READ_ONLY_NO_MUTATION`,
POST-read допустим). Reuse shop-runner retry/rate-limit/timeout + finite
run ceiling. `preflight` — smallest probe; `collect` — best-effort pull
с честным PARTIAL + gap report. Сдаёт Owner-local research-архив
(payload + report, secret-strip only, + sha256) с абсолютным локальным
путём после `kubectl cp`. Боевой прогон: магазин «Дилера» (`shop_id`
только аргументом Job, не навсегда в коде).

Contribution to North Star:

Даёт первый повторяемый proof, что Owner-bot Job умеет безопасно читать
WB API и сдавать реальный research-dump — без этого карта/swagger не
превращаются в исследование.

Scope boundary:

Не включает Web L2 sanitize / quarantine→transfer, Web CLEAN_DUMP /
Stage B accept gate / `READ_ONLY_PREFLIGHT_PASS`, swagger regen,
API Master, read-only token hardening, finance/write.

Evidence / completion:

Успешный Job + локальный archive path в `SCRIPTS_REPORT`; ledger
entry runnable обновлён по evidence. `battle_tested` — только через
отдельный Owner `RECORD_BATTLE`.

### INC-RO-02 — One-command swagger status/sync

```text
STATUS: CANDIDATE
LINKED_CHANGES: wb-api-swagger-inventory-ops (scaffold; not linked until gap)
```

Outcome:

Высокоуровневая команда поверх `tools/generate_wb_api_client.py`:
status / sync изменённых swagger → next `vN` client.

Contribution to North Star:

Держит локальные swagger актуальными как source of truth для API Master
и последующего map-driven collect.

Scope boundary:

Запускать только при доказанном gap в исследовании (нет/устарел
эндпоинт в текущем клиенте). Не обязательный следующий шаг после
INC-RO-01.

Evidence / completion:

Отчёт status/sync; при sync — новый `vN` + `spec.lock.json`.

### INC-RO-03 — API Master: карта из локальных swagger

```text
STATUS: DELIVERED
LINKED_CHANGES: wb-api-master-swagger-map
```

Outcome:

Команда строит карту path × method × семья из уже сохранённых
`vN/swagger/*.yaml` (без сети, без генерации клиента).

Contribution to North Star:

Даёт оператору/collect явный allowlist возможностей API вместо
угадывания URL.

Scope boundary:

Только разбор локальных спек; не collect и не swagger download.

Evidence / completion:

1. Change archived
   `openspec/changes/archive/2026-08-05-wb-api-master-swagger-map/`
   (tasks §1–3 complete).
2. Main spec synced: `openspec/specs/wb-api-master-map/spec.md`.
3. Accepted decision:
   `openspec/decisions/wb-api-master-local-swagger-map/decision.md`.

### INC-RO-04 — Map-driven permanent collect + Web CLEAN_DUMP / Stage B

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome:

Постоянный collect по allowlist API Master / карте, period args, Web
CLEAN_DUMP package (L2 sanitize где нужен transfer), Stage B accept /
`READ_ONLY_PREFLIGHT_PASS` gate для пилотного Web-контура, включая
COL-R03-009 `contract_preflight` / primary RETURN.zip. Не дублирует
уже owed research L0 (INC-RO-01 / INC-RO-07 / INC-RO-08).

Contribution to North Star:

Закрывает «раз и сразу собрали по карте» для постоянного операторского
и Web-compatible сценария.

Scope boundary:

Не Web PROCESSOR/RHP; не finance/write. Best-effort / period research
L0 dumps закрыты INC-RO-01 / INC-RO-07 / INC-RO-08 — не Web PASS.

Evidence / completion:

Успешный Job/Web package path; gap-лог при PARTIAL; accept gate evidence
где применимо.

### INC-RO-05 — Read-only token / hardening

```text
STATUS: CANDIDATE
LINKED_CHANGES: none
```

Outcome:

Ужесточение credential plane (предпочтение read-only token category и
смежные защиты) без смены collect UX.

Contribution to North Star:

Снижает риск mutation при операторских прогонах.

Scope boundary:

Не блокирует INC-RO-01…04; включается после рабочего collect path.

Evidence / completion:

Доказанный bind token category + отсутствие write capability в прогоне.

### INC-RO-06 — Domain adapter GET statistics-api ORDERS (+ sales) + wire

```text
STATUS: DELIVERED
LINKED_CHANGES: statistics-orders-sales-get-adapter
```

Outcome:

Полный generate Reports OpenAPI-клиента из inventory `12-reports.yaml` +
узкий domain adapter/manager (только GET supplier orders и при необходимости
sales) + wire семьи `ORDERS_OR_SALES_REPORTS_READ` **первой** в
`wb_api_readonly_ops` preflight/collect. Stage A: `dateFrom` на начало
пилотного окна, одна first page, `next_page_followed=NO`, честная attestation
модели периода (не silent yesterday→today). Unit tests без live prod
statistics-api.

Contribution to North Star:

Без GET orders/sales family нельзя честно закрыть COL-R03 / map-driven
collect alias #1; funnel / FBS / search-report / promotion fullstats не
являются ORDERS_OR_SALES.

Scope boundary:

Не включает COL-R03-009 RETURN packager / Web PASS, Stage B cursor
pagination / CLEAN_DUMP, live Dilera preflight из Cursor, mass swagger
regen (INC-RO-02), cards GET_ONLY workaround, finance/wallet/payout.

Evidence / completion:

Generated `reports/vN` + swagger lock; adapter/manager в `wb/api`;
ORDERS family first в readonly_ops + MAPPING attestation; targeted unit
tests green без live API.

### INC-RO-07 — Prod Job collect + real ORDERS/sales data (wired Reports)

```text
STATUS: DELIVERED
LINKED_CHANGES: wb-readonly-job-smoke-reports
```

Outcome:

Успешный Kubernetes Job на prod (контур `/opsx-scripts` / Owner-bot) с
`wb_api_readonly_ops --mode collect` на уже подключённом generated Reports +
domain adapter path (ORDERS + sales GET Stage A). Оператор получает локальный
research archive (payload + report, secret-strip) с **реальными** данными
orders и/или sales (ненулевые rows), доказывающими что новые Reports-клиенты
реально собирают данные — не unit mocks и не пустой Job без данных.
Targeted unit/smoke + ledger обязательны как ворота, но недостаточны для
закрытия increment. Без нового raw HTTP client, без Stage B pagination, без
Web CLEAN_DUMP.

Contribution to North Star:

Live proof: «новые клиенты подключили» → prod Job → реальные ORDERS/sales
данные у Owner — следующий кирпич к постоянному сбору.

Scope boundary:

Не включает INC-RO-02 swagger sync, INC-RO-03 API Master, INC-RO-04 Stage B /
Web CLEAN_DUMP / `READ_ONLY_PREFLIGHT_PASS`, INC-RO-05 token hardening,
finance/write, Cursor→prod WB calls. PARTIAL по *другим* семьям (norms и т.п.)
не блокирует DoD. Пустой ORDERS+sales при «зелёном» Job **не** закрывает
increment — нужен повтор/другое окно/`shop_id` до появления реальных rows.

Evidence / completion:

1. Sales+orders Stage A wire в ORDERS family + targeted unit/smoke green —
   OpenSpec change archived
   `openspec/changes/archive/2026-08-05-wb-readonly-job-smoke-reports/`.
2. Prod Job `ops-script-wb-ro-collect-20260805-072757` (`--mode collect`)
   Complete exit 0 via `/opsx-scripts`.
3. Local archive
   `.tmp/opsx-scripts/20260805-072757/outputs/wb_readonly_research.zip`
   with ORDERS rows_count=1188 and sales rows_count=801 (Stage A
   `dateFrom` / first page / `next_page_followed=NO`).
4. Ledger `scripts/REGISTRY.md` updated from Job evidence
   (`runnable=WORKS`, image `b1e6b2f8…`, notes).

### INC-RO-08 — ORDERS/sales period collect + cursor (research L0)

```text
STATUS: ACTIVE
LINKED_CHANGES: none
```

Outcome:

Job `wb_api_readonly_ops --mode collect` для семьи
`ORDERS_OR_SALES_REPORTS_READ` на bound «Дилера» /
`WB-TEST-CABINET-001`, окно `2026-07-04..2026-08-02` Europe/Moscow.
Не Stage A first-page: follow pagination / `lastChangeDate` (cursor)
до покрытия period при finite page/time budget и честном stop reason.
Owner получает L0 research zip (+ sha256) с реальными ORDERS и/или
sales rows за окно; attestation периода/курсора честная.

Contribution to North Star:

Без period-coverage collect research остаётся на first-page smoke
(INC-RO-07); добор страниц даёт пригодный для исследования срез
ORDERS/sales по COL-R03 окну.

Scope boundary:

IN: только `ORDERS_OR_SALES_REPORTS_READ` через generated Reports +
existing adapter; `mode=collect`; period выше; cursor/pagination follow;
bound arg-only; Owner-local L0 + report; unit/smoke на cursor loop +
ceiling; live Job через `/opsx-scripts`.

OUT: Web COLLECTOR / COL-R03-009 RETURN / `contract_preflight`; Stage B
accept / CLEAN_DUMP / `READ_ONLY_PREFLIGHT_PASS`; другие семьи как DoD;
invent URL / raw HTTP; swagger sync / API Master / token hardening;
Cursor→prod WB; finance/mutation; бесконечный pagination без ceiling.

Evidence / completion:

1. Code + targeted unit/smoke: cursor/period collect path green.
2. Prod Job via `/opsx-scripts` Complete exit 0.
3. Local L0 zip: ORDERS и/или sales rows за окно; attestation
   `next_page_followed` / stop reason / period model.
4. Ledger / SCRIPTS_REPORT обновлены по Job evidence.

## Forward Compatibility Constraints

- Не вводить новый raw HTTP-клиент WB; расширять только существующие
  managers/adapters при необходимости.
- Ретраи/лимиты — reuse production WB API patterns (shop-runner path),
  finite budget, no hang.
- Owner-local L0 archive (payload + report, secret-strip) должен допускать
  расширение до будущего Web CLEAN_DUMP / L2 package для тех же 4
  endpoint aliases — без требования L2 в INC-RO-01 / INC-RO-08.
- Путь `generated/<key>/vN/swagger/` остаётся будущим SoT для API Master;
  INC-RO-01 не должен ломать эту конвенцию.
- Policy исполнения API: `READ_ONLY_NO_MUTATION` (не литерал HTTP GET_ONLY).
- Execution contour: API только из Owner-bot Job runtime; Cursor — plan/run/cp.
- ORDERS_OR_SALES только через generated Reports + `wb/api` (no invent URL;
  источник — swagger inventory `12-reports`).
- ORDERS ≠ funnel / search-report / FBS assembly / promotion fullstats.
- Для будущего COL-R03 GET_ONLY: POST-read ≠ GET; Stage A period = dateFrom /
  cursor attestation, не ложный exact start+end.
- INC-RO-08 cursor/period collect MUST NOT объявлять Web PASS / RETURN /
  `READ_ONLY_PREFLIGHT_PASS`; Web accept остаётся INC-RO-04.
- Cursor/pagination MUST reuse honest dateFrom/`lastChangeDate` model from
  `orders-or-sales-reports-read-identity`; finite page/time ceiling required.

## Non-Goals

- Объявление Web `READ_ONLY_PREFLIGHT_PASS` из INC-RO-01 runtime
- Finance / payout / wallet API
- POST/PUT/PATCH/DELETE с mutation semantics
- Автоматический полный swagger regen «на всякий случай» без gap
- Замена Web COLLECTOR / PROCESSOR контуров
- Web-grade body/ID redaction как DoD INC-RO-01

## Related North Stars

- None.

## History

- 2026-08-06T11:57:52Z — INC-RO-03 marked DELIVERED (archived map change +
  main spec); INC-RO-08 ACTIVE (ORDERS/sales period collect + cursor for
  research L0; Дилера / WB-TEST-CABINET-001; window 2026-07-04..2026-08-02
  Europe/Moscow); Web RETURN / COL-R03-009 parked under INC-RO-04 Future;
  exactly one ACTIVE.
- 2026-08-05T07:59:05Z — INC-RO-07 DELIVERED (prod Job + real ORDERS/sales
  archive; change archived); INC-RO-03 ACTIVE (API Master from local swagger);
  exactly one ACTIVE.
- 2026-08-05T06:37:00Z — INC-RO-07 DoD sharpened: successful prod K8s Job
  collect + real ORDERS/sales archive data proving generated Reports clients;
  LINKED_CHANGES → `wb-readonly-job-smoke-reports`; empty ORDERS+sales no longer
  closes increment.
- 2026-08-05T05:44:00Z — INC-RO-07 ACTIVE (Job smoke collect on wired
  Reports ORDERS+sales Stage A + tests/ledger); INC-RO-06 marked DELIVERED
  (exactly one ACTIVE); linked change pending `/opsx-ff` or `/opsx-new`.
- 2026-08-04T23:18:52Z — INC-RO-06 ACTIVE (Reports GET orders/sales adapter
  + ORDERS family wire); linked `statistics-orders-sales-get-adapter`;
  INC-RO-01 marked DELIVERED (exactly one ACTIVE).
- 2026-08-04T05:24:57Z — INC-RO-01 revised to B+L0 (preflight +
  best-effort collect + Owner-local secret-strip archive); linked
  `wb-readonly-api-preflight`; INC-RO-04 narrowed to map-driven /
  Web CLEAN_DUMP / Stage B (no duplicate of INC-RO-01 research dump).
- 2026-08-04T04:47:00Z — card created; ACTIVE increment INC-RO-01
  (preflight Job); swagger/API Master/collect-full/token = CANDIDATE,
  swagger sync triggered by research gap only.
