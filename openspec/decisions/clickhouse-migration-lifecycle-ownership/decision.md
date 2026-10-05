# Decision: Ownership жизненного цикла миграций ClickHouse

## Status

Accepted

Решение принято при archive change `clickhouse-migrations-control-plane`
после `/opsx-verify mode=archive` → `✅ GO` и Owner `GO`. Оно фиксирует
reusable ownership, write-path и recovery-инварианты, подтверждённые
repository evidence, owner-contract и принятой реализацией.

## Context

У этой базы ClickHouse нет версионированного жизненного цикла. В worktree
есть только ручные файлы `scripts/clickhouse_migrations/001`–`005`. Отдельного
запускатора и журнала применённых версий в репозитории нет. Какой набор
применён на проде, неизвестен. Имя файла и `IF NOT EXISTS` не являются этим
статусом.

`005_grant_system_log_truncate_to_adv_bot_user.sql` — `GRANT TRUNCATE` на
`system.*` для `adv_bot_user`. Заголовок файла говорит, что его вызывают
вручную через clickhouse-client. Это не DDL схемы `default_db`.

`006` в этом worktree отсутствует.

Рабочий клиент приложения
(`app/utils/click_house/client.py`) подключается к базе `default_db`.
Файлы `001`–`004` создают объекты `ENGINE = MergeTree()` и родственные
движки без `ON CLUSTER`. Тестовый контур использует отдельную базу
`test_adv_bot_clickhouse` и не является корпусом миграций.

Зависимости `asyncpg` и `psycopg2` уже есть в проекте.
`app/db/migrate.py` берёт сессионный `pg_try_advisory_lock` с ключом
`MIGRATION_LOCK_ID = 731984123` и отпускает его через `pg_advisory_unlock`
на соединении Alembic к `DATABASE_URL`. Это доказанный в репозитории
примитив координации. Он координирует Job Alembic и не является журналом
ClickHouse.

Lookup accepted decisions (context-first: `openspec/decisions/index.md`, затем
два названных decision-файла; fallback по ownership миграций ClickHouse —
пусто):

- `openspec/decisions/clickhouse-sql-database-qualification/decision.md`
  (Accepted) требует `default_db.<object>` в тексте рабочего CH SQL. Он не
  назначает владельца жизненного цикла миграций и не задаёт журнал
  применённых версий.
- `openspec/decisions/alembic-forward-only-head-convergence/decision.md`
  (Accepted) держит топологию Alembic в своём слое. `alembic.ini` не
  ссылается на `clickhouse_migrations`.

Architecture Decision Missing до этого артефакта: ownership, write authority
и recovery жизненного цикла миграций ClickHouse. Координатор одного писателя
разрешён здесь как техническое размещение, не как новое решение Owner.

## Decision

Жизненный цикл миграций ClickHouse этой базы принадлежит отдельному
control plane, не runtime бота и не Alembic.

Два факта MUST оставаться раздельными:

1. Идентичность корпуса. Канонические версии — неизменяемые файлы
   `scripts/clickhouse_migrations` в этом репозитории. Отпечаток версии —
   SHA-256 сырых байтов файла. Отпечаток описывает, какой SQL принят в
   систему. Он не говорит, что цель его исполнила.
2. Применённое состояние цели. Его источник истины — append-only журнал на
   том ClickHouse, к которому относится применение:
   `default_db.ch_schema_migration_ledger`. Идентификатор цели —
   `serverUUID()` этого сервера. База сессии MUST быть `default_db`.
   Текущее состояние версии — последний event журнала, не файл в git и не
   строка `applied_state` в репозитории. PostgreSQL применённый статус не
   хранит.

Журнал в git, таблица PostgreSQL под ревизией Alembic и ключ Redis эту роль
не получают. Git не привязан к серверу. Alembic по accepted decision остаётся
слоем PostgreSQL. Redis и runtime бота не являются владельцем миграций.
Обновление строки через мутацию ClickHouse не используется: мутации
асинхронны, поэтому переход состояния — новый `INSERT` в тот же журнал.

Ограждение одного писателя — не журнал и не append-only таблица ClickHouse.
Инвариант: среди всех экземпляров этого запускатора для одной и той же цели
(`serverUUID()` и база `default_db`) не больше одного санкционированного
процесса может начать или продолжить мутацию цели. Захват — сессионный
PostgreSQL advisory lock на отдельном соединении control plane.

Контракт оператора: каждый санкционированный запускатор одной цели MUST
получить один и тот же явный DSN координатора. Реализация MUST NOT
подставлять `DATABASE_URL`, DI приложения, Redis, локальный файл или nonce
ClickHouse. Нет DSN — отказ до любой мутации цели. Команды только на чтение
координатор не открывают.

