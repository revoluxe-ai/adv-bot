# Tasks — wb-readonly-job-smoke-reports

Owed scope: **INC-RO-07** — successful prod K8s Job `--mode collect` + Owner
receives **real** (non-empty) ORDERS and/or sales data proving generated
Reports clients collect; plus Stage A wire + unit/smoke + ledger.  
Не включать: Stage B / Web PASS / swagger sync / API Master / token hardening;
не закрывать change при пустых ORDERS+sales.

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
      честный PARTIAL + gaps, не silent OK (runtime honesty; DoD close всё равно
      требует non-empty на Job evidence)
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
      `wb-api-read-only-preflight` / INC-RO-07
- [x] 2.5 Прогнать targeted unit:
      `poetry run pytest -m unit tests/unit/scripts/wb_api_readonly_ops/ -v`

## 3. Local smoke (без live WB)

- [x] 3.1 Узкий CLI/`--help` или import smoke entrypoint
      `wb_api_readonly_ops` (без Cursor→prod WB)
- [x] 3.2 При необходимости обновить notes в `scripts/REGISTRY.md` по
      local evidence (`tests=PARTIAL|COVERED`, `last_local_at`) — без
      `battle_tested=YES`

## 4. Prod Job evidence + real data (`/opsx-scripts`, Owner GO)

- [x] 4.1 Подготовить PLAN_RUN: script WB API read-only preflight/collect,
      **`--mode collect`**, `--shop-id` аргументом (Dilera допустим), prod
      Owner-bot Job contour
      → `openspec/changes/wb-readonly-job-smoke-reports/JOB_EVIDENCE_PLAN.md`
- [ ] 4.2 После apply code green: Owner `/opsx-scripts RUN GO` — один Job;
      дождаться successful terminal; скопировать known outputs / archive
- [ ] 4.3 Проверить report: `ORDERS_OR_SALES_REPORTS_READ` Stage A orders+sales
      attempts; PARTIAL других семей допустим
- [ ] 4.4 Проверить archive: **ненулевые** rows ORDERS и/или sales; если оба
      пусты — НЕ закрывать change, повторить с другим `dateFrom`/`shop_id`
- [ ] 4.5 Обновить ledger из Job evidence (`runnable`, `last_cluster_*`,
      `last_image_ref`, notes) — unit-only / empty ORDERS+sales ≠ Job proof
- [ ] 4.6 Зафиксировать evidence path/Job name + note о non-empty rows в change
      notes (для verify)

## 5. Evolution link + gates

- [x] 5.1 Проверить, что card INC-RO-07 уже имеет
      `LINKED_CHANGES: wb-readonly-job-smoke-reports` (уже проставлено
      `/opsx-evolution`); при расхождении — поправить через evolution, не
      invent scope
- [x] 5.2 `poetry run pyright-strict` на затронутые пути (или project gate
      как принято) + `git diff --check`
- [x] 5.3 Self-check: нет Stage B pagination, нет Web PASS claim, нет нового
      raw client / swagger regen в diff этого change
