# Owner Contract

## Что хотим получить

Финальный acceptance-тест `tests/unit/test_clickhouse_migration_final_acceptance.py` читает артефакты там, где они лежат после архивации: в `openspec/changes/archive/2026-10-01-clickhouse-migrations-control-plane`. Проверка решения о lifecycle больше не требует статуса Proposed: переиспользуемое решение уже Accepted.

## Зачем

После канонической архивации change `clickhouse-migrations-control-plane` тест всё ещё смотрит в активный каталог `openspec/changes/clickhouse-migrations-control-plane` и в тексте решения ищет `Proposed`. Из-за этого acceptance расходится с фактическим архивом и промотированным решением.

## Что должно остаться неизменным

Поведение control plane миграций ClickHouse, набор команд runner и остальные проверки этого же теста: `--help`, read-only `validate`, замыкание 42 scenario, запрет forbidden imports и то, что shop-wide runtime остаётся вне пакета. Содержимое архива и смысл принятого решения не переписываем и не возвращаем change в активный каталог.

## Чего сейчас не делаем

Не чиним другие тесты и не меняем код runner. Не трогаем production, Kubernetes и секреты. На этом шаге не правим сам тест — только фиксируем договорённость, что правка будет узкой.

## Как поймём, что получилось

`test_clickhouse_migration_final_acceptance.py` открывает spec и decision из `openspec/changes/archive/2026-10-01-clickhouse-migrations-control-plane`. Проверка статуса решения согласована с Accepted. Остальные проверки этого файла по-прежнему проходят. Код пакета `scripts/clickhouse_migration_control_plane` для этой починки не менялся.

## Решения Owner

Чиним только регрессию acceptance-теста после архивации. Каноническое место артефактов — архивный каталог `openspec/changes/archive/2026-10-01-clickhouse-migrations-control-plane`. Статус переиспользуемого решения — Accepted, не Proposed. Код и тесты на этом шаге не меняем. Доступа к production нет.
