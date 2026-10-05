## Context

У этой базы ClickHouse нет версионированного жизненного цикла. В worktree лежат
только ручные SQL-файлы `scripts/clickhouse_migrations/001`–`005`. Отдельного
запускатора и журнала применённых версий нет. Заголовок `005` указывает ручной
вызов `clickhouse-client`; этот вызов не является журналом. Точка входа
`trunc_system_log_in_clickhouse` — потребитель права `TRUNCATE` на системных
логах, не регистратор миграций.

Какой набор версий реально применён на проде, в репозитории не записан.
Наличие файлов и `IF NOT EXISTS` этот факт не устанавливают.

`006` в этом worktree нет. Тестовый DDL
(`tests/support/destructive_ch_reset.py`, база `test_adv_bot_clickhouse`) и
шов `tests/support/rewrite_default_db_ch_client.py` живут в тестовом контуре
и не входят в корпус версий.

Рабочий клиент `app/utils/click_house/client.py` фиксирует базу `default_db`.
Объекты `001`–`004` используют семейство `MergeTree` без `ON CLUSTER`.

`app/db/migrate.py` доказывает сессионный `pg_try_advisory_lock` /
`pg_advisory_unlock` на соединении PostgreSQL. Ключ Alembic —
`MIGRATION_LOCK_ID = 731984123` на `DATABASE_URL`. Зависимости `asyncpg` и
`psycopg2` уже объявлены. Этот control plane использует тот же класс
примитива на своём соединении и своём ключе и не вызывает Alembic.

Проверенные файлы корпуса:

| Версия | Файл | Текст SQL | Класс (планирование) |
| --- | --- | --- | --- |
| 001 | `001_create_incremental_tables.sql` | несколько `CREATE TABLE` / `CREATE MATERIALIZED VIEW` … `IF NOT EXISTS` объектов `default_db.*` | `schema_ddl` |
| 002 | `002_add_event_date_event_id_to_fact_stat_states.sql` | `CREATE TABLE IF NOT EXISTS default_db.fact_stat_states` и затем `ALTER TABLE` … `ADD COLUMN IF NOT EXISTS` | `schema_ddl` |
| 003 | `003_add_buyouts_sum_rub_to_wb_common_stat.sql` | один `ALTER TABLE default_db.wb_common_stat` … `ADD COLUMN IF NOT EXISTS` | `schema_ddl` |
| 004 | `004_create_auto_shelf_bid_increment_tables.sql` | два `CREATE TABLE IF NOT EXISTS default_db.*` | `schema_ddl` |
| 005 | `005_grant_system_log_truncate_to_adv_bot_user.sql` | девять `GRANT TRUNCATE ON system.* TO adv_bot_user`; заголовок: вручную `clickhouse-client` | `privileged_grant` |

ClickHouse не оборачивает файл из нескольких statement в одну транзакцию.
`IF NOT EXISTS` делает повтор statement менее опасным и одновременно не
доказывает, что файл уже целиком исполнен.

## Goals / Non-Goals

**Goals:**

- Безопасно принять уже лежащие `001`–`005` в версионированный жизненный цикл
  ClickHouse этой базы.
- Отделить неизменяемую идентичность корпуса от долговечного журнала
  применённого состояния на цели.
- Дать запускатор: статус, проверка и drift, план без исполнения, осмотр
  только на чтение.
- На изолированной непроизводственной цели реализовать `ensure-ledger`,
  санкционированную сверку и санкционированный apply `001`–`004` под
  сессионным PostgreSQL advisory lock.
- Закрыть частичный сбой и обрыв fail-closed, без файловой транзакции, без
  автоматического downgrade и без продолжения со середины файла.
- Держать исторический applied-state прода явно неизвестным, пока нет
  санкционированной сверки.
- Зафиксировать класс `005` как привилегированный `GRANT` и не исполнять его.
- Сохранить явную квалификацию базы в тексте SQL и слой Alembic.
- Проверить запускатор подставными портом цели и сессией координатора, без
  прод-сокета и без живого сетевого вызова.

**Non-Goals:**

- Версия `006` из другой рабочей копии shop-wide: не копировать и не менять.
- Подключение к проду и исполнение SQL на продовом ClickHouse в этом change.
- Секреты, Kubernetes, выкладка, зашитые учётные данные, живые сетевые вызовы.
- Перенос корпуса в Alembic или изменение поведения Alembic.
- Хранение применённого статуса в PostgreSQL.
- Расширение сбора shop-wide campaign data.
- Изменение paid/free поведения, WB API и runtime бота.
- Подмена тестового session DDL корпусом миграций.
- Автоматический откат уже выполненного statement.
- Политика продолжения `partial` и privileged writer для `005`.
- Исполнение `005`.

