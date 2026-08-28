# Change: drop-unused-neo4j-config

## Why

Обязательный Neo4j в инфраструктурном конфиге приложения блокирует создание runtime config и unit/DI-прогоны, хотя драйвер и DI Neo4j в приложении уже не подключены. Нужно убрать мёртвый hard-require сейчас, чтобы тесты и config surface не зависели от неиспользуемого сервиса, и зафиксировать, что Neo4j не входит в runtime stack.

## Intent

Один intent: убрать Neo4j из обязательной поверхности app config / DI, не реанимируя graph/ML pipeline и не делая полную зачистку docs/infra в этом change.

## Current behavior

- Инфраструктурный конфиг приложения требует переменные Neo4j при создании config.
- Без них падают пути, которым Neo4j не нужен (в т.ч. unit/DI).
- Активный Neo4j DI/driver в приложении отсутствует; пакет драйвера в зависимостях Poetry не заявлен.

## Desired behavior

- Создание app config MUST NOT требовать Neo4j env.
- Runtime config/DI surface MUST NOT объявлять Neo4j как обязательную зависимость приложения.
- Unit/DI пути, ранее падавшие только из‑за отсутствия Neo4j env, MUST проходить без stub’ов Neo4j как «архитектурного костыля».

## What Changes

- **BREAKING** (config contract): удаление обязательного Neo4j-блока из инфраструктурного конфига приложения; потребители `settings.infrastructure.neo4j` (если остались) больше не получат это поле.
- Удаление orphan Neo4j DI-контейнера / мёртвой config-модели из active surface.
- Proposed architecture decision: Neo4j не входит в runtime config/DI stack приложения.
- Точечная проверка unit/DI, затронутых ValidationError Neo4j.

## Scope

### In scope

- Обязательный Neo4j в app infrastructure config.
- Orphan Neo4j DI на стороне приложения.
- Decision + минимальная verification для разблокировки unit/DI.

### Out of scope

- Docs / docker / monitoring runbooks про Neo4j.
- Commented ML/graph entrypoints и косметическая зачистка мёртвого кода вне config/DI.
- Cluster teardown живого Neo4j в k8s (отдельный infra GO).
- Stub `NEO4J_*` в test conftest как финальная архитектура.
- Другие красные unit-кластеры (TG tokens, shelf bid asserts и т.п.), не вызванные Neo4j config.

Отложено в WORKLOG: `DOTO/WORKLOG.md` → `Deferred from change drop-unused-neo4j-config` (не DoD).

## Capabilities

### New Capabilities

- `app-config-without-neo4j`: требования к поверхности app config/DI без обязательного Neo4j и к наблюдаемому поведению создания config без Neo4j env.

### Modified Capabilities

- _(нет — существующие specs про ClickHouse qualification / local-dev connectivity не меняют requirement-level поведение этого change)_

## Impact

- Config/DI bootstrap приложения (все пути через создание app config).
- Локальные/CI unit-прогоны, ранее падавшие на missing Neo4j fields.
- Возможный внешний/legacy код, ожидавший поле Neo4j в infrastructure settings (в активном runtime репозитория не используется).

## Risk

- Низкий для paid automation / WB write path: Neo4j не является hot path shop-runner.
- Средний, если вне репозитория ещё читают `infrastructure.neo4j` — контракт ломается явно (**BREAKING** config).

## Rollback idea

Вернуть обязательный Neo4j-блок в infrastructure config и orphan DI-файл из git history; при необходимости временно задать test env stubs (не как целевая архитектура).
