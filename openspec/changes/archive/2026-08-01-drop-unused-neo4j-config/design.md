# Design: drop-unused-neo4j-config

## Context

`AppConfig` / `InfrastructureConfig` требуют nested `Neo4jConfig` с обязательными `NEO4J_*` полями. Любой bootstrap через `AppConfig.create()` (Redis client provider, DI `AppContainer.settings`, часть unit) падает с ValidationError, хотя:

- Poetry dependency на `neo4j` отсутствует;
- `create_neo4j_driver` / `Neo4jLifecycle` в DI databases нет;
- `Neo4jContainer` не экспортируется из active containers.

Нужен минимальный вырез hard-require из config/DI surface без зачистки docs/ML/k8s.

## Goals / Non-Goals

**Goals:**

- Убрать обязательный Neo4j из infrastructure config.
- Убрать orphan Neo4j DI-контейнер из дерева приложения.
- Соблюсти proposed decision: Neo4j не в runtime config/DI.
- Разблокировать unit/DI, падавшие только на missing Neo4j fields.

**Non-Goals:**

- Docs / `dockers/neo4j` / monitoring runbooks.
- Commented ML/graph entrypoints и `image_master` хвосты.
- Cluster teardown live Neo4j.
- Stub `NEO4J_*` в `conftest` как целевое решение.
- Фикс прочих unit-кластеров (TG tokens, shelf asserts).

Deferred parks: `DOTO/WORKLOG.md` (`[deferred-from:drop-unused-neo4j-config]`).

## Architecture Decision References

- Proposed (change-local): `openspec/changes/drop-unused-neo4j-config/decisions/neo4j-not-in-runtime-config-di/decision.md`
- Accepted registry: relevant Neo4j runtime ownership decision отсутствует до этого change (`Architecture Decision Missing` закрыт proposed artifact выше; при archive — promote в `openspec/decisions/`).

## Ownership & Placement

| Роль | Layer |
|---|---|
| Owner | App infrastructure config (`app/configs/infrastructure_config`) + orphan DI cleanup (`app/core/di/containers`) |
| Allowed | Удаление поля/модуля Neo4j config; удаление неэкспортируемого `neo4j_container.py`; точечные unit/DI проверки |
| Forbidden | Ослабление prod validation «defaults вместо удаления»; маскировка stub’ами в conftest как DoD; трогать shop-runner bidding / WB write; infra k8s teardown в этом change |

Rationale: проблема — ложная обязательность на config/DI bootstrap, не отсутствие graph feature. Placement совпадает с decision: Neo4j MUST NOT быть required runtime dependency.

## Decisions

1. **Удалить поле `neo4j` из `InfrastructureConfig`, а не делать optional defaults**  
   Альтернатива (optional Field + conftest stubs) сохраняет мёртвый контракт. Выбрано удаление — соответствует decision и BREAKING config из proposal.

2. **Удалить `neo4j_config.py` и orphan `neo4j_container.py`**  
   Контейнер уже broken (импорт несуществующих driver factories) и не в `__init__` export. Оставлять файл хуже, чем явный delete.

3. **Не трогать Redis/WB блоки `InfrastructureConfig`**  
   Минимальный diff; только Neo4j.

4. **Verification = targeted unit/DI, не полный `-m unit` как DoD**  
   Достаточно путей, ранее падавших на Neo4j ValidationError; остальные красные кластеры out of scope.

## Risks / Trade-offs

- [BREAKING config: внешний код ждёт `infrastructure.neo4j`] → Mitigation: в репо active use не найден; rollback = git restore config modules.
- [Скрытый import Neo4jConfig останется] → Mitigation: grep после удаления; pyright/import fail на apply.
- [Путаница со stub conftest] → Mitigation: DoD явно запрещает stubs как архитектуру; decision Forbidden.

## Migration Plan

1. Apply: удалить Neo4j из infrastructure config + orphan DI.
2. Прогнать targeted tests (billing module load, DI build, sample shop_menu / wb_shop_run / snapshot factory).
3. Deploy: обычный app rollout; Neo4j env в `.env` становится неиспользуемым приложением (можно оставить в env до later cleanup).
4. Rollback: вернуть удалённые config/DI файлы из git; временно допустимы env stubs только как emergency, не как целевое состояние.
5. Archive: promote decision в `openspec/decisions/neo4j-not-in-runtime-config-di/` со status Accepted.

## Open Questions

- Есть ли вне репозитория потребители `settings.infrastructure.neo4j`? (Owner confirm; в репо — нет.)
- Нужен ли отдельный later change на cluster teardown — да, out of scope здесь.

## Affected components / side effects

- `AppConfig.create()` больше не валидирует Neo4j.
- DI settings singleton и Redis-via-AppConfig пути разблокируются.
- Performance: нейтрально (меньше nested settings validation).
- Access guards / Free-Paid / WB write: не затрагиваются.
- Validation plan: см. tasks — targeted pytest + grep no live Neo4jConfig import.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision _(apply: config/DI placement)_
