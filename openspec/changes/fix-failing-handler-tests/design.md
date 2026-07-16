## Context

В текущем состоянии unit-тесты упали из-за трёх типов рассинхронизации: устаревшие имена helper-ов в `adv_setting`-пакете, неawaitable `session.begin()` в моках и неполные fixtures для `ComplexAdv`-подобных объектов. Проблема затрагивает два независимых участка кода: client-bot navigation handlers и shop-runner minus-phrase orchestration.

Ограничение этого изменения: не менять paid automation behavior без необходимости и не вводить новую бизнес-логику ради прохождения тестов. Приоритет — восстановить корректность контрактов и тестового сигнала.

## Goals / Non-Goals

**Goals:**
- Синхронизировать unit-тесты с актуальными публичными контрактами handler-слоя.
- Зафиксировать, что `turn_adv_on` использует awaitable session lifecycle.
- Зафиксировать, что minus-phrase batch filtering требует `bot_active` и `auto_update_minus_phrases`.
- Сохранить поведение paid automation core без функциональных изменений.

**Non-Goals:**
- Не пересматривать бизнес-логику включения/выключения кампаний.
- Не добавлять новые WB write-paths.
- Не вводить новые доменные модели или миграции.
- Не расширять public API сверх того, что нужно для совместимости и тестов.

## Decisions

1. **Предпочесть обновление тестов текущему runtime behavior**
   - Почему: падения вызваны в первую очередь устаревшими assumptions в тестах, а не production-regression.
   - Альтернатива: добавить дополнительные compatibility alias-ы в runtime package. Это возможно, но повышает риск разрастания API и маскирует устаревшие call sites.

2. **Использовать awaitable mocks для session lifecycle**
   - Почему: production path уже опирается на `await session.begin()`, и тест должен проверять именно этот контракт.
   - Альтернатива: изменить production code на синхронный `begin()`. Это ухудшит согласованность с async SQLAlchemy usage и не решает root cause.

3. **Сделать fixtures минимально полными, а не "магическими"**
   - Почему: minus-phrase filtering читает `bot_active` напрямую, значит fixture должен содержать это поле. Недостающие атрибуты должны отражаться в тесте явно.
   - Альтернатива: оборачивать все проверки в `getattr(..., default)`. Это меняло бы production semantics и могло бы скрыть реальные ошибки данных.

4. **Оставить runtime contract handler package явным**
   - Почему: navigation handlers и package-level exports являются точкой, на которую опираются unit-тесты и часть UI call sites. Контракт должен быть либо стабильным, либо тесты должны использовать актуальные имена.
   - Альтернатива: менять call sites на старые private-style names. Это неверный вектор для публичного API.

## Risks / Trade-offs

- [Risk] Если где-то ещё используются старые helper names, то простая правка тестов покажет следующие падающие места → [Mitigation] до завершения change проверить call sites и, при необходимости, добавить минимальные compatibility aliases только там, где это оправдано.
- [Risk] Усиление fixture strictness может вскрыть ещё один слой неполных тестовых данных → [Mitigation] добавлять только реально обязательные поля и не раздувать mock-объекты лишними атрибутами.
- [Risk] Команда может ожидать runtime fix вместо test fix → [Mitigation] в proposal и tasks явно разделить test-only work и возможные compatibility adjustments.

## Migration Plan

1. Обновить unit-тесты под текущие helper names и async expectations.
2. Поправить test fixtures для minus-phrase orchestration так, чтобы они отражали обязательные поля доменной модели.
3. Прогнать targeted unit suites по затронутым модулям.
4. Если после этого останутся внешние call sites на старые helper names, добавить минимальную compatibility-обвязку и повторно проверить тесты.
5. Rollback strategy: откатить изменения в тестах/fixtures или, если compatibility-слой будет добавлен, удалить только его без трогания product logic.

## Open Questions

- Нужна ли отдельная compatibility alias-обвязка в `adv_setting` package, или достаточно полностью перевести тесты на актуальные имена helper-ов?
- Есть ли ещё unit suites, которые зависят от того же mock pattern для `session.begin()`?
- Следует ли выделить общую фабрику fixtures для `ComplexAdv`-подобных объектов, чтобы не повторять обязательные поля в нескольких тестах?
