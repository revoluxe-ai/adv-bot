## Why

Сейчас включение платного управления кампанией через `bot_active=True` не гарантирует включение автообновления минус-фраз: если `auto_update_minus_phrases` был `False`, runner не будет обновлять минус-фразы. Это расходится с ожидаемым paid-start поведением: при включении бота пользователь должен получить активное автообновление минус-фраз без отдельного ручного переключателя.

## What Changes

- При явном включении paid auto-management режима система MUST включать автообновление минус-фраз для этой кампании.
- При выключении paid режима система MUST NOT принудительно сбрасывать существующее значение автообновления минус-фраз.
- Существующий runtime gate должен остаться строгим: обновление минус-фраз выполняется только когда включены и `bot_active`, и `auto_update_minus_phrases`.
- Out of scope: изменение алгоритма построения минус-фраз, изменение WB API write-пути, миграции БД, изменение free-mode runtime доступа, изменение whitelist/ставочных auto-flags.

## Capabilities

### New Capabilities

- `paid-minus-phrases-default`: paid activation contract for automatically enabling minus-phrases updates when bot management is turned on.

### Modified Capabilities

- Нет.

## Impact

Изменение затрагивает paid activation contract для кампаний, тесты перехода FREE/PAID и пользовательское ожидание запуска paid automation. Риск связан с тем, что автообновление минус-фраз является WB write-действием, поэтому поведение должно оставаться ограниченным paid `bot_active=True` режимом и не должно расширять free path. Rollback idea: вернуть paid transition к сохранению старого значения `auto_update_minus_phrases` и оставить ручное включение через существующий экран настройки минус-фраз.
