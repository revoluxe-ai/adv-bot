## Evolution Context (owed)

```text
STAR_ID: wb-safe-readonly-collect
INCREMENT_ID: INC-RO-06
CURRENT_INCREMENT: полный generate Reports-клиента + узкий adapter
  (GET supplier orders/sales) + period attestation + wire
  ORDERS_OR_SALES_REPORTS_READ первым в wb_api_readonly_ops;
  unit tests без live prod
```

Future (не owed): COL-R03-009 packager, Stage B pagination, INC-RO-02
auto-refresh, CLEAN_DUMP, token hardening.

Spec: `specs/wb-api-read-only-preflight/spec.md`  
Design: `design.md`  
Decisions: `orders-or-sales-reports-read-identity` (Proposed) + accepted
`scripts-wb-api-ops-stack`

## 1. Tests-first (unit)

- [x] 1.1 Unit: orchestrator / family order — `ORDERS_OR_SALES_REPORTS_READ`
  выполняется **первой**; docstring ссылается на Requirement
  `ORDERS_OR_SALES_REPORTS_READ family` (спека delta)
  *(re-verified 2026-08-04 apply: test_orders_family green)*
- [x] 1.2 Unit: anti-substitution — успех funnel / fullstats / search-report
  **не** засчитывается как OK для ORDERS family (падает, если guard убрать);
  paired: при реальном ORDERS runner → OK/PARTIAL по его результату
- [x] 1.3 Unit: period Stage A — вызов ORDERS использует `dateFrom` на
  `2026-07-04` (Moscow); **не** yesterday→today; `next_page` / follow
  `lastChangeDate` не вызывается (Requirement: ORDERS period attestation)
- [x] 1.4 Unit: adapter (или facade) принимает mock HTTP/client response для
  GET supplier orders; не использует invent URL вне generated client path
- [x] 1.5 Unit: generator mapping — `reports` присутствует в
  `SWAGGER_TARGETS` (или эквивалент), English `12-reports.yaml`,
  `skip_transliteration=True` (Requirement: Reports client generation
  procedure)
  *(test_reports_swagger_target_mapping_english_no_transliteration)*

## 2. Generate Reports OpenAPI client

- [x] 2.1 Добавить `reports` в `tools/generate_wb_api_client.py`
  (`SWAGGER_TARGETS`): en URL/`12-reports.yaml`,
  `target_root=…/generated/reports`, package name, `skip_transliteration=True`
- [x] 2.2 Подготовить `generated/reports/vN/swagger/12-reports.yaml` из
  inventory `swagger_inventory/2026-08-04/yaml/en/12-reports.yaml`
- [x] 2.3 Сгенерировать клиент:
  `poetry run python tools/generate_wb_api_client.py --spec-key reports --force-version N --use-cached-spec`;
  проверить `spec.lock.json` + package; не удалять чужие `v*`
- [x] 2.4 Обновить таблицу в `app/core/mp/wb/api/generated/doc.md` строкой
  `reports`

## 3. Domain adapter + hub (узкий surface)

- [x] 3.1 Реализовать adapter GET `/api/v1/supplier/orders` (+ при
  необходимости `sales`) поверх generated Reports client; docstrings на
  русском со ссылкой на ORDERS identity decision / spec
- [x] 3.2 Пробросить методы в domain manager / hub так, чтобы
  `wb_api_readonly_ops` вызывал только orders (и optional sales); остальные
  Reports ops не экспонировать в readonly path
- [x] 3.3 `assert_read_only_op` / denylist: не открывать mutation/finance
  через новый фасад

## 4. Wire `wb_api_readonly_ops`

- [x] 4.1 Добавить семью `ORDERS_OR_SALES_REPORTS_READ` (или contract alias) в
  models / `FAMILY_ORDER` **первой**
- [x] 4.2 Runner preflight/collect: вызов adapter; period `dateFrom`;
  one page; gaps честные; не подставлять analytics
- [x] 4.3 Обновить `MAPPING.md`: ORDERS → statistics-api GET; явный GAP note
  что funnel/fullstats ≠ ORDERS; period model dateFrom/cursor
- [x] 4.4 CLI/period: для ORDERS не использовать default yesterday→today
  (contract window start `2026-07-04` для pilot attestation)

## 5. Quality gates

- [x] 5.1 `poetry run pytest -m unit` на targeted
  `tests/unit/scripts/wb_api_readonly_ops/` + новые adapter tests
- [x] 5.2 `poetry run pyright-strict` на затронутых модулях
- [x] 5.3 `git diff --check` на изменённых файлах
- [x] 5.4 Подтвердить: нет live statistics-api вызовов в unit path; нет
  COL-R03 packager / Stage B в diff (scope INC-RO-06 only)

## Telegram UI / Message Safety

Не применимо: change не меняет Telegram bot UI / captions / callback_data.
