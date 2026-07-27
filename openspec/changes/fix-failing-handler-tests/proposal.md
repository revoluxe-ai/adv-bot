## Why

Несколько unit-тестов упали не из-за бизнес-логики, а из-за рассинхронизации между текущими контрактами кода и устаревшими тестовыми ожиданиями. Это мешает безопасно вносить изменения в `client_bot` и `shop_runner`, потому что тестовый сигнал сейчас не отражает реальное состояние системы.

## What Changes

- Привести контракт `adv_setting`-handler package к ожидаемому стабильному публичному API для навигационных хендлеров и тестовых патчей.
- Согласовать тестовые моки с актуальным async-поведением `turn_adv_on`, включая awaitable session lifecycle.
- Зафиксировать контракт фильтрации в `update_minus_phrases_in_advs`: обработка возможна только для кампаний, у которых есть и `bot_active`, и `auto_update_minus_phrases`.
- Обновить unit fixtures так, чтобы они отражали реальные обязательные поля доменных объектов.

## Capabilities

### New Capabilities
- `client-bot-handler-compatibility`: стабильный контракт публичного handler package для paid auto-management navigation и совместимости с unit-тестами.
- `shop-runner-minus-phrase-contract`: контракт отбора кампаний для минус-фразового фона на основе `bot_active` и `auto_update_minus_phrases`.

### Modified Capabilities
-

## Impact

Затрагиваются unit-тесты в `client_bot` и `shop_runner`, публичный импортный контракт `app.client_bot.user_interface.handlers.adv_setting`, а также фильтрация кампаний в `shop_runner`-оркестраторе. Изменения не предполагают новых WB write-actions и не меняют продуктовый сценарий paid automation core; цель — восстановить корректность тестового сигнала и зафиксировать реальные контракты.
