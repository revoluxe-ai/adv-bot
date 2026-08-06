## 1. Tests-first: парсер и инварианты карты

- [x] 1.1 Добавить unit-фикстуры минимальных OpenAPI YAML (несколько path/method,
      одна family) для capability `wb-api-master-map`
- [x] 1.2 Тест: из fixture YAML извлекаются только объявленные path×method;
      invent/hardcoded URL отсутствуют (spec: Offline API Master map /
      No invent URL)
- [x] 1.3 Тест: family записи = identity источника fixture, не произвольная
      метка (spec: Family bound to swagger source)
- [x] 1.4 Тест: два прогона на тех же входах → одинаковый machine-readable
      inventory (stable sort; timestamp metadata исключён из compare)
      (spec: Deterministic inventory artifact)
- [x] 1.5 Тест: missing/unreadable source → gap/failure без fabricated
      entries; полный провал источников ≠ silent success
      (spec: Honest gaps)
- [x] 1.6 Тест: CLI/API построения карты не требует shop_id/token и не
      вызывает WB (spec: Map does not authorize WB calls)
- [x] 1.7 Тест: не-GET methods из YAML попадают в inventory (spec: Mutation
      filter out of scope)

## 2. Tooling: offline map builder в `tools/`

- [x] 2.1 Реализовать модуль разбора локальных swagger → entries
      `{path, method, family}` в `tools/` (ownership:
      `wb-api-master-local-swagger-map`)
- [x] 2.2 CLI: указать output path; по умолчанию сканировать known family
      roots / latest `vN` с `swagger/*.yaml` (или явный override); без сети
      и без вызова codegen/`generate_wb_api_client` download ветки
- [x] 2.3 Эмит детерминированного JSON inventory (+ опциональный human view,
      не единственный SoT)
- [x] 2.4 Gap report / non-success при отсутствии пригодных источников
- [x] 2.5 Краткая регистрация/usage note для оператора (REGISTRY или
      docstring/`--help`) без Job collect DoD

## 3. Проверка на реальных локальных vN

- [x] 3.1 Прогнать CLI на существующих local generated swagger (как минимум
      families с YAML на диске) → артефакт path×method×family
- [x] 3.2 Подтвердить: в артефакте нет path вне YAML; прогон offline
- [x] 3.3 Прогнать unit-набор из §1 (`poetry run pytest` targeted)

## Out of scope (не owed; не чекбоксы apply)

INC-RO-02 swagger sync · codegen · INC-RO-04 map-driven collect / Web Stage B /
CLEAN_DUMP · INC-RO-05 read-only token · Job collect / shop_id / live WB.
