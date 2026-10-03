# Tasks — wb-readonly-job-smoke-reports

Owed scope (this change / `/opsx-apply`): **Stage A wire** ORDERS+sales в
`ORDERS_OR_SALES_REPORTS_READ` на existing Reports stack + unit/local smoke
(без live WB).

Не включать в apply / не owed DoD этого change:
- prod Job / `/opsx-scripts` RUN / kubectl cp / local archive delivery;
- ledger update из cluster evidence;
- закрытие evolution INC-RO-07 live-proof (это scripts/evolution lane).

Не включать вообще: Stage B / Web PASS / swagger sync / API Master / token
hardening.

## 1. Tests-first (characterization + regression)

- [x] 1.1 Расширить unit `test_orders_family`: characterization текущего
      orders-only Stage A (что sales ещё не вызывается) — baseline перед wire
- [x] 1.2 Добавить failing/target tests: Stage A MUST вызвать
      `get_supplier_orders` и `get_supplier_sales` с одним `dateFrom`,
      `next_page_followed=NO` (spec: Stage A requests orders and sales;
      ORDERS period attestation)
- [x] 1.3 Добавить paired test: orders OK + sales fail → family PARTIAL + sales
      gap + orders evidence retained (spec: Stage A family status when sales
      fails after orders)
- [x] 1.4 Добавить paired test: orders fail → family non-success / FAILED +
      orders gap (тот же requirement)
- [x] 1.5 Добавить/обновить test empty first page: пустые orders и/или sales →
      честный PARTIAL + gaps, не silent OK (runtime honesty)
- [x] 1.6 Убедиться, что anti-substitution (funnel/fullstats) по-прежнему не
      закрывает семью; sales не подменяется funnel

## 2. Wire sales Stage A в ORDERS family

- [x] 2.1 В `HubFamilyRunners.run_orders_or_sales_reports_read` вызвать
      existing `get_supplier_sales` через Reports manager / data manager
      (тот же `dateFrom`, flag как у orders Stage A); без invent URL / raw HTTP
- [x] 2.2 Собрать один `FamilyResult`: раздельные orders/sales в payload,
      общая attestation (`date_from`, `next_page_followed=NO`,
      `period_parameter_model`); статус per design (sales fail → PARTIAL)
- [x] 2.3 `assert_read_only_op` для sales; не вызывать другие Reports ops
- [x] 2.4 Обновить module/method docstrings (русский) со ссылкой на delta
      `wb-api-read-only-preflight` / wire Stage A
- [x] 2.5 Прогнать targeted unit:
      `poetry run pytest -m unit tests/unit/scripts/wb_api_readonly_ops/ -v`

## 3. Local smoke (без live WB)

- [x] 3.1 Узкий CLI/`--help` или import smoke entrypoint
      `wb_api_readonly_ops` (без Cursor→prod WB)
- [x] 3.2 При необходимости обновить notes в `scripts/REGISTRY.md` по
      local evidence (`tests=PARTIAL|COVERED`, `last_local_at`) — без
      `battle_tested=YES` и без cluster Job claim

## 4. Evolution link + gates

- [x] 4.1 Проверить, что card INC-RO-07 уже имеет
      `LINKED_CHANGES: wb-readonly-job-smoke-reports` (уже проставлено
      `/opsx-evolution`); при расхождении — поправить через evolution, не
      invent scope. Live Job proof для increment — вне owed tasks этого change.
- [x] 4.2 `poetry run pyright-strict` на затронутые пути (или project gate
      как принято) + `git diff --check`
- [x] 4.3 Self-check: нет Stage B pagination, нет Web PASS claim, нет нового
      raw client / swagger regen в diff этого change; нет `/opsx-scripts`
      orchestration в apply code
