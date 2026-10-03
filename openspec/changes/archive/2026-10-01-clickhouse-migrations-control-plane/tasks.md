# Tasks

Разложение уже разрешённого design и spec `clickhouse-migration-lifecycle`.
Новых продуктовых выборов здесь нет. Proposed decision
`decisions/clickhouse-migration-lifecycle-ownership/decision.md` остаётся
`Proposed`: эти задачи его реализуют и MUST NOT повышать его до `Accepted`,
MUST NOT считать его решением Owner и MUST NOT промотить его в
`openspec/decisions/`.

План сценариев потреблён как текущее доказательство, не как второй
источник семантики:

```text
PLAN_EVIDENCE_ID: 0390ceb9be3cedd1c9453ab03363d3c679eaec0bab0b3a7970464e3f4d308a33
PLAN_CONTENT_HASH: 7da6c403c548a7958ee29812c489df3222784a5cd1b7fbba858dd69fe93bf592
SCENARIO_COUNT: 42
PLAN_STATUS: ready
PLAN_FRESHNESS: current
```

Роли доказательств: `LEGACY_BASELINE` фиксирует нынешние байты корпуса и
чужие слои и MUST оставаться зелёным после change. `TARGET_REGRESSION`
проверяет новое поведение. `FINAL_ACCEPTANCE` доказывает конечные запреты
change. Старое отсутствие запускатора не является обязательством, которое
MUST сохраниться.

Порядок внутри каждого среза: сначала тест, затем код. Чекбокс реализации
нельзя закрывать, пока тест того же среза не написан и не падает на
отсутствии охраняемого поведения. Apply завершён: все 31 чекбокса ниже
закрыты по репозиторному и pytest-доказательству; см. «Apply evidence».

Пакет: `scripts/clickhouse_migration_control_plane`. Точка входа:
`poetry run python -m scripts.clickhouse_migration_control_plane`.
Тесты: `tests/unit`, маркер `unit`, подставные порт цели
`isolated-target-port-v1` и сессия координатора `coordinator-session-v1`.
Живой сокет, прод-учётные данные и сервисы ClickHouse/PostgreSQL этим
change MUST NOT требоваться.

У каждой новой функции и каждого нового теста docstring на русском со
ссылкой на spec `clickhouse-migration-lifecycle` и причиной, зачем вызов
существует. Тест MUST NOT мокать разбор корпуса, класс привилегии,
сравнение SHA-256, ворота санкции, нарезку statement, диспетчер команд и
отказ до запрещённого statement. Общий module-level patch вокруг `await`
запрещён. `AsyncMock(return_value=True)` не является ни одним из двух
контрактов.

Три санкции MUST оставаться разными и MUST NOT подменять друг друга:
флаг `ensure-ledger`, флаг сверки, флаг apply. Точное имя argv — деталь
команды, не новый продуктовый выбор.

Telegram UI этот change не создаёт и не меняет.

## 1. LEGACY_BASELINE: корпус и чужие слои

- [x] 1.1 `LEGACY_BASELINE`. Добавить тест, который читает сырые байты
  `scripts/clickhouse_migrations/001`–`005` и фиксирует их SHA-256 без
  нормализации переводов строк и без отбрасывания комментариев. Существующий
  читатель `004` MUST по-прежнему видеть
  `default_db.auto_shelf_bid_intervals` и
  `default_db.auto_shelf_bid_prev`. Тест MUST оставаться зелёным после
  появления запускатора и MUST NOT требовать, чтобы запускатора не было.
- [x] 1.2 `LEGACY_BASELINE`. Добавить тест границ, которые change MUST NOT
  сдвинуть: `alembic.ini` и `alembic_/` не содержат ревизии `001`–`005`;
  тестовый DDL `tests/support/destructive_ch_reset.py` и база
  `test_adv_bot_clickhouse` не лежат в каталоге корпуса; файл `006` в этом
  worktree не читается и не копируется. Сценарии этого среза:
  `Alembic stays out of ClickHouse migrations`,
  `Test DDL is not canonical`, `Missing 006 is not imported`,
  `Shop-wide expansion waits` — здесь только неизменность чужих деревьев;
  запрет импорта и расширения повторяется в `TARGET_REGRESSION` среза 14.