## Design Readiness

```text
DESIGN_READINESS
PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY
REASON: none
```

Классификация `005`, журнал на цели и PostgreSQL только как сессионный
advisory lock не являются решением Owner (`owner-contract.md`: отдельных
решений Owner нет). Они разрешены как техническое планирование по фактам
репозитория. Proposed decision остаётся `Proposed`.

`PRODUCT_ACCEPTANCE_REQUIRED: true` — у change есть долговечное состояние
цели и временной жизненный цикл миграции. Lifecycle ниже выведен из
просмотренного контракта Owner, proposal и proposed decision. Повторный
`CONFIRM_LIFECYCLE` не требуется.

## Architecture Decision References

Поиск: `openspec/decisions/index.md`, затем decision-файлы, названные
proposal и proposed decision. Реестр не содержит accepted decision об
ownership жизненного цикла миграций ClickHouse.

- `openspec/decisions/clickhouse-sql-database-qualification/decision.md`
  — **Accepted**. Рабочий ClickHouse SQL MUST квалифицировать объекты рабочей
  БД как `default_db.<object>` в тексте запроса. Этот change сохраняет
  квалификацию в `001`–`004`. `005` квалифицирует `system.<table>` в тексте
  `GRANT`; это не объект `default_db` и не повод переписывать файл.
- `openspec/decisions/alembic-forward-only-head-convergence/decision.md`
  — **Accepted**. Топология Alembic остаётся слоем PostgreSQL. Опубликованные
  ревизии не становятся корпусом ClickHouse и не становятся журналом
  ClickHouse. `alembic.ini` / `alembic_/` MUST NOT получить версии `001`–`005`.
- `openspec/changes/clickhouse-migrations-control-plane/decisions/clickhouse-migration-lifecycle-ownership/decision.md`
  — **Proposed**. Control plane, раздельные права записи, журнал
  `default_db.ch_schema_migration_ledger` на `serverUUID()`, сессионный
  advisory lock отдельного координатора, fail-closed для неизвестной истории
  и частичного прогона. Design следует этому размещению и не повышает статус
  до Accepted.

Accepted decision на этот ownership в `openspec/decisions/` по-прежнему нет.
Пробел закрыт proposed decision этого change, не выбором Owner.

## Ownership & Placement

**Owner layer:** control plane миграций ClickHouse, пакет
`scripts/clickhouse_migration_control_plane/`.

**Allowed layers:**

- чтение корпуса `scripts/clickhouse_migrations/001`–`005`;
- код запускатора, отпечаток корпуса и клиент мутаций изолированной цели
  внутри этого пакета;
- отдельное соединение PostgreSQL только для сессионного advisory lock,
  открытое по явному DSN координатора;
- изолированные unit-тесты с подставными портом цели и сессией координатора,
  без сетевого сокета и без чтения учётных данных приложения.

**Forbidden layers:**

- `app/` runtime, shop-runner, ARQ, `trunc_system_log_in_clickhouse` как
  исполнитель или источник учётных данных;
- вызов `app.db.migrate` и ключ Alembic `731984123`;
- `alembic_/`, `alembic.ini` как журнал или ревизии ClickHouse;
- клиент `app/utils/click_house/` как исполнитель миграций и как источник
  учётных данных;
- тестовый шов `rewrite_default_db_ch_client` как исполнитель миграций;
- Redis, локальный файл и fence ClickHouse как mutex;
- Kubernetes, секреты, выкладка, прод-сокет;
- файл `006` из другой рабочей копии;
- запись журнала применённого состояния в git или в PostgreSQL.

**Rationale:** proposed decision запрещает вешать учёт версий и журнал на
runtime бота и запрещает делать Alembic системой миграций ClickHouse.
Корпус уже лежит в `scripts/clickhouse_migrations`. Журнал обязан жить на
цели `default_db`, потому что git и PostgreSQL не являются фактом применения.
Advisory lock Alembic доказывает примитив, но принадлежит другому слою.
Control plane стоит рядом с корпусом и не входит в DI приложения.

## Decisions

### 1. Два источника истины и отдельный координатор

