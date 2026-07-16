## Context

Paid activation сейчас проходит через общий transition-helper, который включает `bot_active` и применяет paid overlay. Common defaults для новой кампании выставляют `auto_update_minus_phrases=False`, а paid overlay не меняет это поле. Runtime updater минус-фраз дополнительно фильтрует кампании по двум условиям: paid activation flag и feature flag автообновления минус-фраз.

В этом модуле уже есть декларативная граница ответственности: transition-helper управляет `bot_active`, а mode overlays через `FieldPolicy` управляют настройками режима. Поэтому `auto_update_minus_phrases` должен жить в paid/free overlay policies рядом с остальными mode-specific auto-flags, а не присваиваться напрямую в transition-helper.

Это write-path в WB, поэтому изменение должно оставаться внутри paid activation contract и не должно расширять free runtime доступ. Существующий ручной экран минус-фраз и сам алгоритм обновления минус-фраз не меняются.

## Goals / Non-Goals

**Goals:**

- Сделать paid activation самодостаточной: при применении paid overlay включается `auto_update_minus_phrases=True`.
- Сделать free transition явным: при применении free overlay выключается `auto_update_minus_phrases=False`.
- Сохранить архитектурную границу: transition-helper переключает `bot_active`, mode overlays декларативно применяют mode-specific fields.
- Сохранить runtime guard: фактическое обновление минус-фраз выполняется только для кампаний, где активны оба флага.
- Зафиксировать поведение тестами на transition-helper и на runner filter.
- Не затрагивать БД-схему и миграции.

**Non-Goals:**

- Не менять алгоритм генерации или отправки минус-фраз в WB.
- Не включать автообновление минус-фраз во Free режиме.
- Не менять вручную управляемый toggle минус-фраз вне режима применения FREE/PAID overlays.
- Не менять bidder, whitelist, target-place, budget watchdog или другие auto-flags.

## Architecture Decision References

Architecture Decisions Found:

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — Status: Accepted. Решение применимо к этому change, потому что `auto_update_minus_phrases` становится mode-specific default и должен принадлежать paid/free overlay policies, а не transition-helper или common defaults.

Architecture Decision Missing: нет. Accepted decision уже разрешает ownership/layering для mode defaults и WB-impacting automation flags, поэтому proposed decision artifact для этого change не нужен.

## Ownership & Placement

Owner layer:

- `PaidModeDefaultsPolicy` владеет paid-only значением `auto_update_minus_phrases=True`.
- `FreeModeDefaultsPolicy` владеет free-only значением `auto_update_minus_phrases=False`.
- `CommonModeDefaultsPolicy` не владеет `auto_update_minus_phrases`, потому что поле теперь различается между режимами.
- Transition-helper остаётся orchestration layer: переключает `bot_active` и применяет overlay, но не присваивает mode-specific defaults напрямую.
- Runner/service write-path сохраняет локальный guard: минус-фразы обновляются только когда одновременно включены `bot_active` и `auto_update_minus_phrases`.

Allowed layers: declarative mode overlay policies для значений по умолчанию, transition-helper для применения overlay, runner filter для защиты WB write-path.

Forbidden layers: прямое присваивание mode-specific default в transition-helper, UI handlers, menu builders, runners или background services; ownership этого флага в common defaults; удаление runtime guard-а для WB write-path.

Rationale: placement следует accepted decision `mode-defaults-policy-ownership`: mode-specific defaults должны жить в декларативных policy overlays, а write-path остаётся защищённым runtime guard-ом.

## Decisions

1. Включать `auto_update_minus_phrases` в `PaidModeDefaultsPolicy`, а не прямым присваиванием в transition-helper.

   Rationale: paid overlay уже является декларативным местом для paid mode fields. Transition-helper должен оставаться orchestration layer: поставить `bot_active=True` и применить policy. Это сохраняет единый механизм применения mode defaults и не разносит правила по двум слоям.

   Alternative considered: оставить прямое присваивание в transition-helper. Отклонено, потому что это обходит существующий `FieldPolicy` contract и делает флаг исключением среди mode-specific auto-flags.

2. Выключать `auto_update_minus_phrases` в `FreeModeDefaultsPolicy`.

   Rationale: автообновление минус-фраз является paid WB write automation. Free overlay уже выключает paid automation flags, поэтому этот флаг должен быть частью той же декларативной группы.

   Alternative considered: сохранять значение флага при выключении paid режима и полагаться только на runtime `bot_active` gate. Отклонено, потому что mode overlay должен отражать фактический режим, а free defaults должны выключать paid automation.

3. Убрать `auto_update_minus_phrases` из common defaults.

   Rationale: common defaults не должны владеть полем, которое теперь различается между FREE и PAID overlays. Это также сохраняет disjoint contract между common fields и mode-specific fields.

   Alternative considered: оставить common default `False` и добавить paid override `True`. Отклонено, потому что это вводит overlap между common и paid policies и ломает текущую модель field ownership.

4. Оставить runner filter с двумя условиями.

   Rationale: mode overlay готовит feature flag, но runtime write-path должен оставаться защищённым локальным guard-ом. Это не даёт минус-фразам обновляться для `bot_active=False`, даже если feature flag включён из старых данных или ручного toggle.

   Alternative considered: полагаться только на выборку `only_bot_active=True`. Отклонено, потому что локальный guard яснее фиксирует WB write safety invariant.

## Risks / Trade-offs

- [Risk] При включении paid режима начнут обновляться минус-фразы у кампаний, где раньше пользователь не включал этот toggle вручную. → Mitigation: зафиксировать это как новый desired paid-start contract и оставить out of scope изменение алгоритма/частоты обновления.
- [Risk] При выключении paid режима free overlay сбросит флаг, который раньше мог сохраняться. → Mitigation: это соответствует Free/Paid boundary; повторное включение paid режима снова выставит флаг через paid overlay.
- [Risk] Изменение может случайно расширить Free write-path. → Mitigation: тест должен явно проверять, что runner не обрабатывает `bot_active=False` даже при `auto_update_minus_phrases=True`.
- [Risk] Существующие тесты ожидают `auto_update_minus_phrases` в common policy field-set. → Mitigation: обновить field ownership tests так, чтобы поле было mode-specific и disjoint от common.

## Migration Plan

1. Перенести ownership `auto_update_minus_phrases` из common defaults в free/paid overlay policies.
2. В paid overlay выставлять `auto_update_minus_phrases=True`; в free overlay выставлять `False`.
3. Убрать прямое присваивание этого флага из transition-helper.
4. Обновить focused unit tests для policy field ownership, default policy, auto-management mode и runner filter.
5. Rollback: вернуть прежнее владение флагом в common defaults и убрать field policies из mode overlays.

## Open Questions

- Нужно ли дополнительно менять текст UI при включении бота, чтобы пользователь видел, что минус-фразы теперь включаются автоматически? Для текущего change это не обязательно и может быть отдельным UX proposal.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing
- [x] implementation layer matches decision