## 2. Контракты подставных швов

- [x] 2.1 `TARGET_REGRESSION`. Написать падающие контрактные тесты
  `isolated-target-port-v1` на общий fixture: `EXEC_SQL` принимает один
  statement `schema_ddl` и отвергает текст `005`, непроверенный файл,
  разошедшийся SQL и statement из одного комментария; `LEDGER_APPEND`
  только дописывает события и не имеет обновления на месте;
  `LEDGER_READ` читает события одного `serverUUID()` и `default_db` по
  `event_seq`; `SERVER_UUID` различает ненулевой, отсутствующий и нулевой
  UUID; `SESSION_DATABASE` различает `default_db` и любую иную базу, включая
  `test_adv_bot_clickhouse`; `INSPECT_READ` отдаёт готовые метаданные без
  записи журнала. Живого ClickHouse MUST NOT быть.
- [x] 2.2 `TARGET_REGRESSION`. Написать падающие контрактные тесты
  `coordinator-session-v1`: захват `pg_try_advisory_lock` или, только при
  явном ожидании оператора, `pg_advisory_lock`; ключ пространства имён
  migration-control MUST NOT равняться `731984123`; `target_key` — знаковый
  int32 из первых четырёх байтов SHA-256 UTF-8 строки
  `clickhouse-migration-control\n{server_uuid}\ndefault_db` (big-endian);
  удержание через мутацию; ложный `try` не шлёт statement; смерть сессии
  останавливает следующий statement; в координаторе нет applied-status.
  Чтение nonce MUST NOT считаться захватом.
- [x] 2.3 Реализовать протоколы порта цели и сессии координатора и
  внутрипроцессные подстановки так, чтобы тесты 2.1 и 2.2 стали зелёными.
  Подстановки MUST NOT подменять решения запускатора. Удаление запрета
  `EXEC_SQL` на текст `005` MUST ронять тест 2.1.

## 3. Принятие корпуса без исполнения

- [x] 3.1 `TARGET_REGRESSION`. Тесты реального принятия корпуса через
  `validate`, без порта и без координатора. Сценарии:
  `Register the existing corpus without executing it` — MUST записать `id`,
  имя файла, `privilege_class` и SHA-256 сырых байтов `001`–`005`, MUST NOT
  менять байты, MUST NOT исполнять SQL, MUST NOT писать applied;
  `Qualification stays in the existing SQL` — `001`–`004` сохраняют
  `default_db.<object>`, `005` сохраняет `system.<table>`;
  `Missing 006 is not imported` — отпечаток содержит только `001`–`005`;
  `Test DDL is not canonical` — session DDL тестовой базы отсутствует в
  отпечатке. Класс `005` в отпечатке — планировочный `privileged_grant`, не
  решение Owner.
- [x] 3.2 Реализовать чтение корпуса и отпечаток в пакете control plane так,
  чтобы тест 3.1 стал зелёным. Байты `001`–`005` MUST NOT изменяться.
  Принятие файла MUST NOT включать исполнение. Docstring каждой новой
  функции ссылается на spec `clickhouse-migration-lifecycle`.

## 4. Разбор, класс и drift до мутации

- [x] 4.1 `TARGET_REGRESSION`. Тесты реальных `validate`, `plan` и `apply`
  на отказе до `execute`. Сценарии:
  `Raw bytes no longer match the fingerprint` — drift корпуса, план и apply
  MUST NOT исполнять SQL, результат MUST быть неуспешным;
  `Privilege class cannot be substituted` — подмена класса `005` на обычный
  schema DDL MUST провалить validate, текст `005` MUST NOT уйти в writer;
  `A semicolon inside a string stops before apply` — validate MUST
  завершиться ошибкой, apply MUST NOT начаться;
  `Unreviewed numeric prefix blocks apply` — файл с числовым префиксом вне
  отпечатка, включая непроверенный `006` в каталоге чтения, MUST быть
  `unreviewed_version` и MUST NOT исполниться.