| WHAT | WHO владеет | WHERE (SoT) | WHO пишет | HOW восстановить |
| --- | --- | --- | --- | --- |
| Корпус версий | control plane читает; байты файлов этот change не меняет | git-файлы `scripts/clickhouse_migrations/001`–`005` | никто в этом change | перечитать файлы; отсутствие ожидаемого файла = корпус неполон, SQL не исполнять |
| Отпечаток идентичности | control plane | SHA-256 сырых байтов плюс класс привилегии в отпечатке пакета | control plane из байтов, без правки SQL | нет отпечатка, нечитаемый отпечаток или несовпадение хэша → `corpus_drift`, SQL не исполнять |
| Применённое состояние цели | control plane | `default_db.ch_schema_migration_ledger` на сервере `serverUUID()` | только control plane, append-only `INSERT`, под удержанным advisory lock | нет журнала, ошибка `serverUUID()`, база сессии не `default_db`, порча чтения → fail-closed, apply и mark-applied запрещены |
| Ограждение писателя | control plane | сессионный PostgreSQL advisory lock на явном DSN координатора; ключ = пространство имён migration-control + цель | control plane на отдельном соединении до мутации и до отпуска после конечного audit или отказа | нет DSN, чужой ключ, `try` вернул ложь, сессия умерла → следующий statement запрещён; `partial` не продолжается |

Журнал в git отклонён: он описывает репозиторий, а не сервер.
Таблица применённого статуса в PostgreSQL отклонена: accepted decision
оставляет Alembic слоем PostgreSQL, и ревизия Alembic не должна стать
журналом ClickHouse. PostgreSQL здесь только координатор.
Redis отклонён: это не долговечный журнал и не авторитетный mutex этого
change. `ALTER UPDATE` строки журнала отклонён: мутация ClickHouse
асинхронна. Журнал — `MergeTree` без `ON CLUSTER`, в том же стиле, что
объекты `001`–`004`, и каждое состояние является новым insert.

Идентификатор цели — строка `serverUUID()`. Если функция недоступна или
возвращает нулевой UUID, запускатор останавливается и не подменяет цель
именем хоста. База сессии MUST быть `default_db`. Иная база, включая
`test_adv_bot_clickhouse`, не является целью этого корпуса.

### 2. Принятие корпуса

Версия = один файл. Граница версии — имя файла с числовым префиксом, не
отдельный statement. Канонический набор этого change — ровно `001`–`005`.

Отпечаток версии = SHA-256 сырых байтов файла, как они лежат на диске, без
нормализации переводов строк и без отбрасывания комментариев.

Отпечаток хранит `id`, `filename`, `sha256`, `privilege_class` в порядке
`id`. Это идентичность принятого корпуса. Он не заменяет байты SQL и не
является applied-state.

Принятие файла в корпус MUST NOT включать исполнение его SQL.

Существующие байты `001`–`005` этот change MUST NOT изменять.

Протокол не кодирует «последняя версия навсегда 005». Файл с иным числовым
префиксом, которого нет в отпечатке этого change, — `unreviewed_version`.
Он блокирует apply. Так следующая проверенная версия сможет войти отдельным
change после ревью. Файл `006` из другой рабочей копии не копируется и не
читается.

### 3. Классы привилегий

Класс выводится из текста SQL на шаге планирования. Это не решение Owner и
не Accepted decision.

- `schema_ddl` — statement `CREATE` / `ALTER` объекта `default_db.<object>`.
  Версии `001`, `002`, `003`, `004`.
- `privileged_grant` — statement `GRANT` на `system.<table>`. Версия `005`.

`005` MUST оставаться привилегированным `GRANT`. Schema-writer MUST NOT
получить его текст и MUST NOT исполнить его. Отдельный privileged writer в
этом change не создаётся и `005` не исполняется.

Schema-writer MAY исполнить `schema_ddl` только когда одновременно есть:
изолированный класс цели, явный конфиг цели, явный DSN координатора,
удержанный advisory lock этой цели, санкционированная базовая линия,
совпавший SHA-256, версия не в `partial` / `applying` и отдельный флаг
санкции apply. Прод-класс цели эти ворота не открывает.

`IF NOT EXISTS` в `001`–`004` MUST NOT читаться как доказательство применения
и MUST NOT закрывать `partial` в `version_applied`.

### 4. Журнал и состояния версии

Форма журнала принадлежит пакету control plane, не
`scripts/clickhouse_migrations` и не Alembic. `ensure-ledger` создаёт только
`default_db.ch_schema_migration_ledger` на изолированной цели под advisory
lock и явной санкцией мутации. Создание не пишет `version_applied` и не
переводит историю в «версии отсутствуют на сервере». После создания без
базовой линии состояние — `history_unresolved`. До создания — `ledger_absent`.

Колонки журнала:

- `target_id` — `serverUUID()`;
- `database` — `default_db`;
- `version_id`;
- `sha256` сырых байтов файла;
- `privilege_class`;
- `event_type`;
- `statement_ordinal`;
- `statement_count`;
- `runner_nonce`;
- `coordinator_lock_identity` — пространство имён, ключ цели и идентификатор
  сессии PostgreSQL, удержавшей lock; это след захвата, не статус в
  PostgreSQL;