Ключ блокировки MUST детерминированно связывать идентичность цели
(`serverUUID()` + `default_db`) с отдельным пространством имён
migration-control. Это пространство MUST NOT совпадать с ключом Alembic
`731984123`. Запускатор MUST NOT вызывать `app.db.migrate`. Захват
`pg_try_advisory_lock` или `pg_advisory_lock` берётся до
`ensure-ledger`, сверки и apply и держится на живой сессии через каждую
мутацию цели. Потеря сессии или блокировки запрещает следующий statement.
Исход остаётся fail-closed или `partial` и требует осмотра или сверки.
Автопродолжения нет. Отпуск — после конечного audit-event или обработки
отказа.

Соседний append-only объект `default_db.ch_schema_migration_fence` и чтение
«последнего nonce» таким захватом не являются. Два писателя могут каждый
увидеть только свой nonce и оба отправить DDL. Наблюдение конфликта не
является mutex. TTL-аренда без живой сессии координатора для
нетранзакционного DDL тоже не является этим захватом.

`k8s/migrations/sql/001_migration_control.sql` (`release_lease` /
`FOR UPDATE`) координирует выкладку PostgreSQL, не DDL ClickHouse, и этим
координатором не становится.

Control plane разделяет права записи. Их нельзя схлопывать в один «прогон
миграций»:

1. Учёт корпуса. Можно зарегистрировать уже лежащие `001`–`005` как
   канонический набор версий, не исполняя их и не переписывая байты файлов.
2. Запись журнала цели. Писать event может только control plane на
   идентифицированной цели под удержанной блокировкой координатора. Имя
   файла и `IF NOT EXISTS` MUST NOT порождать event `version_applied`.
   Пока нет санкционированной базовой линии, цель остаётся
   `history_unresolved`.
3. Исполнение schema SQL. Обычный schema-writer MAY исполнять только
   `schema_ddl` `001`–`004` на изолированной непроизводственной цели, когда
   есть явный конфиг цели, явный DSN координатора, удержанный advisory lock
   и отдельный флаг санкции оператора. Прод-цель MUST отказать без будущего
   отдельного GO. Этот change прод-сокет не открывает и учётные данные не
   зашивает.
4. Создание журнала. `ensure-ledger` — мутация цели. Она допустима только
   под тем же захватом и явной санкцией на изолированной цели. Она создаёт
   только журнал control plane и MUST NOT помечать исторические версии
   применёнными.
5. Сверка базовой линии. Пишет журнал по доказательству осмотра и MUST NOT
   исполнять SQL `001`–`005`.
6. Исполнение `005`. Это отдельный privileged-GRANT writer. Schema-writer
   MUST NOT исполнять `005`. Этот change privileged-GRANT writer не
   подключает и `005` не исполняет. Принятие файла в корпус MUST NOT
   включать его проведение.

Неизвестный исторический applied-state восстанавливается fail-closed:

- MUST NOT помечать версии применёнными из-за наличия файлов или
  `IF NOT EXISTS`;
- MUST NOT запускать догоняющее применение `001`–`005`, чтобы «закрыть»
  неизвестность;
- MUST NOT переписывать `001`–`005`, чтобы подогнать историю;
- осмотр только на чтение MAY собирать доказательство и MUST NOT писать
  журнал и MUST NOT брать координатор;
- запись базовой линии требует отдельной санкции, доказательства осмотра и
  удержанного advisory lock;
- частичный прогон и обрыв оставляют версию незакрытой. Автоматического
  отката и автоматического продолжения нет. Повтор, пока состояние
  `partial` или `applying`, отказывает, пока нет явной политики сверки
  оператора. Этот change такую политику продолжения не задаёт.

Готовность этого change MUST NOT доказываться подключением к проду,
записью в продовом ClickHouse, Kubernetes, секретами, выкладкой или живым
сетевым вызовом. Изолированная мутация проверяется подставными портом цели
и сессией координатора.

DDL журнала принадлежит пакету control plane. Он не входит в корпус
`001`–`005` и не является версией `006`. Создание пустого журнала не
помечает `001`–`005` применёнными.

Это правило слоя. Текст CLI и разбор statement остаются в design и не меняют
ownership выше.

## Applies to

- Capability `clickhouse-migration-lifecycle`.
- Корпус `scripts/clickhouse_migrations/001`–`005` этой базы.
- Журнал `default_db.ch_schema_migration_ledger` на цели с данным
  `serverUUID()`.
- Сессионный PostgreSQL advisory lock отдельного координатора control plane
  для мутаций той же цели. Append-only fence ClickHouse им не является.
  Alembic lock им не является.
- Любой runner, команда apply, `ensure-ledger` и сверка базовой линии для
  ClickHouse этой базы.
- Граница, после которой допустим рост ClickHouse в сборе shop-wide campaign
  data: только когда этот жизненный цикл приведён в порядок по контракту.

## Allowed

- Держать канонические версии в `scripts/clickhouse_migrations` этого
  репозитория и регистрировать `001`–`005` без исполнения и без смены байтов.
- Хранить применённое состояние только в целевом append-only журнале
  `default_db` на сервере `serverUUID()`.
