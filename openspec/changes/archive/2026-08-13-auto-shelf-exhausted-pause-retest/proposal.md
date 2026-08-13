## Evolution Context

```text
EVOLUTION_LINK: LINKED
STAR_ID: affordable-auto-pause-on-empty
INCREMENT_ID: INC-AUTO-SHELF-PAUSE-01
KEEP: terminal Auto pause after shelf test exhausted without resolve-CPO fit + retest/clear-our-block + kill mid-cycle cost pause when shelf module ON + distinct reason/notify + proposed ADL; no billing/empty-keywords/1000/comms
HARD: EVOLUTION_SCOPE_DRIFT if artifacts/tasks include OUT_OF_SCOPE or FUTURE_INCREMENTS
FORWARD: clear our block MUST NOT force Auto start when other pause blocks remain; retest/coverage MUST NOT require stats older than 7d; do not mask terminal under empty-keywords or sole cost_rule_failed; coexistence shelves ON → legacy bid path ignored; Hold freeze ≠ stop
```

## Why

Когда «Управление ставкой в полках» включено и тест ставок уже исчерпан, а среди протестированных нет ставки под план при допустимом CPO, Авто-РК всё равно может крутиться вхолостую. Сейчас контроль активности при том же модуле ещё и может поставить Авто на паузу по себестоимости посреди теста — это мешает дотестировать. Нужна честная пауза Авто после исчерпания теста, понятный перетест и снятие только нашего блока причины, без выключения модуля полок.

## What Changes

### Intent

Один результат: при включённом «Управление ставкой в полках» и режиме main bid «Best plan» Авто на WB ставится на паузу только когда эпоха теста исчерпана и нет ставки под текущий resolve CPO; отдельная причина и уведомление; сброс только нашего блока (календарь / кнопка «Сбросить паузу» / тик); mid-cycle cost-пауза при этом модуле выпиливается; модуль полок остаётся включённым.

### Current behavior

- «Управление ставкой в полках» тестирует ставки Авто; coexistence уже фиксирует: при модуле ON старый путь «управление ставкой для Авто» не пишет ставку.
- Empty-keywords паузит Search, не Авто.
- Контроль активности при включённом «Управление ставкой в полках» MAY ставить Авто на паузу по себестоимости (`cost_rule_failed`) посреди цикла теста, если best CPO и факт выше порога.
- Отдельной терминальной причины «тест полок исчерпан / нет ставки под план», durable-отметки эпохи/перетеста, настройки интервала суток и кнопки «Сбросить паузу» для этой причины нет.
- В registry нет accepted decision ownership для shelf terminal write-path (**Architecture Decision Missing** до proposed decision в этом change).

### Desired behavior

- Gate: только «Управление ставкой в полках» ON и main bid «Best plan»; иначе path не трогает.
- Terminal: нет новых ставок по мин. шагу в эпохе AND нет проходных среди квалифицированно протестированных vs текущий resolve CPO (цель, если план закрыт прогнозом; иначе макс — не «всегда только Max»).
- Пауза WB Авто через activity-control с отдельным reason; в учёте/notify видно какой CPO (цель/макс + значение). «Управление ставкой в полках» остаётся включённым.
- Через N суток (настройка в UI полок, default 7) снимается только наш блок паузы; то же при кнопке «Сбросить паузу» и при появлении проходных на тике. Другие блоки (бюджет, расписание, баланс, авария) MAY оставить Авто на паузе. Старт Авто — только если больше нечему держать паузу. Новая эпоха — только когда Авто реально стартует после снятия нашего блока; окно покрытия MUST NOT мгновенно закрывать ставки старой историей (`date_from = max(now-7d, epoch_start)` или эквивалент).
- **BREAKING** (для контура с модулем ON): при включённом «Управление ставкой в полках» контроль активности MUST NOT ставить Авто на паузу по себестоимости mid-cycle (в т.ч. best CPO + факт > target → `cost_rule_failed`). При модуле OFF прежняя cost-пауза сохраняется. Terminal shelf-exhausted MUST NOT маскироваться под единственный durable `cost_rule_failed`.

### Scope in

- Detect terminal + durable reason/отметка + resolve CPO в reason/notify.
- Activity-control: pause Авто; снятие нашего блока; старт только при отсутствии других blockers.
- Настройка интервала перетеста (сутки, default 7); Telegram notify + «Сбросить паузу».
- Выпил mid-cycle cost-паузы при модуле ON.
- Proposed architecture decision: shelf (detect/intent/epoch) → activity-control (pause/start) → Telegram (interval + reset).
- Paired proof: terminal; clear-our-block без форса старта при чужих блоках; epoch при реальном старте; reason distinctness; no mid-cycle cost при модуле ON; coexistence не ломается.

### Scope out

- Fair Auto/Search leg billing, тариф 1000₽, канал-анонс, disconnect, onboarding.
- Empty-keywords Search pause/recheck.
- Retire updater v2.
- Перепись plan_distance / selection math сверх terminal/retest hook.
- Пауза Search или обеих ног из‑за shelf-exhausted.
- Выключение «Управления ставкой в полках» вместо паузы WB Auto.
- Rewrite coexistence bid-module contract.
- Terminal для стратегий main bid кроме «Best plan».

### Risk

- High-risk: WB pause/start Авто, CPO/resolve, БД/durable reason, Telegram, конфликт с budget/schedule/balance.
- Ошибка clear-our-block (форс-старт или наоборот вечная пауза) и смешение terminal reason с `cost_rule_failed` / empty-keywords.
- Без proposed write-path decision change не apply-ready.

### Rollback idea

- Откатить terminal detect/intent, reason, notify, настройки интервала и gate mid-cycle cost; вернуть прежнюю cost-паузу при модуле ON. Coexistence и empty-keywords Search не трогать откатом шире необходимого.

## Capabilities

### New Capabilities

- `auto-shelf-exhausted-pause`: terminal пауза Авто при исчерпании теста полок без ставки под resolve CPO (модуль ON + «Best plan»); clear-our-block / retest / notify / «Сбросить паузу»; выпил mid-cycle cost-паузы при модуле ON; ортогональность к empty-keywords и к coexistence writers.

### Modified Capabilities

- (нет обязательных delta к main requirements) — `auto-bid-module-coexistence` и `pause-on-empty-keywords` остаются действующими контрактами; этот change MUST NOT ломать coexistence и MUST NOT менять Search empty-keywords. Уточнения forward-compat / reason distinctness при необходимости — в design/decision, не как расширение чужого DoD.

## Impact

- Paid automation: lifecycle Авто при «Управление ставкой в полках» (detect → pause/clear block → условный старт → новая эпоха); контроль активности (gate mid-cycle cost при модуле ON); Telegram UX настроек полок (интервал суток, notify, «Сбросить паузу»).
- Architecture: обязателен proposed decision `auto-shelf-exhausted-pause-write-path` (или аналог) в change до implementation-ready; цитировать Accepted `auto-bid-module-coexistence-write-path` и `empty-keywords-pause-write-path` как ортогональные.
- Тесты: paired terminal / clear-our-block / no forced start / epoch on real start / no mid-cycle cost when module ON; Telegram payload limits для новых сообщений/кнопок.
- Free bot MUST NOT получать этот automation write-path как бесплатный core.
