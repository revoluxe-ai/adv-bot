## 1. Контрактная подготовка и границы записи

- [x] 1.1 Подтвердить текущую характеристику графа и выделенной проверки `tests/migrations/test_alembic_heads.py::test_exactly_one_alembic_head`: до реализации единственными исходными terminal revision являются `d1e2f3a4b5c6` и `f2a3b4c5d6e7`; не менять другие тесты или миграции.
- [x] 1.2 Зафиксировать перед записью две и только две разрешённые цели implementation: одна новая revision file в `alembic_/versions/` и единственное ожидаемое значение в `tests/migrations/test_alembic_heads.py`; MUST NOT изменять существующие revision files, ORM-модели, DDL, data-migration или прикладной код.

## 2. Forward-only слияние топологии

- [x] 2.1 Создать ровно одну новую пустую forward-only merge revision в `alembic_/versions/`, с новым сгенерированным идентификатором revision и `down_revision`, содержащим ровно `d1e2f3a4b5c6` и `f2a3b4c5d6e7`.
- [x] 2.2 Оставить `upgrade()` и `downgrade()` новой merge revision без schema- и data-операций; MUST NOT добавлять DDL, миграцию данных или побочную прикладную логику.

## 3. Явный контракт итоговой head

- [x] 3.1 После фиксации идентификатора новой merge revision обновить только ожидаемую итоговую head в `tests/migrations/test_alembic_heads.py::test_exactly_one_alembic_head`, подставив этот идентификатор и не сохраняя ни `d1e2f3a4b5c6`, ни `f2a3b4c5d6e7` как ожидаемую head.
- [x] 3.2 Выполнить только `tests/migrations/test_alembic_heads.py::test_exactly_one_alembic_head`, чтобы подтвердить одну итоговую head и регрессионно защитить инвариант из `alembic-head-convergence`.

## 4. Ограниченная проверка поставки

- [x] 4.1 Выполнить `alembic heads` и убедиться, что команда выводит ровно одну head — идентификатор новой merge revision.
- [x] 4.2 Выполнить `git diff --check`; подтвердить отсутствие whitespace-ошибок, не запускать другие тесты, миграции, деплой, commit, push, PR или архивирование change.

## 5. Lifecycle решения и итоговый inventory записей

- [x] 5.1 Сверить lifecycle change-local решения: `alembic-forward-only-head-convergence` остаётся `Proposed`, пока change активен; implementation conformance подтверждён, promotion в постоянный registry отложен до archive.
- [x] 5.2 Зафиксировать итоговый inventory: implementation — `alembic_/versions/8c541a39b7e2_merge_alembic_heads.py` и `tests/migrations/test_alembic_heads.py`; reconciliation — `decisions/alembic-forward-only-head-convergence/decision.md`, `design.md` и этот `tasks.md`; `WRITE_SCOPE_RECONCILED: yes`. Во время reconciliation product-, migration- и test-файлы не изменялись.
