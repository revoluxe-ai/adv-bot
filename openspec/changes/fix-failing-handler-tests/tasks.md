## 1. Client-bot handler regression tests

- [ ] 1.1 Обновить `test_auto_management_landing_handlers.py` под актуальные имена helper-ов и current package API из `adv_setting`, чтобы патчи попадали в реальные точки расширения.
- [ ] 1.2 Исправить `test_turn_adv_on_read_only_token.py`, заменив sync-mock для `session.begin()` на awaitable mock и выровняв assertions под async session lifecycle.
- [ ] 1.3 Сверить тестовые ожидания по landing/how-it-works/back navigation: оставить проверку неизменности `bot_active` и безопасных runtime errors без изменения продуктовой логики.

## 2. Shop-runner minus-phrase contract regression test

- [ ] 2.1 Обновить fixtures в `test_update_minus_phrases_filter.py`, добавив обязательный `bot_active` и другие минимально необходимые поля для `ComplexAdv`-подобного объекта.
- [ ] 2.2 Зафиксировать в тесте, что в background sync попадают только кампании, которые одновременно активны и включают `auto_update_minus_phrases`.
- [ ] 2.3 Проверить, что невалидные или неактивные кампании не попадают в minus-phrase updater path.

## 3. Verification and compatibility check

- [ ] 3.1 Прогнать targeted pytest по трём затронутым unit suites и подтвердить, что исходные падения устранены.
- [ ] 3.2 Если после обновления тестов останутся внешние call sites на устаревшие helper names, либо перевести их на актуальный API, либо добавить минимальную compatibility-обвязку только там, где это действительно необходимо.
- [ ] 3.3 Зафиксировать итог проверки в change summary и убедиться, что вносились только тестовые и точечные compatibility изменения без изменения paid automation behavior.
