# Decision: ClickHouse SQL — обязательная квалификация database

## Status

Accepted (promoted to `openspec/decisions/clickhouse-sql-database-qualification/`)

## Context

Рабочий ClickHouse-контур приложения использует БД `default_db`. Имя БД
сейчас задаётся в клиенте (`app/utils/click_house/client.py`), а не через
env. Недавние правки под injectable test seam сняли `default_db.` из текста
отдельных CH SQL, полагаясь на session database клиента. Для рабочего
контура запрос без имени БД в тексте SQL считается некорректным.

В registry (`openspec/decisions/`) нет accepted decision про квалификацию
database в CH SQL (`Architecture Decision Missing` после context-first
lookup по index и поиску clickhouse/default_db). Нужен reusable domain
invariant: «имя БД MUST быть в тексте CH query», чтобы будущие seam/test
правки не повторяли регресс.

Политика env → `client.database` как единственный резолвер и массовый
unqualify всех readers — вне этого decision (отдельный follow-up / park).

## Decision

ClickHouse SQL в application read/write paths MUST явно квалифицировать
database в тексте запроса для текущего рабочего контура: `default_db.<object>`
(таблица, MV, view и т.п.).

- Квалификация живёт в тексте SQL (строка запроса / SQL-файл), а не только
  в неявном session `client.database`.
- Текущее каноническое имя рабочей БД: `default_db`.
- Proof корректности qualification — проверка issued SQL (SQL-contract /
  capture), а не полный mock функции, чей SQL меняли.

## Applies to

- Application-owned ClickHouse queries (Python string SQL, `sql/` под
  сервисами), которые обращаются к объектам рабочей БД.
- Read-path статистики/агрегатов (в т.ч. `wb_adv_updater` /
  `get_keyword_statistic_clickhouse` и однотипные места).
- Test seams и injectable wrappers вокруг таких queries: seam не отменяет
  требование квалификации в issued SQL.
- Capability `clickhouse-query-database-qualification` этого change.

## Allowed

- Писать `FROM default_db.<table>` / `JOIN default_db.<mv>` и аналоги в
  тексте CH SQL для рабочего контура.
- Точечно восстанавливать снятый prefix `default_db.` после seam/рефакторинга.
- Unit/SQL-contract тесты, которые ассертят наличие `default_db.` (или
  согласованного qualified form) в issued SQL.
- Документировать в docstring, что рабочая БД — `default_db`, без подмены
  proof полным mock producer'а SQL.

## Forbidden

- Считать «голый» `FROM <table>` допустимым для рабочего CH query path
  только потому, что клиент выставил `database=default_db`.
- Снимать database-prefix из CH SQL ради injectable test seam без
  одновременного сохранения квалификации в issued SQL и SQL-contract proof.
- Доказывать корректность rewrite CH SQL полным mock'ом функции, чей SQL
  меняли (`SQL_REWRITE_MOCKED_AWAY`).
- В рамках этого decision менять политику на env-only резолв имени БД или
  массово переводить readers на unqualified SQL.

## Examples

Good:

- `FROM default_db.mv_clusters_daily_agg` в
  `app/modules/wb_adv_updater/data_manager.py` (`get_keyword_statistic_clickhouse`).
- Unit-тест перехватывает issued SQL и требует substring `default_db.`.

Bad:

- `FROM mv_clusters_daily_agg` в том же path «потому что client.database
  уже default_db».
- Unit-тест мокает всю `get_keyword_statistic_clickhouse` и не видит текст
  SQL после снятия prefix.

## Related specs

- Delta (этот change):
  `openspec/changes/fix-bug-with-remove-ch-db-name-from-queries/specs/clickhouse-query-database-qualification/spec.md`
  (создаётся следующим артефактом).
- Stable: в `openspec/specs/` отдельного capability на CH qualification нет.

## Related changes

- `fix-bug-with-remove-ch-db-name-from-queries` (proposed; имя каталога
  историческое — intent: удержать/вернуть квалификацию, не убрать DB из
  queries).

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (нет accepted по теме; зафиксирован gap)
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision
