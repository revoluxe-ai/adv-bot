## 1. Regression Tests

- [ ] 1.1 Обновить tests-first ожидание paid transition: при включении paid auto-management `bot_active=True` и `auto_update_minus_phrases=True`.
- [ ] 1.2 Добавить или обновить тест, который фиксирует сохранение `auto_update_minus_phrases=True` при выключении paid режима.
- [ ] 1.3 Добавить или обновить runner-filter тест: кампания с `bot_active=False` и `auto_update_minus_phrases=True` не доходит до автоматического WB write handler для минус-фраз.

## 2. Core Implementation

- [ ] 2.1 Изменить paid activation transition так, чтобы он устанавливал `auto_update_minus_phrases=True` вместе с `bot_active=True`.
- [ ] 2.2 Оставить common defaults и free transition без принудительного включения или сброса `auto_update_minus_phrases`.
- [ ] 2.3 Проверить, что runtime filter минус-фраз по-прежнему требует одновременно paid bot management и включённый minus-phrases flag.

## 3. Documentation And Validation

- [ ] 3.1 Добавить или обновить русские docstrings/comments в изменённых тестах и изменённом transition-коде с указанием spec `paid-minus-phrases-default`.
- [ ] 3.2 Запустить focused unit tests для default policy, auto-management mode и update-minus-phrases filter.
- [ ] 3.3 Запустить `git diff --check`.