- `evidence_sha256`;
- `event_seq`;
- `created_at`.

Движок: `MergeTree`, `ORDER BY (target_id, version_id, event_seq)`.

Текущее состояние версии — event с максимальным `event_seq` для пары
`(target_id, version_id)`.

Состояния, которые видит оператор:

- `ledger_absent` — журнала на цели нет;
- `history_unresolved` — журнал есть, санкционированной базовой линии нет;
- `applying` — записан старт версии, закрывающего event нет;
- `partial` — есть успешный statement, версия не закрыта;
- `applied` — event `version_applied` с тем же SHA-256, что у корпуса;
- `drift` — в журнале другой SHA-256, чем у текущего файла;
- `blocked_privileged_grant` — версия `005`, schema-writer её не берёт.

Event `applied` из-за наличия файла не пишется.

### 5. Неизвестная история, осмотр и базовая линия

Исторический applied-state прода MUST оставаться явно неизвестным, пока нет
отдельной санкции базовой линии. Наличие файлов и `IF NOT EXISTS` MUST NOT
порождать `version_applied`.

Пока состояние цели `ledger_absent` или `history_unresolved`:

- apply MUST отказаться;
- пометка «применено» MUST отказаться;
- догоняющий прогон `001`–`005` MUST NOT выполняться.

`inspect` только читает цель (`system.tables`, `system.columns`,
`SHOW CREATE`) и печатает доказательство. Журнал он не пишет. Координатор
не берёт. В этом change против прода он не запускается. Тест подставляет
готовый ответ чтения.

`reconcile` требует отдельный флаг санкции, SHA-256 доказательства осмотра,
явный конфиг изолированной цели и удержанный advisory lock. Доказательство
MUST быть результатом осмотра, а не списком имён файлов. Версия со статусом
«не определено» не получает `version_applied`. `reconcile` дописывает
базовую линию в журнал и MUST NOT исполнять SQL `001`–`005`. Флаг сверки не
заменяет флаг apply. В этом change против прода команда не запускается.

Ручной `clickhouse-client` из заголовка `005`, точка входа
`trunc_system_log_in_clickhouse` и тестовый DDL MUST NOT становиться этой
записью.

### 6. Частичный DDL, обрыв, идемпотентность

Версии `001`, `002`, `004` и `005` содержат несколько statement. `003` —
один `ALTER`. Граница шага — один statement после отрезания полнострочных
комментариев `--`. В этих пяти файлах нет точки с запятой внутри строкового
литерала. Если разбор встречает такую точку с запятой, `validate` завершается
ошибкой и apply не начинается.

Порядок apply `schema_ddl` под удержанной сессией координатора:

1. event `apply_started` с числом statement, `runner_nonce`, идентичностью
   блокировки, целью, версией, SHA-256 и временем;
2. исполнить statement;
3. event `statement_ok` с порядковым номером;
4. только после успеха всех statement — event `version_applied`.

Обрыв между `apply_started` и `version_applied`, обрыв соединения ClickHouse
или потеря сессии координатора оставляет `applying` или `partial`. Следующий
statement не отправляется. Автоматического продолжения с середины файла нет.
Автоматического downgrade нет. Повторный запуск на `partial` или `applying`
отказывает, пока нет явной политики сверки оператора. Этот change политику
продолжения не определяет и `IF NOT EXISTS` в `version_applied` не превращает.

Повторный apply версии в состоянии `applied` с тем же SHA-256 SQL не
исполняет. Под удержанным lock он MAY дописать audit-event
`skipped_already_applied`. `partial` и `applying` не пропускаются и не
переигрываются.

Успех statement с `IF NOT EXISTS` сам по себе event `version_applied` не
создаёт.

### 7. Один писатель: сессионный advisory lock

Инвариант цели (`serverUUID()`, база `default_db`): не больше одного
санкционированного экземпляра этого запускатора входит в мутацию цели.
Захват атомарный на PostgreSQL и живёт в сессии, не в строке ClickHouse.

Конфиг. Мутирующие команды (`ensure-ledger`, `reconcile`, `apply`) требуют
три независимых входа:

- явный конфиг цели, класс `isolated`, база `default_db`;
- явный DSN координатора control plane;
- отдельный флаг санкции этой команды.

Класс `production` отказывает кодом `blocked_production_target` до захвата и
до statement. Будущий GO оператора этим change не реализуется. Нет DSN —
`blocked_missing_coordinator` до мутации. Реализация MUST NOT читать
`DATABASE_URL`, настройки `app.utils.click_house` и DI приложения.

