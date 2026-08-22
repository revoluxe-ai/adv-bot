## Why

В ClickHouse-запросах приложения имя базы MUST присутствовать в тексте SQL
(квалификация `database.table`). Для текущего рабочего контура это
`default_db` (например `default_db.<table>`). Недавние правки под injectable
test seam сняли этот prefix у отдельных запросов; без имени БД в query
запрос не считается корректным для рабочего контура. Нужно исправить
текущий регресс, найти аналогичные дыры того же класса и закрепить паттерн
«DB в тексте CH query» для текущего change. (Имя каталога change
историческое; intent — не «убрать DB из queries», а вернуть/удержать
квалификацию.)

## What Changes

**Intent:** восстановить и закрепить обязательную квалификацию database в
тексте ClickHouse SQL для затронутых и однотипных регрессий; не менять
продуктовую семантику агрегатов, только корректность адресации БД в query.

**Current behavior:** часть CH SQL (в т.ч. после seam-правок) обращается к
таблицам/MV без database-prefix в тексте запроса, полагаясь на session
database клиента. Рабочий контур ожидает явное имя БД в SQL.

**Desired behavior:** такие CH queries MUST содержать явную квалификацию
database в тексте SQL — для текущего prod-контура `default_db`
(например `default_db.<table>`). Аналогичные снятия prefix того же класса
MUST быть найдены и исправлены в границах change. Тесты MUST доказывать
наличие квалификации в issued SQL (не заменять proof полным mock функции,
чей SQL меняли).

**Scope in:**
- исправление текущего бага (отсутствие DB в CH query);
- поиск и точечное исправление аналогичных CH SQL без database-prefix
  (тот же класс регрессии);
- закрепление паттерна в specs/design этого change;
- proof-тесты на наличие DB в тексте CH query.

**Scope out:**
- перевод имени CH БД на env / `client.database` как единственный резолвер;
- массовый рефакторинг всех CH SQL readers «под unqualified» или «под env»;
- reusable Architecture Decision Registry про env-политику CH DB (отдельный
  follow-up / WORKLOG park после bound-scope GO при необходимости);
- изменение бизнес-логики CTR/keyword boost, кроме восстановления корректного
  CH SQL addressing.

**Risk:** ошибочная квалификация на несуществующую БД → ошибки CH runtime;
пропуск аналогичных мест → повторный регресс. Снижение: hunt по тому же
паттерну + SQL-contract unit до live.

**Rollback idea:** вернуть предыдущий квалифицированный SQL на затронутых
запросах; откатить только qualification-правки без затрагивания несвязанной
бизнес-логики.

## Capabilities

### New Capabilities

- `clickhouse-query-database-qualification`: требования к явной квалификации
  database в тексте ClickHouse SQL; запрет считать «голый» table name
  допустимым для рабочего CH query path в рамках этого паттерна; proof через
  проверку issued SQL.

### Modified Capabilities

- (нет) — в `openspec/specs/` нет существующего capability с требованиями к
  квалификации CH SQL; `local-dev-db-connectivity` не меняется.

## Impact

- Read-path ClickHouse: запросы статистики/агрегатов, где prefix был снят или
  отсутствует; поведение для пользователя — корректное чтение той же рабочей
  CH БД, без смены бизнес-формул.
- Тестовый контур: unit на SQL-contract; destructive/live CH — по существующим
  gate'ам проекта, не ослабляя правило «DB в тексте query».
- Process: согласовать с уже принятыми guardrail'ами
  `SQL_REWRITE` / `SQL_REWRITE_MOCKED_AWAY` (mock rewritten SQL producer ≠ proof).
- Имя change-каталога может вводить в заблуждение при review — в артефактах
  всегда повторять фактический intent.
