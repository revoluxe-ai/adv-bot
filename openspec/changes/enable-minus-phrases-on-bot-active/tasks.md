## 1. Regression Tests

- [x] 1.1 Обновить tests-first ожидание paid overlay: при включении paid auto-management `bot_active=True` и `auto_update_minus_phrases=True`.
- [x] 1.2 Обновить tests-first ожидание free overlay: при выключении paid режима `bot_active=False` и `auto_update_minus_phrases=False`.
- [x] 1.3 Обновить field ownership tests: `auto_update_minus_phrases` входит в mode-specific overlay fields и не входит в common fields.
- [x] 1.4 Добавить или обновить runner-filter тест: кампания с `bot_active=False` и `auto_update_minus_phrases=True` не доходит до автоматического WB write handler для минус-фраз.

## 2. Core Implementation

- [x] 2.1 Убрать прямое присваивание `auto_update_minus_phrases` из paid transition-helper.
- [x] 2.2 Убрать `auto_update_minus_phrases` из common defaults.
- [x] 2.3 Добавить `auto_update_minus_phrases=True` в paid mode overlay policy.
- [x] 2.4 Добавить `auto_update_minus_phrases=False` в free mode overlay policy.
- [x] 2.5 Проверить, что runtime filter минус-фраз по-прежнему требует одновременно paid bot management и включённый minus-phrases flag.

## 3. Documentation And Validation

- [x] 3.1 Добавить или обновить русские docstrings/comments в изменённых тестах и изменённом policy-коде с указанием spec `paid-minus-phrases-default`.
- [x] 3.2 Запустить focused unit tests для default policy, auto-management mode и update-minus-phrases filter.
- [x] 3.3 Запустить `git diff --check`.