Ключ. Двухаргументный сессионный lock:

- `namespace_key` — фиксированная константа пространства имён
  migration-control. Она MUST NOT равняться `731984123`.
- `target_key` — знаковый int32 из первых четырёх байтов SHA-256 строки
  UTF-8 `clickhouse-migration-control\n{server_uuid}\ndefault_db`
  (big-endian).

Вызов до первой мутации цели, на соединении, открытом только для этой
сессии:

- по умолчанию `pg_try_advisory_lock(namespace_key, target_key)`; ложь —
  `blocked_lock_contention`, statement цели нет;
- `pg_advisory_lock(namespace_key, target_key)` только если оператор явно
  задал ожидание; это тот же ключ и та же сессия.

Сессия остаётся открытой на каждый statement цели. Перед следующим
statement запускатор проверяет, что соединение живо и lock ещё удерживается.
Потеря — немедленный останов, без следующего statement. Исход журнала, если
`apply_started` уже записан, остаётся `applying` или `partial`.

Отпуск `pg_advisory_unlock(namespace_key, target_key)` на той же сессии
после конечного audit-event (`version_applied`, baseline, созданный журнал
или `skipped_already_applied`) либо после обработки отказа. Обрыв процесса
отпускает lock вместе с сессией PostgreSQL. Новый процесс может взять lock
и всё равно MUST отказать, если версия `partial` или `applying`.

Контракт оператора: все санкционированные запускаторы одной цели используют
один и тот же DSN. Реализация не ищет второй координатор и не сливает два
DSN в один mutex. Ключ Alembic, fence ClickHouse, Redis и локальный файл
этим lock не заменяются.

`status`, `validate`, `plan` и `inspect` координатор не открывают и журнал
не пишут. Ручной `clickhouse-client` запускатором не перехватывается. Это
оговорка оператора. Она не заменяет advisory lock.

### 8. Runner

Пакет: `poetry run python -m scripts.clickhouse_migration_control_plane`.
Обязателен `--help`.

Команды:

- `status` — корпус, классы, SHA-256 и, если цель передана подстановкой,
  состояние журнала. Без цели печать `target_not_attached`. Координатор не
  нужен. Это не запись `applied` и не git-журнал.
- `validate` — отпечаток, класс `005`, квалификация `default_db` в
  `001`–`004`, квалификация `system.` в `005`, разбор statement. Сеть и
  координатор не нужны.
- `plan` — сухой порядок statement и причина остановки (нет цели, нет
  координатора для будущей мутации, неизвестная история, `005`, drift,
  partial, прод-класс). SQL не исполняется. Координатор не берётся.
- `apply` — явный конфиг изолированной цели, явный DSN координатора и флаг
  санкции apply. Без любого из них отказ до statement. При
  `history_unresolved` отказ. Для `005` отказ `blocked_privileged_grant` до
  передачи текста schema-writer. Для `partial` / `applying` отказ. При
  совпавшем `applied` SQL не повторяется. Иначе под lock пишутся
  `apply_started`, `statement_ok`, затем `version_applied`. Пакет MUST NOT
  импортировать `app.utils.click_house` и MUST NOT читать настройки
  подключения приложения.
- `inspect` — только чтение через порт цели. Без цели не открывает сеть.
  Координатор не берётся.
- `reconcile` — свой флаг санкции, хэш доказательства, конфиг цели и DSN.
  Под lock дописывает базовую линию. SQL `001`–`005` не исполняет.
- `ensure-ledger` — свой флаг санкции мутации, конфиг изолированной цели и
  DSN. Под lock создаёт только журнал control plane. Исторические версии не
  помечает применёнными. Fence-таблицу не создаёт.

Код выхода `0`, когда команда сделала ровно свою работу: `validate` при
цельном корпусе; `status` при честном отчёте, включая неизвестную историю;
`plan` при построенном плане; `ensure-ledger`, `reconcile` и `apply` при
пройденных воротах на изолированной подстановке. `corpus_drift`, подмена
класса `005`, отсутствие санкции, отсутствие или чужой координатор,
конкуренция или потеря lock, неизвестная история, partial, прод-класс и
попытка провести `005` — ненулевой выход.

Этот change MUST NOT передавать в порт продовые учётные данные, MUST NOT
открывать продовый сокет и MUST NOT выполнять живой сетевой вызов.
Проверка — подставные порт и сессия. Будущее прод-исполнение — отдельный GO
оператора вне этого change.

### 9. Тестовый DDL, квалификация, запись

