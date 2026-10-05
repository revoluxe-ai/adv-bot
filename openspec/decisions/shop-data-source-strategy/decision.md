# Decision: Стратегия источников и накопления данных магазина

## Status

Accepted

## Context

AI Package и будущие контуры накопления аналитики магазина должны читать
одну и ту же стратегию источников, зерна, режимов и полноты. Иначе ZIP
собирается из «последнего ответа WB», статистика кампании режется на
артикулы, а сбор начинает управлять рекламой.

В `openspec/decisions/` нет Accepted decision, которое фиксирует этот
инвариант. Соседние решения закрывают другие границы и здесь не
переопределяются:

- `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
  (Accepted) задаёт identity семьи `ORDERS_OR_SALES_REPORTS_READ`: только
  чтение ленты заказов и/или продаж поставщика через statistics-api
  (`GET /api/v1/supplier/orders` и/или `GET /api/v1/supplier/sales`). Оно
  запрещает закрывать эту семью воронкой, заказами внутри статистики
  кампании и смежными отчётами. Оно не назначает supplier GET источником
  товарных заказов и продаж контура магазина для AI Package. Цитата
  фиксирует identity operator-семьи, не назначение shop-контура.
- `openspec/decisions/clickhouse-sql-database-qualification/decision.md`
  (Accepted) требует квалификацию `default_db.<object>` в тексте
  ClickHouse SQL рабочего контура. Этот decision SQL не пишет и правило
  квалификации не меняет.
- `openspec/decisions/mode-defaults-policy-ownership/decision.md`
  (Accepted) отдаёт mode-specific defaults декларативным policy overlay
  (`paid_mode_defaults_policy`, `free_mode_defaults_policy`,
  `common_mode_defaults_policy`). Transition helpers только применяют
  overlay и не владеют значениями defaults, включая поля управления вроде
  `bot_active`. Это решение не переносит ownership defaults на сборщиков.

Обнаружение кампаний, которых ещё нет в инвентаре, остаётся у change
`shop-wide-campaign-data-collection`. Формат документа и ZIP остаётся у
`ai-package-v1-contract`. Этот decision их не дублирует.

Наблюдение по репозиторию, которое стратегия не закрепляет как норму:
цикл магазина уже пишет воронку, полную статистику кампаний и кластеры,
но воронка идёт по основному артикулу комплекса, полная статистика
хранится зерном «кампания + дата» без списка товаров внутри дня, кластеры
идут через normquery v0, а заказы и продажи поставщика, остатки и цены
цикл не пишет. Коды типа 8 и 9 не являются определением пары «Авто
(полки) / Поиск (ключи)»: связь пары хранится отдельно. Эти факты
объясняют, зачем нужен инвариант; они не выбирают источник товарных
заказов и продаж и не подтверждают живые лимиты API.

Ранее прочитанные числовые лимиты vendored OpenAPI не подтверждены живым
порталом WB: загрузка портала 2026-09-26 не удалась. Они не являются
Accepted фактом и не становятся нормативным MUST этого decision.

Реализация коллекторов, CSV poller, схемы базы, экспортёра ZIP, создания
и управления кампаниями, JSON ответа AI, preview/apply и Telegram UI в
этот decision не входит.

## Decision

Для подключённого магазина накопление товарных и рекламных dataset и
чтение этого накопления пакетом AI Package подчиняются одному reusable
инварианту.

1. Подключённый магазин MUST собирать данные по всем своим артикулам и
   всем доступным рекламным кампаниям независимо от того, подключены ли
   кампании к управлению WB Sky.
2. Сбор данных и управление кампаниями MUST оставаться разными контурами.
   Сбор MUST NOT менять `bot_active` и MUST NOT выдавать новых прав на
   запись в WB. Сбор MUST NOT назначать mode defaults и MUST NOT вызывать
   paid/free transition, который переводит кампанию в управление ботом.
   Ownership этих defaults остаётся у
   `openspec/decisions/mode-defaults-policy-ownership/decision.md`.
3. Базовая аналитическая единица входа MUST быть `nm_id`: это точка
   входа в аналитику магазина. `nm_id` MUST NOT быть универсальным
   зерном каждого факта. Факты источника MUST сохранять своё зерно.
   Связь `nm_id` и `campaign_id` MUST быть многие-ко-многим. Авто
   (полки) и Поиск (ключи) MUST сохранять отдельные `campaign_id` и
   отдельные исходные ряды. Явно помеченный производный агрегат по
   уникальным `campaign_id` MAY строиться, когда семантика метрики
   верна и двойного счёта нет. Такой агрегат не обязателен. Авто и
   Поиск MUST NOT молча суммироваться как одна кампания и MUST NOT
   сливаться в один неразличимый ряд. Связь пары MUST быть отдельной
   логической связью вне строк статистики. Этот decision MUST NOT
   предписывать для неё новую физическую таблицу. Схема хранения
   остаётся будущим implementation change. Коды 8 и 9 MUST NOT
   считаться определением этой пары.
4. Статистику уровня кампании MUST NOT распределять на `nm_id` без
   подтверждённого источником breakdown.
5. Основной источник AI Package MUST быть уже накопленные PostgreSQL и
   ClickHouse. Формирование ZIP MUST NOT запускать полный сбор магазина
   через WB API.
6. Для каждого dataset MUST быть зафиксированы основной источник,
   допустимый fallback, совместимость зерна и семантики метрики,
   сохранение provenance, приоритет и разбор противоречий,
   гранулярность, доступная история, правило обновления, права,
   зависимость от подписки и `reason_codes`. Fallback MUST NOT молча
   подменять одну метрику другой. Источник товарных заказов и продаж
   магазина остаётся открытым, пока нет evidence.
7. Оперативный сбор, исторический backfill и асинхронные CSV-отчёты
   MUST быть разными режимами. Ограничение API MUST NOT обходиться
   увеличением периода одного запроса. Оперативное окно — то, которое
   выбранный метод реально возвращает. Более длинная история идёт другим
   допустимым для этого dataset режимом либо dataset остаётся неполным:
   явный разрыв с периодом и `reason_codes`. Непроверенные числовые
   потолки vendored OpenAPI MUST NOT записываться как нормативный MUST. После простоя
   пропущенный интервал MUST быть определён. Если оперативный API не
   восстанавливает старые дни, история MUST идти допустимым для этого
   dataset режимом backfill или CSV. Если восстановление невозможно,
   MUST сохраняться явный разрыв с периодом и причиной. Успешный
   следующий оперативный тик MUST NOT делать историю полной.
8. Полнота накопления MUST вестись четырьмя независимыми измерениями.
   Они MUST NOT подменять друг друга:
   - `collection_outcome` — результат попытки получения;
   - `coverage` — полнота покрытия сущностей и периода;
   - `reason_codes` — одна или несколько причин отсутствия или
     неполноты; несколько кодов MAY действовать сразу, ровно один код
     не требуется;
   - `freshness` — насколько накопленные данные актуальны.
   Отсутствие данных, недостаточные права, отсутствие подписки,
   частичный сбор и ошибка источника MUST различаться как
   машинно-читаемые `reason_codes` и MUST NOT схлопываться в один
   пустой успех. `NO_DATA` MUST NOT автоматически означать неполное
   `coverage`. Успешный пустой ответ MUST NOT доказывать полное
   `coverage`. `UNKNOWN` MUST NOT считаться успехом и MUST NOT
   считаться полным `coverage`: неизвестность закрывается fail-closed.
9. Новые фоновые задачи MUST NOT нарушать лимиты WB API и MUST NOT
   вытеснять работающие production collectors.
10. Источник товарных заказов и продаж контура магазина остаётся открытым,
    пока нет evidence. Этот decision MUST NOT назначать supplier GET
    источником этого контура. Это не пожизненный запрет: будущее
    отдельное decision MAY выбрать источник по evidence. Заказы воронки
    и заказы рекламы MUST NOT автоматически заменять товарную ленту.
    Цитата
    `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`
    сохраняет identity operator-семьи `ORDERS_OR_SALES_REPORTS_READ`,
    а не назначение shop-контура. Shop-контур эту identity не назначает.
    Это Accepted decision не ослабляется.

Какой dataset лежит в PostgreSQL, а какой в ClickHouse, и физическая
схема хранения — предмет будущего change базы. Логическая связь пары
Авто и Поиск новую физическую таблицу не задаёт. Когда такой change пишет
ClickHouse SQL, текст запроса MUST квалифицировать `default_db` по
`openspec/decisions/clickhouse-sql-database-qualification/decision.md`.

Процедура обнаружения кампаний вне инвентаря и формат пакета ZIP в этот
инвариант не входят.

## Applies to

- Накопление товарных и рекламных dataset подключённого магазина.
- Чтение этого накопления при формировании AI Package.
- Capabilities этого change: `data-source-selection`,
  `grain-preservation`, `collection-modes`, `coverage-provenance`.
- Будущие changes оперативного сбора, исторического backfill,
  асинхронных CSV, схемы хранения и экспортёра накопленного
  PostgreSQL/ClickHouse — в части источника, зерна, режима и полноты.

Не покрывает placement mode defaults, квалификацию ClickHouse SQL,
identity operator-семьи `ORDERS_OR_SALES_REPORTS_READ`, обнаружение
кампаний вне инвентаря и формат ZIP.

## Allowed

- Читать для пакета уже накопленные PostgreSQL и ClickHouse.
- Оперативно собирать только то окно, которое выбранный метод реально
  отдаёт, и записывать более длинную историю отдельным допустимым
  режимом или явной неполнотой.
- Хранить исходные ряды Авто и Поиска раздельно. Держать связь пары
  отдельной логической связью вне строк статистики, без новой
  физической таблицы.
- Строить явно помеченный производный агрегат по уникальным
  `campaign_id`, когда семантика метрики верна и двойного счёта нет.
  Такой агрегат не обязателен.
- Оставлять источник товарных заказов и продаж магазина невыбранным до
  evidence. Будущее отдельное decision MAY выбрать его по evidence.
- Вести `collection_outcome`, `coverage`, `reason_codes` и `freshness`
  независимо. Несколько `reason_codes` MAY стоять сразу.
- Ставить новые фоновые задачи так, чтобы они не ломали лимиты WB API и
  не вытесняли работающие production collectors.
- В будущем ClickHouse SQL писать с квалификацией `default_db` в тексте
  запроса, не в этом decision.

## Forbidden

- Запускать полный сбор магазина через WB API из формирования ZIP.
- Менять `bot_active`, выдавать новые WB write permissions, назначать
  mode defaults или переводить кампанию в управление ботом из контура
  сбора.
- Сливать Авто и Поиск в один неразличимый ряд, молча суммировать их
  как одну кампанию или считать коды 8 и 9 определением пары.
- Раскладывать статистику уровня кампании на `nm_id` без
  подтверждённого источником breakdown.
- Предписывать новую физическую таблицу под связь пары.
- Считать успешный следующий оперативный тик полной историей после
  простоя.
- Молча подменять fallback одну метрику другой.
- Обходить лимит API увеличением периода одного запроса и подменять
  CSV «тем же запросом на больший период».
- Закреплять непроверенные числовые лимиты vendored OpenAPI как
  обязательное окно сбора.
- Этим decision назначать supplier GET источником товарных заказов и
  продаж магазина. Автоматически заменять товарную ленту заказами
  воронки или заказами рекламы. Ослаблять Accepted identity
  `ORDERS_OR_SALES_REPORTS_READ`.
- Схлопывать отсутствие данных, права, подписку, частичный сбор и
  ошибку источника в один пустой или успешный ответ. Считать `NO_DATA`
  автоматически неполным `coverage`. Считать успешный пустой ответ
  доказательством полного `coverage`. Считать `UNKNOWN` успехом или
  полным `coverage`. Требовать ровно один `reason_code`.
- Вытеснять production collectors новыми фоновыми задачами.
- Повторно описывать обнаружение кампаний вне инвентаря
  (`shop-wide-campaign-data-collection`) или формат пакета
  (`ai-package-v1-contract`).
- Реализовывать в этом change коллекторы, CSV poller, схему базы,
  экспортёр ZIP, создание и управление кампаниями, JSON ответа AI,
  preview/apply и Telegram UI.

## Examples

Хорошо:

- ZIP читает накопленные PostgreSQL и ClickHouse. Если у dataset нет
  истории длиннее окна метода, `coverage` говорит, что история
  неполная, и оперативный запрос не растягивается. После простоя
  пропущенный интервал либо закрыт допустимым backfill или CSV, либо
  записан явным разрывом с периодом и причиной. Успешный следующий
  тик эту историю полной не делает.
- Полная статистика кампании остаётся на зерне кампании, пока источник
  не подтвердил breakdown по `nm_id`. `nm_id` остаётся точкой входа.
  Авто и Поиск сохраняют свои `campaign_id` и исходные ряды. Явно
  помеченный агрегат по уникальным кампаниям допустим, если метрика
  не двоит счёт. Логическая связь пары лежит вне строк статистики;
  новая таблица этим decision не задаётся.
- Пустой успешный ответ не доказывает полное покрытие. `NO_DATA` само
  по себе неполное покрытие не означает. Несколько `reason_codes`
  могут стоять вместе. `UNKNOWN` не читается как успех.

Плохо:

- Сборка ZIP вызывает полный обход WB API магазина.
- Задача аналитики ставит `bot_active` или применяет paid mode overlay,
  чтобы «подключить» кампанию к боту ради сбора.
- Дневной итог кампании делится поровну по артикулам комплекса.
- Авто и Поиск молча сложены в один ряд без подписи агрегата.
- Заказы воронки или поле `orders` полной статистики записываются как
  товарная лента заказов и продаж магазина. Supplier GET назначен
  источником shop-контура этим decision.
- Успешный оперативный тик после простоя объявлен полной историей.
- `UNKNOWN` принят за полный успех, а `NO_DATA` автоматически записан
  как дыра покрытия.
- Лимит «31 день» или «7 дней» из ранее прочитанного vendored OpenAPI
  становится обязательным окном, хотя живой портал его не подтвердил.

## Related specs

- `openspec/specs/data-source-selection/spec.md`
- `openspec/specs/grain-preservation/spec.md`
- `openspec/specs/collection-modes/spec.md`
- `openspec/specs/coverage-provenance/spec.md`
- Не переписываются: `openspec/specs/wb-api-read-only-preflight/spec.md`,
  `openspec/specs/clickhouse-query-database-qualification/spec.md`.

## Related changes

- Accepted via archive: `openspec/changes/archive/2026-09-26-ai-package-data-source-strategy`.
- Граница, не копия: `shop-wide-campaign-data-collection` (кампании вне
  инвентаря), `ai-package-v1-contract` (формат пакета и ZIP).
- Cited Accepted:
  `openspec/decisions/orders-or-sales-reports-read-identity/decision.md`,
  `openspec/decisions/clickhouse-sql-database-qualification/decision.md`,
  `openspec/decisions/mode-defaults-policy-ownership/decision.md`.

## Review checklist

- [x] Existing decisions were searched before proposing implementation.
- [x] Relevant decisions are cited by path.
- [x] New decision proposed because an accepted decision for shop source,
      grain, collection-versus-management, modes, and coverage was missing.
- [x] Ownership and placement match this decision: collection does not own
      mode defaults, WB writes, campaign discovery outside inventory, ZIP
      format, ORDERS family identity, or ClickHouse SQL qualification.
- [x] No forbidden layer performs this decision's responsibility inside
      this change: product code is not edited here.
- [ ] Tests verify behavior without masking placement violations. Этот
      change коллекторы не поставляет; проверка остаётся последующим
      implementation changes.