- [x] 4.2 Реализовать нарезку statement (граница — один statement после
  снятия полнострочных комментариев `--`), вывод класса из текста SQL и
  отказ `corpus_drift` / подмены класса / непроверенного префикса так, чтобы
  тест 4.1 стал зелёным. В этих пяти файлах точки с запятой внутри строки
  нет; встретив её, разбор MUST остановить apply. Комментарий про
  пересоздание объекта MUST NOT исполняться — исполнение комментария
  закрывается тестом среза 10.

## 5. Команды без записи

- [x] 5.1 `TARGET_REGRESSION`. Тесты реальных команд, которые журнал не пишут
  и координатор не открывают. Сценарии:
  `Status without a target is not an applied record` — без цели печать
  `target_not_attached`, applied-записи нет, координатор не открыт;
  `File presence is not applied state` — при прикреплённой цели ответ только
  из журнала или из факта «цель не прикреплена»; файлы и `IF NOT EXISTS`
  MUST NOT быть ответом и MUST NOT писать `version_applied`;
  `Plan is dry` — для отсутствующей цели, неизвестной истории, `005`, drift,
  `partial` и прод-класса план MUST показать порядок версий, класс, SHA-256,
  statement и причину остановки, MUST NOT исполнять SQL, MUST NOT писать
  журнал, MUST NOT брать lock;
  `Inspect does not write and does not baseline` — только чтение через порт
  (`system.tables`, `system.columns`, `SHOW CREATE` на подстановке), без
  append и без захвата; вывод осмотра MUST NOT быть базовой линией. Без цели
  inspect сеть не открывает.
- [x] 5.2 Реализовать `status`, `plan` и `inspect` (и довести `validate` из
  срезов 3–4) так, чтобы тест 5.1 стал зелёным. Эти четыре команды MUST NOT
  открывать координатор. Код выхода `0` допустим для цельного `validate`,
  честного `status` (включая неизвестную историю и `ledger_absent`) и
  построенного `plan`.

## 6. Журнал на цели, не в PostgreSQL

- [x] 6.1 `TARGET_REGRESSION`. Тесты реального мутирующего пути на подстановке
  порта. Сценарии:
  `Ledger identity is the server UUID and default_db` — журнал
  `default_db.ch_schema_migration_ledger`, каждое состояние — новый append,
  не обновление строки; PostgreSQL applied-status не получает; координатор
  хранит только след lock;
  `Missing or zero server UUID fails closed` — отказ, hostname MUST NOT
  стать `target_id`;
  `Another database is not this corpus target` — сессия не `default_db`,
  включая `test_adv_bot_clickhouse`, MUST отказаться и MUST NOT писать
  `version_applied`;
  `Ledger checksum differs from the file` — состояние `drift`, apply MUST
  NOT чинить расхождение исполнением файла и MUST NOT переписывать
  `001`–`005`, результат неуспешный.
- [x] 6.2 Реализовать форму журнала пакета: колонки `target_id`, `database`,
  `version_id`, `sha256`, `privilege_class`, `event_type`,
  `statement_ordinal`, `statement_count`, `runner_nonce`,
  `coordinator_lock_identity`, `evidence_sha256`, `event_seq`, `created_at`;
  движок `MergeTree`, `ORDER BY (target_id, version_id, event_seq)`; текущее
  состояние — event с максимальным `event_seq`. Состояния оператора MUST
  включать `ledger_absent`, `history_unresolved`, `applying`, `partial`,
  `applied`, `drift`, `blocked_privileged_grant`. Тест 6.1 MUST стать
  зелёным. Журнал MUST NOT жить в git, в таблице PostgreSQL, в Alembic и в
  Redis.

## 7. ensure-ledger

- [x] 7.1 `TARGET_REGRESSION`. Парные тесты. Положительный сценарий
  `Authorized ensure-ledger holds the advisory lock`: изолированная цель,
  явный DSN координатора и отдельный флаг санкции `ensure-ledger` MUST
  взять сессионный advisory lock этой пары `serverUUID()` + `default_db` до
  создания журнала и держать сессию до конечного исхода или отказа.
  Сценарий `Empty ledger does not apply the corpus`: создаётся только
  `default_db.ch_schema_migration_ledger`, `version_applied` для `001`–`005`
  MUST NOT появиться, состояние после создания без базовой линии MUST быть
  `history_unresolved` («не установлено»), а не «на сервере точно
  отсутствует». До создания состояние MUST быть `ledger_absent`. Fence-таблицу
  команда MUST NOT создавать.
