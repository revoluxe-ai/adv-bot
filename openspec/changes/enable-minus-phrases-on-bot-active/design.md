## Context

Paid activation сейчас проходит через общий transition-helper, который включает `bot_active` и применяет paid overlay. Common defaults для новой кампании выставляют `auto_update_minus_phrases=False`, а paid overlay не меняет это поле. Runtime updater минус-фраз дополнительно фильтрует кампании по двум условиям: paid activation flag и feature flag автообновления минус-фраз.

Это write-path в WB, поэтому изменение должно оставаться внутри paid activation contract и не должно расширять free runtime доступ. Существующий ручной экран минус-фраз и сам алгоритм обновления минус-фраз не меняются.

## Goals / Non-Goals

**Goals:**

- Сделать paid activation самодостаточной: при включении `bot_active=True` в paid transition одновременно включается `auto_update_minus_phrases=True`.
- Сохранить runtime guard: фактическое обновление минус-фраз выполняется только для кампаний, где активны оба флага.
- Зафиксировать поведение тестами на transition-helper и на runner filter.
- Не затрагивать БД-схему и миграции.

**Non-Goals:**

- Не менять алгоритм генерации или отправки минус-фраз в WB.
- Не включать автообновление минус-фраз во Free режиме.
- Не менять вручную управляемый toggle минус-фраз, кроме совместимости с новым paid-start default.
- Не менять bidder, whitelist, target-place, budget watchdog или другие auto-flags.

## Decisions

1. Включать `auto_update_minus_phrases` в paid transition, а не в common defaults.

   Rationale: common defaults применяются к новым кампаниям и не должны бесплатно включать WB write automation. Paid transition уже является явным переходом в paid auto-management, поэтому это правильная граница для включения write-feature.

   Alternative considered: поменять common default на `True`. Отклонено, потому что это может включить write-feature до явного paid activation и размыть Free/Paid boundary.

2. Не сбрасывать `auto_update_minus_phrases` в free transition.

   Rationale: текущий контракт уже сохраняет пользовательское значение при выключении paid режима, а runtime gate всё равно требует `bot_active=True`. Это снижает churn и позволяет восстановить paid behavior при повторном включении.

   Alternative considered: на free transition принудительно ставить `False`. Отклонено как лишнее изменение поведения и потенциальная потеря пользовательской настройки.

3. Оставить runner filter с двумя условиями.

   Rationale: paid transition должен подготовить feature flag, но runtime write-path должен оставаться защищённым локальным guard-ом. Это не даёт минус-фразам обновляться для `bot_active=False`, даже если feature flag остался включён.

   Alternative considered: полагаться только на выборку `only_bot_active=True`. Отклонено, потому что локальный guard яснее фиксирует WB write safety invariant.

## Risks / Trade-offs

- [Risk] При включении paid режима начнут обновляться минус-фразы у кампаний, где раньше пользователь не включал этот toggle вручную. → Mitigation: зафиксировать это как новый desired paid-start contract и оставить out of scope изменение алгоритма/частоты обновления.
- [Risk] Изменение может случайно расширить Free write-path. → Mitigation: тест должен явно проверять, что runner не обрабатывает `bot_active=False` даже при `auto_update_minus_phrases=True`.
- [Risk] Существующие тесты ожидают старое значение `False` после common plus paid defaults. → Mitigation: обновить ожидания только в тестах paid transition, не менять unrelated defaults.

## Migration Plan

1. Изменить paid transition contract так, чтобы он устанавливал `auto_update_minus_phrases=True`.
2. Обновить focused unit tests для default policy и auto-management mode.
3. Проверить runner filter тестами, чтобы free/inactive кампании не доходили до WB write handler.
4. Rollback: вернуть paid transition к сохранению старого значения `auto_update_minus_phrases`; тесты paid-start expectation вернуть к старому контракту.

## Open Questions

- Нужно ли дополнительно менять текст UI при включении бота, чтобы пользователь видел, что минус-фразы теперь включаются автоматически? Для текущего change это не обязательно и может быть отдельным UX proposal.
