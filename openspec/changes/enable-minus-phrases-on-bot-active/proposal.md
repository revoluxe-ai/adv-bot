## Why

Сейчас включение платного управления кампанией через `bot_active=True` не гарантирует включение автообновления минус-фраз: если `auto_update_minus_phrases` был `False`, runner не будет обновлять минус-фразы. Это расходится с ожидаемым paid-start поведением: при включении бота пользователь должен получить активное автообновление минус-фраз без отдельного ручного переключателя.

## What Changes

- При явном включении paid auto-management режима система MUST включать автообновление минус-фраз для этой кампании.
- При переходе в free/manual режим система MUST выключать автообновление минус-фраз как paid WB write automation.
- Включение и выключение `auto_update_minus_phrases` должно применяться декларативно через mode overlay policies, а не прямым присваиванием внутри transition-helper.
- Существующий runtime gate: обновление минус-фраз выполняется когда включён
  `auto_update_minus_phrases` (default false). Фича входит в free-пакет и
  **не** требует `bot_active`; paid-start MAY дополнительно включать флаг.
- Out of scope: изменение алгоритма построения минус-фраз, изменение WB API write-пути, миграции БД, изменение whitelist/ставочных auto-flags.

## Capabilities

### New Capabilities

- `paid-minus-phrases-default`: paid activation contract for automatically enabling minus-phrases updates when bot management is turned on.

### Modified Capabilities

- Нет.

## Impact

Изменение затрагивает paid/free overlay contract для кампаний, тесты перехода FREE/PAID и пользовательское ожидание запуска paid automation. Риск связан с тем, что автообновление минус-фраз является WB write-действием, поэтому поведение должно оставаться ограниченным paid `bot_active=True` режимом и не должно расширять free path. Rollback idea: вернуть overlay policies к прежнему владению флагами и оставить ручное включение через существующий экран настройки минус-фраз.