- [x] 7.2 Реализовать `ensure-ledger` так, чтобы тест 7.1 стал зелёным.
  Создание журнала MUST идти только на `target_class=isolated` под
  удержанным lock и своим флагом. Прод-класс эту команду не открывает —
  отказ прод-класса закрывается срезом 14.

## 8. Неизвестная история блокирует прогон

- [x] 8.1 `TARGET_REGRESSION`. Сохранить обе ветки, не схлопывая их в «прогон
  MAY случиться». Ветка неизвестной истории, сценарии
  `Unresolved history blocks apply and mark-applied` и
  `Catch-up cannot close unknown history`: пока цель `ledger_absent` или
  `history_unresolved`, apply MUST отказаться даже с флагом apply, пометка
  «применено» MUST отказаться, догоняющий прогон `001`–`005` MUST NOT
  выполниться, статус MUST остаться неизвестным. Ветка после санкционированной
  базовой линии в этом срезе не реализуется: она MUST открываться только
  срезом 9 и положительным apply среза 10. `IF NOT EXISTS` и ручной
  `clickhouse-client` из заголовка `005`, точка входа
  `trunc_system_log_in_clickhouse` и тестовый DDL MUST NOT стать этой
  записью.
- [x] 8.2 Реализовать отказы apply и mark-applied при `ledger_absent` и
  `history_unresolved` так, чтобы тест 8.1 стал зелёным и удаление отказа
  роняло его. Политику продолжения `partial` этот change MUST NOT задавать.

## 9. Сверка отдельно от осмотра и от apply

- [x] 9.1 `TARGET_REGRESSION`. Три сценария на реальной команде `reconcile`:
  `Reconcile requires its own flag and inspection evidence` — свой флаг,
  SHA-256 доказательства осмотра, явный конфиг изолированной цели и
  удержанный lock MUST дописать базовую линию и MUST NOT исполнить SQL
  `001`–`005`; одного флага apply MUST NOT хватить;
  `Filename list and undetermined evidence do not apply a version` — список
  имён файлов MUST быть отвергнут, версия «не определено» MUST NOT получить
  `version_applied`;
  `Reconcile without flag or evidence writes nothing` — отсутствие флага или
  доказательства MUST NOT писать базовую линию.
- [x] 9.2 Реализовать `reconcile` так, чтобы тест 9.1 стал зелёным. Флаг
  сверки MUST NOT заменять флаг apply. Против прода команда в этом change
  MUST NOT запускаться.

## 10. Санкционированный apply 001–004

- [x] 10.1 `TARGET_REGRESSION`. Положительная ветка, когда ворота держатся
  все сразу. Сценарии:
  `Schema writer may run only schema DDL under every gate` — для
  изолированной непроизводственной цели, явного конфига цели, явного DSN,
  удержанного advisory lock, санкционированной базовой линии, совпавшего
  SHA-256 и версии `001`/`002`/`003`/`004` не в `partial` и не в `applying`
  флаг apply MUST заставить schema-writer исполнить schema DDL этой версии;
  порядок событий MUST быть `apply_started`, затем `statement_ok` с
  порядковым номером, затем `version_applied` только после успеха всех
  statement; на событиях MUST быть nonce, идентичность lock, UUID цели,
  база, версия, sha256, ordinal и время; текст `005` MUST NOT попасть в
  writer;
  `Statements commit one by one` — файл MUST NOT считаться транзакцией,
  автоматический downgrade MUST NOT обещаться;
  `Comments are not statements` — комментарий отсутствует в отправленном SQL
  и MUST NOT пересоздавать объект.
  Если хотя бы одно ворота отсутствует, эта положительная ветка MUST NOT
  срабатывать: отказ — срезы 8, 11, 13 и 14.
- [x] 10.2 Реализовать apply `schema_ddl` под удержанной сессией так, чтобы
  тест 10.1 стал зелёным. Schema-writer MUST исполнять `001`–`004` только
  при всех воротах сразу. Успех statement с `IF NOT EXISTS` сам по себе
  `version_applied` MUST NOT создавать. Пакет MUST NOT импортировать
  `app.utils.click_house` и MUST NOT читать настройки подключения приложения.