`tests/support/destructive_ch_reset.py` создаёт session-таблицы в
`test_adv_bot_clickhouse`. Эти statement MUST NOT попадать в отпечаток
корпуса.

`tests/support/rewrite_default_db_ch_client.py` переписывает `default_db.` →
`test_adv_bot_clickhouse.` только на тестовом шве. Control plane MUST NOT
использовать этот шов. Текст `001`–`004` MUST сохранить `default_db.<object>`.
Текст `005` MUST сохранить `system.<table>`.

Существующий unit-тест, который читает байты `004` и проверяет
`default_db.auto_shelf_bid_intervals` / `default_db.auto_shelf_bid_prev`,
остаётся читателем корпуса.

Путь записи, который проверяют тесты на подстановках:

- preview — вывод `plan`: версии, классы, SHA-256, statement, причина
  остановки; SQL и lock не берутся;
- явное подтверждение — отдельные флаги `ensure-ledger`, сверки и apply;
  плюс конфиг цели и DSN координатора;
- затронутые записи — журнал цели и, для apply, statement `001`–`004` на
  изолированном порту; PostgreSQL получает только advisory lock, без строк
  применённого статуса; Redis и WB не затрагиваются;
- восстановление — обрыв сессии оставляет `partial` / `applying`; отката SQL
  нет; повтор не продолжает файл;
- тесты — парные положительные: санкционированные `ensure-ledger`, сверка и
  apply `001`–`004` под удержанным `pg_try_advisory_lock`; отрицательные:
  нет DSN, ключ Alembic или молчаливый `DATABASE_URL`, конкуренция lock,
  потеря сессии, неизвестная история, `partial`, `005`, drift контрольной
  суммы, прод-класс без отдельного GO. Пакет не импортирует клиент
  приложения и Alembic. Тестовый DDL отсутствует в отпечатке. Живого сокета
  нет.

Побочных эффектов на продовом ClickHouse, Redis, PostgreSQL приложения и
WB API этот change не производит.

Производительность: пять небольших файлов, один проход SHA-256 на
`validate` и одна сессия координатора на мутацию. Отдельный бюджет не нужен.

### 10. Semantic write target

Высокорисковая мутация схемы имеет несколько правдоподобных адаптеров в
репозитории. Выбор зафиксирован фактами репозитория и proposed decision, не
новым решением Owner.

```text
SEMANTIC_WRITE_TARGET_STATUS: RESOLVED
BUSINESS_TERM: версионированная миграция схемы ClickHouse этой базы
TARGET_ENTITY_OR_LEG: ClickHouse serverUUID(); database default_db; ledger default_db.ch_schema_migration_ledger; mutating commands only on target_class=isolated
ALLOWED_ADAPTERS: isolated migration target port of scripts.clickhouse_migration_control_plane (ClickHouse session for ensure-ledger, ledger append, and schema_ddl 001-004); PostgreSQL session advisory-lock coordinator (dedicated connection, pg_try_advisory_lock/pg_advisory_lock, namespace_key distinct from 731984123, target_key of serverUUID+default_db, explicit coordinator DSN) for ensure-ledger, reconcile, and apply
FORBIDDEN_ADAPTERS: app.utils.click_house.get_clickhouse_client and application DI as executor or credential source; app.db.migrate and Alembic lock 731984123; alembic_/ and alembic.ini as ClickHouse migration state; Redis; local file lock; append-only ch_schema_migration_fence or ClickHouse nonce as mutex; silent fallback to DATABASE_URL; schema-writer for 005; git JSON as applied-state ledger; PostgreSQL table as applied-state ledger; test database test_adv_bot_clickhouse as corpus target; tests.support.rewrite_default_db_ch_client; runtime bot, shop-runner, and ARQ; production target without a future separate operator GO
TARGET_EVIDENCE: app/utils/click_house/client.py database=default_db; app/db/migrate.py session pg_try_advisory_lock(731984123) proves the primitive and is Alembic-only; pyproject.toml depends on asyncpg and psycopg2; accepted openspec/decisions/clickhouse-sql-database-qualification/decision.md; accepted openspec/decisions/alembic-forward-only-head-convergence/decision.md; corpus 001-004 has no ON CLUSTER; owner-contract.md forbids treating files as applied state, forbids Alembic as the ClickHouse migration system, and forbids production apply in this change; 005 is GRANT on system.*
OWNER_DECISION_SOURCE: openspec/changes/clickhouse-migrations-control-plane/owner-contract.md (no separate Owner decisions; SQL names the database; 005 is not ordinary schema; do not apply to production) plus proposed decision clickhouse-migration-lifecycle-ownership; coordinator placement is technical planning, not a new Owner decision
REQUIRED_PAIRED_TESTS: positive — authorized isolated apply of schema_ddl 001-004, ensure-ledger, and reconcile each run under a held PostgreSQL advisory lock and leave applied state only in the ClickHouse ledger; negative — missing coordinator, Alembic key or DATABASE_URL fallback, lock contention, lock loss, history_unresolved, partial rerun, 005 through the schema writer, checksum drift, and production target without a separate GO all refuse before the forbidden mutation
```

