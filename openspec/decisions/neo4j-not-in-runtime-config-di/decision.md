# Decision: Neo4j не входит в runtime config/DI stack приложения

## Status

Accepted

## Context

В инфраструктурном конфиге приложения долгое время оставался обязательный блок Neo4j, хотя активный Neo4j driver/DI в runtime уже не подключены. Это создаёт ложную зависимость: создание app config и unit/DI падают без Neo4j env даже на путях, которым граф не нужен. Accepted decision на ownership/layering Neo4j в registry отсутствовал (`Architecture Decision Missing`). Нужно reusable правило: что принадлежит runtime config/DI surface, а что остаётся вне обязательного bootstrap.

## Decision

Neo4j MUST NOT быть обязательной частью runtime app config и application DI stack.

- Обязательный infrastructure config приложения MAY включать только сервисы, без которых bootstrap реально не стартует (например Redis/прочие активные зависимости по действующему коду).
- Вывод Neo4j из обязательного config/DI — корректный placement для текущего продукта; возврат Neo4j в runtime stack допускается только отдельным change с явным driver/DI wiring и зависимостью в Poetry.
- Stub’ы `NEO4J_*` в test harness MUST NOT считаться заменой архитектурного решения «сервис не в runtime stack».

## Applies to

- App infrastructure config / `AppConfig` bootstrap.
- Application DI containers и providers settings.
- Capability `app-config-without-neo4j`.
- Unit/DI verification paths, создающие app config без Neo4j env.
- Будущие change, которые захотят снова подключить Neo4j к приложению.

## Allowed

- Отсутствие поля/модели Neo4j в обязательном infrastructure config.
- Удаление orphan Neo4j DI-контейнера, не экспортируемого в active DI.
- Исторические docs/docker/monitoring артефакты вне runtime bootstrap (их зачистка — отдельный scope).
- Отдельный infra/ops change на teardown cluster Neo4j, не смешанный с app config MVP.

## Forbidden

- Требовать Neo4j env при создании app config «на всякий случай», если runtime path Neo4j не wired.
- Считать test env stub `NEO4J_*` целевой архитектурой вместо удаления hard-require.
- Возвращать Neo4j в `InfrastructureConfig` / DI без явного change, Poetry dependency и рабочего driver lifecycle.
- Маскировать отсутствие wiring ослаблением production validation defaults без decision/change.

## Examples

**Good:** создание app config для Redis client path успешно без переменных Neo4j; в infrastructure settings нет обязательного Neo4j-блока.

**Bad:** unit/DI падают с ValidationError missing Neo4j fields, хотя тест не использует граф; «фикс» — только `os.environ["NEO4J_…"]` в conftest без удаления require из config.

**Bad:** вернуть `infrastructure.neo4j` в config без контейнера driver и без зависимости в Poetry.

## Related specs

- `openspec/specs/app-config-without-neo4j/spec.md`

## Related changes

- `openspec/changes/archive/2026-08-01-drop-unused-neo4j-config` — ввёл и применил это decision.

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited _(нет accepted Neo4j decision — gap закрыт этим decision)_
- [x] new decision proposed because accepted decision was missing
- [x] implementation layer matches decision _(apply 2026-08-01: Neo4j removed from InfrastructureConfig + orphan DI deleted)_
- [x] No forbidden layer performs this decision's responsibility
- [x] Tests verify behavior without masking placement violations