## 11. Отказы apply, 005 и идемпотентность

- [x] 11.1 `TARGET_REGRESSION`. Сохранить развилки явно. Сценарии:
  `Apply without authorization refuses` — без флага apply, даже если прочие
  ворота уже есть, MUST отказаться до statement, результат неуспешный;
  `Authorized apply still refuses 005` — при изолированной цели, удержанном
  lock и флаге apply версия `005` MUST отказаться кодом
  `blocked_privileged_grant` до вызова schema-writer, текст `005` writer
  MUST NOT получить; отдельный privileged writer этот change MUST NOT
  создавать и `005` MUST NOT исполняться;
  `Same checksum skips SQL` — повтор apply версии `applied` с тем же SHA-256
  MUST NOT слать SQL и MUST оставить версию applied; под удержанным lock
  система MAY дописать audit-event `skipped_already_applied` и MUST NOT
  быть обязана это делать, если spec не требует обязательной записи;
  `Partial and applying are not idempotent skips` — при последнем состоянии
  `partial` или `applying`, даже с новым флагом apply и заново взятым lock,
  система MUST отказаться, MUST NOT пропустить версию как applied, MUST NOT
  переиграть statement, MUST NOT продолжить с середины файла и MUST NOT
  закрыть её из-за `IF NOT EXISTS`.
- [x] 11.2 Реализовать эти отказы и пропуск уже закрытой версии так, чтобы
  тест 11.1 стал зелёным. Удаление отказа `005` или превращение `partial` в
  идемпотентный skip MUST ронять соответствующий тест. Классификация `005`
  остаётся планированием, не решением Owner.

## 12. Обрыв и рестарт

- [x] 12.1 `TARGET_REGRESSION`. Сценарии:
  `Crash after a successful statement leaves the version unclosed` — обрыв
  между `apply_started` и `version_applied`, обрыв ClickHouse или потеря
  сессии координатора оставляют `applying` или `partial`; следующий
  statement MUST NOT отправиться; уже успешный statement MUST NOT откатиться;
  `Restart does not continue a partial or unknown history` — новый процесс
  читает журнал цели, не память и не PostgreSQL; если после рестарта состояние
  `partial` или `history_unresolved`, слепой прогон MUST NOT начаться, даже
  если lock снова взят. Ветка «журнал показывает applied с тем же SHA-256»
  остаётся пропуском SQL из среза 11, а не продолжением файла.
- [x] 12.2 Реализовать fail-closed обрыва так, чтобы тест 12.1 стал зелёным.
  Автоматического продолжения с середины файла и автоматического downgrade
  MUST NOT быть. Этот change политику продолжения `partial` MUST NOT
  определять.

## 13. Координатор: захват, чужой ключ, потеря

- [x] 13.1 `TARGET_REGRESSION`. Четыре сценария на реальных мутирующих
  командах и подстановке координатора:
  `Missing coordinator fails closed` — нет явного DSN у `ensure-ledger`,
  `reconcile` или `apply` → `blocked_missing_coordinator` до statement;
  `DATABASE_URL` приложения MUST NOT подставиться;
  `Wrong coordinator is not this lock` — ключ Alembic `731984123`, вызов
  `app.db.migrate`, молчаливый `DATABASE_URL`, Redis, файл или nonce
  ClickHouse MUST NOT быть этим lock, отказ до statement;
  `Lock contention sends no statement` — `pg_try_advisory_lock` вернул ложь →
  `blocked_lock_contention`, statement цели нет, чтение nonce не является
  захватом;
  `Lock loss stops further SQL` — смерть сессии после `apply_started` или
  `statement_ok` MUST NOT отправить следующий statement и MUST оставить
  `applying` или `partial` без отката уже успешного statement.
  По умолчанию захват MUST быть `pg_try_advisory_lock`. Блокирующий
  `pg_advisory_lock` MAY использоваться только если оператор явно задал
  ожидание, на том же ключе и той же сессии.