- Координировать мутации сессионным `pg_try_advisory_lock` /
  `pg_advisory_lock` на явном DSN control plane, с ключом пространства имён
  migration-control и детерминированным ключом `serverUUID()` + `default_db`.
- На изолированной непроизводственной цели под этим захватом создавать
  журнал, писать санкционированную базовую линию и применять `schema_ddl`
  `001`–`004`.
- Реализовать чтение корпуса, статус, проверку, осмотр и план без
  координатора и без отправки DDL.
- Оставлять `001`–`004` с явной квалификацией `default_db.<object>` в тексте
  SQL, как требует accepted decision о квалификации.
- Оставлять `005` привилегированным `GRANT` на `system.*` вне schema-writer.
- Планировать протокол так, чтобы следующая проверенная версия после ревью
  могла войти в корпус отдельным change. Файл `006` из другой копии сюда не
  входит.

## Forbidden

- Считать PostgreSQL Alembic (`alembic_/`, `alembic.ini`) системой миграций
  ClickHouse, хранить там журнал ClickHouse или переносить туда корпус
  `001`–`005`.
- Вызывать `app.db.migrate` или брать его ключ `731984123` как блокировку
  этого control plane.
- Хранить применённый статус миграций ClickHouse в PostgreSQL.
- Считать append-only fence ClickHouse или чтение последнего nonce mutex.
- Молча подставлять runtime DI, `DATABASE_URL` приложения, Redis или
  локальный файл вместо явного DSN координатора.
- Вешать учёт версий, журнал или apply на runtime бота, shop-runner, ARQ,
  Redis или `app/utils/click_house/`.
- Считать git-файл, в том числе локальный JSON, журналом применённого
  состояния цели.
- Считать наличие `001`–`005` или `IF NOT EXISTS` доказательством применения
  на проде.
- Автоматически проводить `005` как обычное изменение схемы или исполнять
  его в этом change.
- Втягивать или править `006` из другой рабочей копии.
- Считать тестовый DDL `test_adv_bot_clickhouse` вторым каноническим корпусом.
- Переписывать байты `001`–`005` ради принятия в систему.
- Подтверждать готовность применением на прод, подключением к проду,
  Kubernetes, секретами, выкладкой или живым сетевым вызовом.
- Обещать автоматический downgrade, файловую транзакцию или продолжение
  `partial` со середины файла.
- Закрывать неизвестную историю слепым догоняющим прогоном или пометкой
  «применено» без отдельной санкции и доказательства.
- Начинать расширение shop-wide campaign data, пока жизненный цикл не
  приведён в порядок.

## Examples

Хорошо:

- Control plane фиксирует SHA-256
  `scripts/clickhouse_migrations/001_create_incremental_tables.sql` …
  `004_create_auto_shelf_bid_increment_tables.sql` как schema-версии.
  Журнал цели при этом `history_unresolved`, пока нет санкционированной
  сверки. SQL этих версий на этом шаге не исполняется.
- На изолированной цели с явным DSN координатора `ensure-ledger` под
  `pg_try_advisory_lock` создаёт только
  `default_db.ch_schema_migration_ledger` и не пишет `version_applied`.
- Санкционированная сверка под тем же захватом дописывает базовую линию из
  доказательства осмотра и не исполняет SQL `001`–`005`.
- Санкционированный apply `001`–`004` после базовой линии держит ту же
  сессию блокировки до `version_applied` или до обработки отказа.
- `005` учитывается как privileged GRANT. Schema-writer его не получает.

Плохо:

- По наличию файлов записать «001–005 applied on prod».
- Заменить журнал цели файлом `applied_state.json` в git или таблицей
  PostgreSQL.
- Взять `pg_try_advisory_lock(731984123)` из Alembic и назвать это
  координатором ClickHouse.
- Прогнать `005` тем же writer, что и `CREATE TABLE default_db.*`.
- Перенести корпус в Alembic revision или скопировать `006` из соседней
  рабочей копии shop-wide.
- Объявить apply безопасным, потому что оператор обещает не запускать второй
  `clickhouse-client`. Ручной клиент вне запускатора этим не запрещён.
- Подменить unknown успешным `kubectl` или прогоном против живого
  продуктового ClickHouse в рамках этого change.
- После обрыва сессии координатора послать следующий statement или пометить
  версию применённой из-за `IF NOT EXISTS`.

## Related specs

- Stable spec capability `clickhouse-migration-lifecycle`:
  `openspec/specs/clickhouse-migration-lifecycle/spec.md`.
- Accepted, смежный, не заменяет это decision:
  `openspec/decisions/clickhouse-sql-database-qualification/decision.md`.

## Related changes

- `openspec/changes/archive/2026-10-01-clickhouse-migrations-control-plane` — archived change, который
  ввёл это decision.
- Источники инвариантов: `owner-contract.md`, `proposal.md` того же change.
  Owner способ не выбирал. Целевой журнал, координатор и права записи
  разрешены здесь из фактов репозитория и accepted decisions, не новым
  решением Owner.

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
