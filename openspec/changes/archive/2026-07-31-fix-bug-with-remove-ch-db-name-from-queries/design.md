## Context

В рабочем ClickHouse-контуре приложение ходит в БД `default_db`
(`app/utils/click_house/client.py`). Недавние правки под injectable test seam
сняли database-prefix из текста отдельных CH SQL (в т.ч.
`get_keyword_statistic_clickhouse` → `FROM mv_clusters_daily_agg`), полагаясь
на session `client.database`. Для текущего рабочего контура запрос без имени
БД в тексте SQL считается некорректным.

Имя change-каталога историческое: intent — **вернуть/удержать** квалификацию
`default_db.` в CH SQL, а не убрать DB из queries. Env-резолв имени БД и
массовый unqualify всех readers вынесены в WORKLOG park (bound-scope GO).

## Goals / Non-Goals

**Goals:**
- Восстановить явную квалификацию `default_db.<object>` в затронутых CH SQL.
- Найти и точечно исправить однотипные снятия prefix того же класса.
- Закрепить SQL-contract unit proof на issued SQL (не полный mock producer'а).
- Согласовать placement с proposed decision этого change.

**Non-Goals:**
- Env / `client.database` как единственный резолвер имени CH БД.
- Массовый рефакторинг всех CH readers под unqualified или под env.
- Изменение бизнес-формул CTR/keyword aggregates.
- Принятие reusable env-политики CH DB в registry (отдельный follow-up).

## Architecture Decision References

**Accepted registry:**
- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — не закрывает
  CH SQL qualification (defaults ownership only).

**Architecture Decision Missing → proposed in this change:**
- `openspec/changes/fix-bug-with-remove-ch-db-name-from-queries/decisions/clickhouse-sql-database-qualification/decision.md`
  — domain invariant: CH SQL MUST содержать `default_db.` в тексте запроса
  для рабочего контура; proof через issued SQL.

## Ownership & Placement

| Concern | Owner layer | Forbidden |
|--------|-------------|-----------|
| Текст CH SQL / qualification | application query owners (`data_manager` и аналогичные CH readers; `sql/` файлы сервисов) | «чинить» только в test mock без правки issued SQL |
| Session `client.database` | CH client factory (`app/utils/click_house/client.py`) | считать session DB заменой qualification в SQL text |
| SQL-contract proof | unit tests, перехватывающие issued SQL / параметры query | полный mock функции, чей SQL меняли (`SQL_REWRITE_MOCKED_AWAY`) |
| Env / mass unqualify policy | out of scope (WORKLOG park) | внедрять в этом change |

Placement matches proposed decision: qualification живёт в SQL text у query
owner; seam/test не снимает prefix без contract proof.

## Decisions

1. **Квалифицировать `default_db.` в тексте SQL, не полагаться на session DB**
   - Почему: рабочий контур и владелец требуют имя БД в query; session DB —
     вспомогательный факт клиента, не контракт addressing.
   - Альтернатива: unqualified + `client.database` — отвергнута (scope out /
     park).

2. **Точечный hunt того же класса, не массовый rewrite**
   - Почему: снизить риск ложных правок и смешения с deferred env-политикой.
   - Альтернатива: пройти все CH readers и унифицировать — out of scope.

3. **SQL_CONTRACT_UNIT на issued SQL**
   - Почему: process guardrails уже запрещают mock rewritten producer как proof.
   - Альтернатива: только destructive live CH — недостаточно как единственный
     gate до merge; live остаётся optional по существующим gate'ам.

4. **Не менять агрегатные формулы**
   - Почему: баг — addressing, не CTR math; rollback проще.

5. **Docstring/комментарии синхронизировать с фактом qualification**
   - Почему: текущий docstring утверждает unqualified-by-design; после fix
     должен отражать `default_db.` в SQL.

## Risks / Trade-offs

- [Risk] Квалификация на несуществующую БД → CH runtime error →
  [Mitigation] канон `default_db` подтверждён client + DevOps; не вводить
  другие имена в этом change.
- [Risk] Пропуск аналогичных мест → повторный регресс → [Mitigation] bounded
  hunt по снятому `default_db.` / `FROM <mv|table>` без prefix в CH paths.
- [Risk] Тест мокает всю функцию → false green → [Mitigation] SQL-contract
  на issued SQL; запрет `SQL_REWRITE_MOCKED_AWAY`.
- [Risk] Имя change вводит reviewer в заблуждение → [Mitigation] в артефактах
  и PR явно повторять intent «вернуть qualification».

## Migration Plan

1. Apply: восстановить `default_db.` в known regression path
   (`get_keyword_statistic_clickhouse` / аналоги из hunt).
2. Добавить/обновить SQL-contract unit.
3. Targeted `pytest -m unit` по затронутому модулю + `pyright-strict` при
   затронутых типах.
4. Rollback: вернуть предыдущий квалифицированный SQL на затронутых запросах
   без отката несвязанной бизнес-логики.

## Open Questions

- Нет блокирующих: имя рабочей БД (`default_db`) и KEEP-паттерн зафиксированы
  proposal + proposed decision. Список «однотипных» мест уточняется hunt-задачей
  на apply.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