- [x] 13.2 Реализовать сессионный advisory lock по design §7 так, чтобы тест
  13.1 стал зелёным. Реализация MUST NOT искать второй координатор и MUST
  NOT сливать два DSN в один mutex. `status`, `validate`, `plan` и `inspect`
  координатор MUST NOT открывать. Оговорка, что ручной `clickhouse-client`
  запускатором не перехватывается, MUST быть сказана оператору и MUST NOT
  считаться доказательством единственного писателя.

## 14. Изолированная мутация, прод и честный выход

- [x] 14.1 `TARGET_REGRESSION`. Сценарии:
  `Isolated apply is real and production is untouched` — санкционированные
  `ensure-ledger`, сверка и apply `001`–`004` на подставных порте и сессии
  MUST реально мутировать контракт цели под удержанным lock; прод-соединение
  и живой сетевой вызов MUST NOT открываться;
  `Production target without a separate GO refuses` — класс `production` на
  `ensure-ledger`, `reconcile` и `apply` MUST отказаться кодом
  `blocked_production_target` до захвата и до statement; этот change MUST
  NOT быть будущим GO оператора;
  `Honest success and refusal` — выход `0` только когда команда сделала ровно
  свою работу (цельный `validate`; честный `status`, включая неизвестную
  историю; построенный `plan`; `ensure-ledger` / `reconcile` / `apply` при
  пройденных изолированных воротах и удержанном lock); drift, подмена класса
  `005`, нет санкции, неизвестная история, `partial`, нет или чужой
  координатор, конкуренция или потеря lock, прод-класс и передача `005` в
  schema-writer MUST быть ненулевым выходом;
  `The application client is not the migration executor` — пакет MUST NOT
  использовать `app.utils.click_house` и MUST NOT читать его настройки и
  учётные данные;
  `Alembic stays out of ClickHouse migrations` — корпус и журнал не переносятся
  в Alembic, lock `731984123` не используется, `app.db.migrate` не вызывается,
  шов `tests.support.rewrite_default_db_ch_client` не используется;
  `Shop-wide expansion waits` — этот change MUST NOT начать расширение сбора
  shop-wide campaign data и MUST NOT менять shop-wide код.
- [x] 14.2 Реализовать оставшиеся отказы прод-класса, граф импортов и коды
  выхода так, чтобы тест 14.1 стал зелёным. Прод-сокет, прод-учётные данные,
  секреты, Kubernetes и выкладка MUST NOT появляться. Готовность change
  MUST NOT подтверждаться применением на прод.

## 15. FINAL_ACCEPTANCE: все 42 сценария и границы

- [x] 15.1 `FINAL_ACCEPTANCE`. Собрать целевой прогон
  `poetry run pytest -m unit` по новым тестам пакета и швов. В нём MUST быть
  отдельный целевой тест на каждый из 42 сценариев плана с
  `PLAN_EVIDENCE_ID`
  `0390ceb9be3cedd1c9453ab03363d3c679eaec0bab0b3a7970464e3f4d308a33`.
  Имена сценариев и привязка к срезам — в таблице замыкания ниже. Прогон
  MUST NOT требовать Docker, живой ClickHouse и живой PostgreSQL.
- [x] 15.2 `FINAL_ACCEPTANCE`. Проверить кросс-границу одним целевым тестом
  и просмотром diff: байты `001`–`005` совпадают с `LEGACY_BASELINE` 1.1;
  пакет не импортирует клиент приложения, Alembic и тестовый шов переписывания
  `default_db`; координатор не хранит applied-status; schema-writer не
  получает текст `005`; proposed decision остаётся `Proposed`; shop-wide
  код, `app/` runtime, секреты и выкладка этим change не меняются. Удаление
  любого охраняемого отказа из срезов 8–14 MUST ронять его тест.

## Замыкание 42 сценариев

Каждая строка — сценарий spec
`specs/clickhouse-migration-lifecycle/spec.md`, который обязан закрыться
названным тестом. Отдельный сценарий не откладывается.

