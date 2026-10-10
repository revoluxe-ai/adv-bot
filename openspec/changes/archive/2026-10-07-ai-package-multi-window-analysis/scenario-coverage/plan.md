# Scenario Coverage Plan

CHANGE_ID: ai-package-multi-window-analysis
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-56cb1ebe559693c3
LIFECYCLE_STATUS: DERIVED

Required-evidence planning only. Does not claim tests exist, were executed, or passed.

## Lifecycle coverage

LIFECYCLE_COVERAGE (Derived Lifecycle L1–L7 from design.md):

- L1 → S02, S03, S24 — номинальная граница пакета отдельно от полноты источника; год не равен 365 дням
- L2 → S01, S04 — запрошенный период, окно и история; произвольный период не пресет
- L3 → S18 — чтение фактов на диапазоне окон
- L4 → S05, S07, S15 — агрегат без копии сырья и без слияния ног
- L5 → S06, S13, S21, S24, S25 — частичное покрытие, честный разрыв, отказ полного статуса по границе пакета
- L6 → S12, S13 — статус сопоставимости
- L7 → S08, S09, S10, S11, S14, S16, S17, S19, S20, S22, S23, S25, S26 — контракт, инструкция, охват пакета, ключевой артикул, отказ экономик, транспорт

Steady-state reconcile: not_applicable. Это снимок чтения на один экспорт, не контур записи состояния.

OPEN_QUESTIONS: none blocking plan ready.

## Owner acceptance mapping

| AT | Scenarios | Смысл |
|---|---|---|
| AT-01 | S02, S03, S24 | Номинальные границы и отказ считать границу пакета полнотой |
| AT-02 | S03 | Календарный год |
| AT-03 | S05 | Нет размножения сырья; агрегаты горизонтов |
| AT-04 | S01 | Окно против истории |
| AT-05 | S06 | Пропуск, ноль, пусто, разрыв |
| AT-06 | S07 | Auto и Search |
| AT-07 | S08, S09 | Прямая и связанная область |
| AT-08 | S10, S21, S25 | DRR магазина требует весь расход и всю выручку |
| AT-09 | S12, S13 | Знаменатель и несопоставимость |
| AT-10 | S19, S22 | Версии и целостность контракта |
| AT-11 | S15, S16 | Порядок и один доменный результат |
| AT-12 | S18, S20 | Диапазон чтения и один кодировщик |
| AT-13 | S11, S14, S23 | Фиксированный CPO и запреты инструкции |

Короткий и длинный реальный локальный экспорт — FINAL_ACCEPTANCE после реализации, не утверждается этим планом.

## SCENARIO_COVERAGE_PLAN

SCHEMA_VERSION: 1
CHANGE_ID: ai-package-multi-window-analysis
SOURCE_SPEC_SHA: a6e98820b58876f2b59727a743867866c309af5c578266e8e2af85abe17c35eb
PLAN_STATUS: ready

SCENARIOS:

- SCENARIO_ID: S01
  GIVEN_WHEN_THEN: история ключей длиннее 7-дневного окна и не обрезается
  PRODUCTION_ENTRYPOINT: доменный расчёт окон полного пакета одного магазина
  CAUSAL_PATH: водяной знак → окна → границы истории семейства
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit на границах; CONTRACT_CASES отдельность полей
  REALITY_CONSTRAINTS: без WB
  MOCKING_CONSTRAINTS: факты дней подставляются, формулы не подменяются

- SCENARIO_ID: S02
  GIVEN_WHEN_THEN: окно 1 дня исключает дату водяного знака
  PRODUCTION_ENTRYPOINT: каталог окон
  CAUSAL_PATH: generated_at → package_cutoff_date, не полнота источника
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: без часовой таблицы как нормы
  MOCKING_CONSTRAINTS: фиксированный водяной знак

- SCENARIO_ID: S03
  GIVEN_WHEN_THEN: предыдущий календарный год не равен 365 дням
  PRODUCTION_ENTRYPOINT: каталог окон
  CAUSAL_PATH: якорь 15 марта → две пары границ
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: UTC календарь
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S04
  GIVEN_WHEN_THEN: произвольный период не пресет и частичен, если включает дату пакета
  PRODUCTION_ENTRYPOINT: каталог окон
  CAUSAL_PATH: входные даты → requested_custom
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S05
  GIVEN_WHEN_THEN: сырая строка одна, агрегаты окон разные
  PRODUCTION_ENTRYPOINT: сборка витрин
  CAUSAL_PATH: дневные факты → окна
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit счёта строк
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: маленький набор дней

- SCENARIO_ID: S06
  GIVEN_WHEN_THEN: разрыв выручки не даёт нулевой DRR магазина
  PRODUCTION_ENTRYPOINT: окно магазина
  CAUSAL_PATH: GAP семейства → невычислимая метрика
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: каталог разрывов как вход

- SCENARIO_ID: S07
  GIVEN_WHEN_THEN: Auto и Search — разные строки окон
  PRODUCTION_ENTRYPOINT: витрина ног
  CAUSAL_PATH: два adv_id → две идентичности
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: пара идентификаторов

- SCENARIO_ID: S08
  GIVEN_WHEN_THEN: заказы кампании не называются прямой атрибуцией
  PRODUCTION_ENTRYPOINT: окно ноги
  CAUSAL_PATH: статистика кампании без фактов атрибуции
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет фактов атрибуции