## Lifecycle

```text
LIFECYCLE_STATUS: DERIVED
PRODUCT_ACCEPTANCE_REQUIRED: true
```

L1. Вход: корпус `001`–`005` уже лежит как ручной SQL, журнала на цели нет,
прод-набор неизвестен.
SOURCE: `owner-contract.md`; repository fact `scripts/clickhouse_migrations/`.

L2. Control plane принимает файлы в корпус: фиксирует id, класс и SHA-256,
байты SQL не меняет и не исполняет. `006` в отпечаток не входит.
SOURCE: `proposal.md` (безопасно принять `001`–`005`; SQL MUST NOT
переписываться; `006` MUST NOT копироваться).

L3. `005` учитывается как `privileged_grant`. Schema-writer его не получает.
Change не проводит GRANT.
SOURCE: `owner-contract.md`; `proposal.md` MUST / MUST NOT для `005`.

L4. Цель без санкционированной базовой линии остаётся `history_unresolved`
даже после `ensure-ledger`. Apply и пометка «применено» блокированы. Осмотр
только читает и координатор не берёт.
SOURCE: `proposal.md` (статус MUST оставаться неизвестным; неизвестность
MUST блокировать слепое догоняние и mark-applied).

L5. На изолированной цели явные конфиг, DSN координатора и санкция открывают
мутацию под сессионным advisory lock: журнал, затем сверка без SQL миграций,
затем apply `001`–`004` событиями `apply_started`, `statement_ok`,
`version_applied`. Обрыв оставляет `partial`. Автопродолжения и downgrade
нет. Прод-класс отказывает.
SOURCE: `proposal.md` (изолированные мутации MUST быть реализованы; прод
MUST NOT; один писатель MUST быть сессионным advisory lock); proposed
decision.

L6. Рестарт процесса читает журнал цели, а не память и не PostgreSQL.
`partial` и `history_unresolved` после рестарта остаются запретом на слепой
прогон, даже если новый процесс снова взял lock.
SOURCE: `owner-contract.md`; proposed decision (fail-closed).

L7. Этот change проверяет L2–L6 на подставной изолированной цели и подставной
сессии координатора и не открывает прод. Расширение ClickHouse в сборе
shop-wide campaign data не начинается.
SOURCE: `owner-contract.md`; `proposal.md` (прод-подключение MUST NOT;
готовность MUST NOT требовать секретов, Kubernetes или выкладки).

Развилка продукта после L1 в контракте Owner не оставлена. Семантика
«неизвестно / не проводить `005` / не переписывать SQL / не трогать прод в
этом change» сохранена. Координатор — техническое закрытие блока design, не
новый выбор Owner.

## Normative preservation