| Сценарий | Тест |
| --- | --- |
| Register the existing corpus without executing it | 3.1 |
| File presence is not applied state | 5.1 |
| Raw bytes no longer match the fingerprint | 4.1 |
| Ledger checksum differs from the file | 6.1 |
| Privilege class cannot be substituted | 4.1 |
| Ledger identity is the server UUID and default_db | 6.1 |
| Missing or zero server UUID fails closed | 6.1 |
| Another database is not this corpus target | 6.1 |
| Empty ledger does not apply the corpus | 7.1 |
| Status without a target is not an applied record | 5.1 |
| Unresolved history blocks apply and mark-applied | 8.1 |
| Catch-up cannot close unknown history | 8.1 |
| Inspect does not write and does not baseline | 5.1 |
| Reconcile requires its own flag and inspection evidence | 9.1 |
| Filename list and undetermined evidence do not apply a version | 9.1 |
| Reconcile without flag or evidence writes nothing | 9.1 |
| Plan is dry | 5.1 |
| Apply without authorization refuses | 11.1 |
| Schema writer may run only schema DDL under every gate | 10.1 |
| Honest success and refusal | 14.1 |
| Authorized apply still refuses 005 | 11.1 |
| Qualification stays in the existing SQL | 3.1 |
| Missing 006 is not imported | 3.1 |
| Unreviewed numeric prefix blocks apply | 4.1 |
| Same checksum skips SQL | 11.1 |
| Partial and applying are not idempotent skips | 11.1 |
| Statements commit one by one | 10.1 |
| A semicolon inside a string stops before apply | 4.1 |
| Comments are not statements | 10.1 |
| Crash after a successful statement leaves the version unclosed | 12.1 |
| Restart does not continue a partial or unknown history | 12.1 |
| Authorized ensure-ledger holds the advisory lock | 7.1 |
| Missing coordinator fails closed | 13.1 |
| Wrong coordinator is not this lock | 13.1 |
| Lock contention sends no statement | 13.1 |
| Lock loss stops further SQL | 13.1 |
| Isolated apply is real and production is untouched | 14.1 |
| Production target without a separate GO refuses | 14.1 |
| The application client is not the migration executor | 14.1 |
| Alembic stays out of ClickHouse migrations | 1.2 и 14.1 |
| Test DDL is not canonical | 1.2 и 3.1 |
| Shop-wide expansion waits | 1.2 и 14.1 |

## Apply evidence (post-apply reconcile)

Зафиксировано после прерванного apply и bounded reconcile
`CHMIG-TASKS-RECONCILE-20260930-R1`:

- Пакет `scripts/clickhouse_migration_control_plane/` — 9 модулей; точка
  входа `poetry run python -m scripts.clickhouse_migration_control_plane`.
- Тесты `tests/unit/test_clickhouse_migration_*.py` и
  `tests/unit/clickhouse_migration_contract_fixture.py` — 75 unit-тестов,
  маркер `unit`, без Docker, живого ClickHouse и PostgreSQL.
- Прогон
  `poetry run pytest -m unit tests/unit/test_clickhouse_migration_*.py` —
  75 passed (2026-09-30).
- Замыкание 42 сценариев:
  `test_every_planned_scenario_is_named_by_a_target_test` в FINAL_ACCEPTANCE.
- `PLAN_EVIDENCE_ID` и `scenario-coverage/plan.receipt.json` upstream inputs
  без изменений; `PLAN_FRESHNESS: current` сохранён.

```text
APPLY_RECONCILE
STATUS: complete
TASKS_COMPLETE: 31/31
EVIDENCE_COMMAND: poetry run pytest -m unit tests/unit/test_clickhouse_migration_*.py
EVIDENCE_RESULT: 75 passed
RECONCILE_DATE: 2026-09-30
PLAN_EVIDENCE_ID_UNCHANGED: yes
```

```text
TASK_GENERATION_READINESS
UNRESOLVED_DESIGN_CHOICES: none
UNRESOLVED_PRODUCT_CHOICES: none
UPSTREAM_NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
CONDITIONAL_BRANCHES_PRESERVED: yes
SCENARIO_REQUIREMENTS_CONSUMED: yes
SCENARIO_PLAN_EVIDENCE_ID: 0390ceb9be3cedd1c9453ab03363d3c679eaec0bab0b3a7970464e3f4d308a33
SCENARIO_PLAN_STATUS: ready
SCENARIO_PLAN_FRESHNESS: current
TASKS_STATUS: READY
REASON: none
```