- SCENARIO_ID: S09
  GIVEN_WHEN_THEN: связанная метрика не подменяется прямой
  PRODUCTION_ENTRYPOINT: окно ноги
  CAUSAL_PATH: запрос связанной области при только прямой доказанности
  REQUIRED_EVIDENCE: CONTRACT_CASES отрицательный
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S10
  GIVEN_WHEN_THEN: DRR магазина невычислим при разрыве продаж
  PRODUCTION_ENTRYPOINT: окно магазина
  CAUSAL_PATH: GAP продаж → отказ метрики
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S11
  GIVEN_WHEN_THEN: фиксированный CPO не переписывается
  PRODUCTION_ENTRYPOINT: сборка пакета
  CAUSAL_PATH: чтение настроек без записи
  REQUIRED_EVIDENCE: CONTRACT_CASES отсутствия write
  REALITY_CONSTRAINTS: без WB
  MOCKING_CONSTRAINTS: шпион записи обязан быть нулевым

- SCENARIO_ID: S12
  GIVEN_WHEN_THEN: нулевой знаменатель делает сравнение несопоставимым
  PRODUCTION_ENTRYPOINT: сравнения
  CAUSAL_PATH: наблюдаемый ноль заказов → статус
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S13
  GIVEN_WHEN_THEN: частичное длинное окно даёт частичное сравнение
  PRODUCTION_ENTRYPOINT: сравнения
  CAUSAL_PATH: observed < requested
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S14
  GIVEN_WHEN_THEN: инструкция запрещает ноль вместо разрыва
  PRODUCTION_ENTRYPOINT: документ инструкции
  CAUSAL_PATH: выпуск пакета → текст запретов
  REQUIRED_EVIDENCE: CONTRACT_CASES на обязательные запреты
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S15
  GIVEN_WHEN_THEN: повторный расчёт сохраняет порядок
  PRODUCTION_ENTRYPOINT: витрины
  CAUSAL_PATH: те же факты дважды
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S16
  GIVEN_WHEN_THEN: два транспорта не меняют метрики окна
  PRODUCTION_ENTRYPOINT: доменный результат
  CAUSAL_PATH: один результат → два кодирования
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: MCP код не требуется
  MOCKING_CONSTRAINTS: второй транспорт — тот же объект, не новая формула

- SCENARIO_ID: S17
  GIVEN_WHEN_THEN: манифест ссылается на контракт анализа
  PRODUCTION_ENTRYPOINT: полный пакет
  CAUSAL_PATH: доменные payload → манифест
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: без живого WB
  MOCKING_CONSTRAINTS: фикстура фактов

- SCENARIO_ID: S18
  GIVEN_WHEN_THEN: узкий период вызывающей стороны не режет окно 30 дней
  PRODUCTION_ENTRYPOINT: чтение фактов анализа
  CAUSAL_PATH: период карточек отдельно от диапазона окон
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit границ запроса
  REALITY_CONSTRAINTS: SQL только в квалификационном тесте текста, без прод-БД
  MOCKING_CONSTRAINTS: ответ источника задан

- SCENARIO_ID: S19
  GIVEN_WHEN_THEN: пакет с анализом не остаётся схемой 1.0.0
  PRODUCTION_ENTRYPOINT: манифест
  CAUSAL_PATH: наличие слоя → версия
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S20
  GIVEN_WHEN_THEN: кодировщик не создаёт вторую копию ключевых окон
  PRODUCTION_ENTRYPOINT: сборка ZIP
  CAUSAL_PATH: уже готовые payload → архив
  REQUIRED_EVIDENCE: CONTRACT_CASES списка имён
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S21
  GIVEN_WHEN_THEN: окна не закрывают разрыв DRR магазина
  PRODUCTION_ENTRYPOINT: каталог разрывов
  CAUSAL_PATH: анализ добавлен → статус семейства
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S22
  GIVEN_WHEN_THEN: порча контракта ломает проверку
  PRODUCTION_ENTRYPOINT: валидатор пакета
  CAUSAL_PATH: хеш манифеста
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S23
  GIVEN_WHEN_THEN: экономические метрики без источника не число и не ноль
  PRODUCTION_ENTRYPOINT: валидатор и витрина
  CAUSAL_PATH: отсутствие атрибуции и выручки
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет

- SCENARIO_ID: S24
  GIVEN_WHEN_THEN: граница пакета 2026-10-05 не делает кампанийный 1d полным, если источник полон только по 2026-09-25
  PRODUCTION_ENTRYPOINT: покрытие окна ноги
  CAUSAL_PATH: package_cutoff_date отдельно от source_complete_through
  REQUIRED_EVIDENCE: SCENARIO_SEAM unit
  REALITY_CONSTRAINTS: часовой пояс WB не выдумывается
  MOCKING_CONSTRAINTS: доказанная полнота источника задана фикстурой

- SCENARIO_ID: S25
  GIVEN_WHEN_THEN: сумма ног пакета не называется расходом всего магазина и не входит в DRR магазина
  PRODUCTION_ENTRYPOINT: агрегат охвата пакета
  CAUSAL_PATH: PACKAGE_CAMPAIGN_SCOPE без полного охвата кампаний магазина
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет доказательства shop-wide coverage

- SCENARIO_ID: S26
  GIVEN_WHEN_THEN: артикул ключевой истории не изображает всю экономику товара
  PRODUCTION_ENTRYPOINT: витрина ключевого артикула
  CAUSAL_PATH: KEYWORD_PERFORMANCE_PRODUCT_SCOPE
  REQUIRED_EVIDENCE: CONTRACT_CASES
  REALITY_CONSTRAINTS: нет
  MOCKING_CONSTRAINTS: нет фактов всех продаж артикула

UNRESOLVED_GAPS: none

GENERATED_FROM:
- design.md content_hash 1da7495d752fc908dca5f905ed83a202f4d8089da45f08e448e51c1375b0146c
- owner-contract.md content_hash e3be5e18ff8169dc83dfe7c7f3657d2ef931de194470d6886c90a87a77b23afd
- spec hashes listed in plan.receipt.json INPUTS.SPEC_REVISION
