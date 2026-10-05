## Why

Сейчас фактический CPO комплекса Auto + Search может использоваться в leg-level логике как единое значение. Из-за этого ухудшение одной рекламной ноги способно повлиять на управляющее решение другой, хотя её собственная экономика остаётся нормальной.

Изменение нужно, чтобы Auto и Search оценивались независимо по своему фактическому CPO, а пользователь видел оба значения отдельно.

## What Changes

- Ввести раздельную семантику фактического CPO для ноги Auto и ноги Search.
- Leg-level управляющая логика Auto должна использовать CPO Auto; Search/keyword logic должна использовать CPO Search.
- Общий CPO комплекса не должен использоваться как скрытый fallback для решения конкретной ноги.
- В paid-интерфейсе кампании отдельно показывать CPO Auto и CPO Search.
- Сохранить существующие Target/Max CPO и общую plan/fact экономику комплекса вне тех мест, где требуется leg-level факт.
- Добавить paired regression: плохая экономика одной ноги не должна сама по себе ухудшать управляющее состояние второй.

### Current behavior

Фактический plan/fact CPO собирается на уровне комплекса и может включать статистику обеих связанных РК. Этот факт прокидывается в runtime DTO и используется несколькими Auto/Search consumers.

### Desired behavior

Каждый consumer, принимающий решение за конкретную рекламную ногу, получает фактический CPO этой же ноги. UI показывает те же leg-level значения, которые используются управляющей логикой.

### Scope

В scope: расчёт/read-model leg-level CPO, передача его Auto/Search consumers, paid UI отображение и regression tests.

### Out of scope

Не меняются бюджетная архитектура, создание/связывание РК, Target/Max CPO, attribution Wildberries, free/paid access model и unrelated automation.

### Risk

Основной риск — скрытый consumer старого общего `fact_pay_for_order`, который продолжит принимать leg-level решение по общей экономике, либо неверное деление статистики Auto/Search.

### Rollback idea

Откат ограничивается новыми leg-level read fields/резолверами и переключёнными consumers; существующий общий plan/fact CPO сохраняется как отдельная метрика и не удаляется.

## Capabilities

### New Capabilities

- `leg-cpo-economics`: раздельный фактический CPO Auto/Search, ownership его consumers и отображение обоих значений в интерфейсе.

### Modified Capabilities

Нет.

## Impact

Затрагиваются runtime economics DTO/read-path, Auto/Search управляющие consumers, ClickHouse-derived рекламная статистика и paid UI кампании. Внешние WB write API, схема рекламных кампаний и зависимости проекта не меняются.