| Источник | Обязательство | В этом design |
| --- | --- | --- |
| proposal | идентичность корпуса и applied-state MUST быть разными фактами; журнал MUST быть долговечным и привязанным к цели | отпечаток SHA-256 отдельно от `default_db.ch_schema_migration_ledger`; PostgreSQL статус не хранит |
| proposal | файлы и `IF NOT EXISTS` MUST NOT быть записью «применено» | эти факты не пишут `version_applied` |
| proposal | исторический статус MUST оставаться неизвестным до санкционированной сверки | `history_unresolved` до `reconcile` |
| proposal | неизвестная история MUST блокировать слепое догоняние и mark-applied | apply без сверки отказывает |
| proposal | запускатор MUST включать status, validate/drift и plan без исполнения | команды §8; plan координатор не берёт |
| proposal | один писатель MUST быть сессионным advisory lock явного координатора | §7 |
| proposal | нет DSN MUST отказывать до мутации; молчаливый fallback MUST NOT | `blocked_missing_coordinator`; запрет `DATABASE_URL` / DI / Redis / файла / nonce |
| proposal | изолированные ensure-ledger, сверка и apply `001`–`004` MUST быть реализованы | §5–§8 |
| proposal | прод MUST NOT исполняться без будущего GO; учётные данные MUST NOT зашиваться; живой сети MUST NOT быть | `blocked_production_target`; тесты на подстановках |
| proposal | многоstatementный файл MUST быть неатомарным; partial и crash MUST fail-closed | пошаговые event §6 |
| proposal | повтор на partial MUST отказать до явной политики сверки | §6; политика продолжения вне change |
| proposal | запускатор MUST NOT считать файл транзакцией и MUST NOT обещать автоматический downgrade | отказ продолжения и отсутствие down SQL |
| proposal | осмотр и базовая линия MUST иметь отдельные санкции; сверка MUST NOT исполнять SQL миграций | `inspect` без lock; `reconcile` со своим флагом |
| proposal | `005` MUST оставаться привилегированным GRANT; schema-writer MUST NOT проводить его | отказ до вызова writer |
| proposal | классификация `005` не является решением Owner | класс помечен как планирование; decision остаётся Proposed |
| proposal | SQL MUST явно указывать базу | `default_db.<object>` и `system.<table>` сохраняются |
| proposal | Alembic MUST NOT становиться системой миграций ClickHouse | корпус и журнал не переносятся; lock `731984123` не используется |
| proposal | тестовый DDL MUST NOT быть вторым корпусом | `test_adv_bot_clickhouse` вне отпечатка |
| proposal | существующий SQL MUST NOT переписываться | байты `001`–`005` не меняются |
| proposal | `006` MUST NOT копироваться и MUST NOT изменяться | `unreviewed_version` блокирует apply |
| proposal | расширение shop-wide MUST NOT начинаться, пока система не в порядке | расширение вне scope |
| proposal | готовность MUST NOT подтверждаться продом и MUST NOT требовать секретов, Kubernetes, выкладки | готовность = пакет и изолированные подстановки |
| proposed decision | schema-writer MAY исполнять только `001`–`004` на isolated под lock | §3 и §7 |
| proposed decision | schema-writer MUST NOT исполнять `005` | сохранено |
| proposed decision | неизвестность MUST NOT закрываться догоняющим прогоном | сохранено |
| owner-contract | прод не применять; файлы не есть applied-state; Alembic не система миграций ClickHouse | сохранено |

Прежний технический `MUST NOT` на любой DDL снят в proposal этого же
update, потому что координатор теперь задан. Design повторяет новый proposal:
изолированные мутации `MUST`, прод и `005` остаются `MUST NOT`. Ослабления
`MUST` → `MAY` для этих запретов нет.

## Risks / Trade-offs

- [Оператор примет `history_unresolved` за знание о проде] → status печатает
  это состояние явно; `version_applied` без базовой линии не пишется.
- [Детектор nonce или ключ Alembic принят за mutex этой цели] → разрешён
  только двухаргументный ключ пространства имён migration-control на явном
  DSN.
- [Два запускатора настроены на разные DSN] → это нарушение контракта
  оператора; реализация не объявляет их одним mutex и не подставляет DSN
  сама.
- [Частично исполненный исторический файл останется невидимым до осмотра] →
  осмотр не имеет права сам пометить версию применённой; apply без сверки
  отказывает.
- [`IF NOT EXISTS` создаёт ощущение безопасного повтора] → повтор закрытой
  версии не шлёт SQL; повтор `partial` запрещён и не пишет `version_applied`.
- [Сессия координатора умерла после успешного statement] → следующий
  statement не уходит; версия остаётся незакрытой.
- [Комментарий в `001` про пересоздание MV с `POPULATE`] → control plane не
  исполняет комментарии и не пересоздаёт объекты.
- [Пустой журнал примут за доказательство, что `001`–`005` не применялись
  исторически] → `history_unresolved` значит «не установлено», а не «точно
  отсутствует на сервере».
- [Proposed decision позже не промотируют в Accepted] → до archive размещение
  действует как proposed план этого change, не как постоянный registry.

## Migration Plan

Прод-данных этот change не меняет. Выкладка не нужна. Прод-сокет не
открывается. Живого сетевого вызова нет.

1. Пакет control plane реализует чтение корпуса и мутации изолированной цели
   по §7–§8. Tasks этим update не создаются.
2. Проверить изолированными тестами на подставных порте ClickHouse и сессии
   PostgreSQL, без сокета и без учётных данных приложения.
3. Откат кода — удалить пакет. Файлы `001`–`005` не восстанавливать: change
   их не меняет. Если подстановочный прогон создал журнал, прод-таблицы он
   не касается. Автоматического downgrade нет.

Готовность change MUST NOT подтверждаться применением миграций на прод.

## Open Questions

Нет. Идентичность цели, журнал, классы, координатор, восстановление после
потери lock и запрет прода заданы. Политика продолжения `partial` и
прод-GO намеренно вне этого change, а не открытый выбор реализации.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
