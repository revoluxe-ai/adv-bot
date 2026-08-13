## Purpose

Paid automation lifecycle ноги **Авто** при включённом **«Управление ставкой
в полках»** и режиме main bid **«Best plan»**: когда эпоха тестирования ставок
исчерпана и среди квалифицированно протестированных нет ставки под текущий
допустимый (resolve) CPO — пауза Авто на Wildberries с отдельной причиной;
сброс только этого блока паузы (календарь / кнопка «Сбросить паузу» / тик);
пользователю понятно почему и когда перетест. Ортогонально empty-keywords
(Search), coexistence writers ставки и A/B Hold freeze. Free MUST NOT получать
этот write-path как бесплатный automation core.

## ADDED Requirements

### Requirement: Gate — module on and Best plan only

Система MUST применять terminal shelf-exhausted pause/retest path только когда
одновременно включено **«Управление ставкой в полках»** и выбран режим main
bid **«Best plan»**. Если модуль выключен или выбран другой режим main bid,
этот path MUST NOT ставить Авто на паузу по причине исчерпания теста полок и
MUST NOT выставлять соответствующий блок паузы. Это Paid automation write-path;
Free MUST NOT получать это поведение как бесплатный automation core.

#### Scenario: Module off — no shelf-exhausted pause

- **GIVEN** paid кампания с ботом и **«Управление ставкой в полках»** выключено
- **WHEN** наступает условие, которое при включённом модуле считалось бы
  исчерпанием теста без ставки под план
- **THEN** система MUST NOT ставить ногу Авто на паузу по причине
  shelf-exhausted / нет ставки под план из этого path

#### Scenario: Non-Best plan mode — no shelf-exhausted pause

- **GIVEN** paid кампания с ботом, **«Управление ставкой в полках»** включено
  и режим main bid не **«Best plan»**
- **WHEN** эпоха теста могла бы считаться исчерпанной
- **THEN** система MUST NOT применять terminal shelf-exhausted pause path

### Requirement: Terminal Auto pause when test epoch exhausted without plan-fit

Когда **«Управление ставкой в полках»** включено, режим **«Best plan»**, и
одновременно (1) в текущей эпохе тестирования больше нет новых ставок по
минимальному шагу для тестирования и (2) среди квалифицированно
протестированных ставок нет ставки под план при текущем допустимом resolve
CPO, система MUST поставить на паузу на Wildberries ногу **Авто** как
следующий automation write. Resolve CPO MUST быть текущим допустимым CPO из
плана продаж: целевая себестоимость заказа, если прогноз закрывает план;
иначе максимальная себестоимость заказа — MUST NOT использовать «всегда только
Max» как единственный порог. **«Управление ставкой в полках»** MUST остаться
включённым. Нога Search MUST NOT ставиться на паузу этим path.

#### Scenario: Exhausted epoch and no resolve-CPO fit → Auto pause

- **GIVEN** paid кампания, **«Управление ставкой в полках»** ON, **«Best plan»**,
  эпоха теста исчерпана и среди протестированных нет ставки под текущий
  resolve CPO, а нога Авто запущена
- **WHEN** срабатывает terminal shelf-exhausted path (в т.ч. на тике detect)
- **THEN** нога Авто на Wildberries оказывается на паузе
- **AND** **«Управление ставкой в полках»** остаётся включённым

#### Scenario: Already-exhausted on reconcile tick arms Auto pause

- **GIVEN** paid кампания, **«Управление ставкой в полках»** ON, **«Best plan»**,
  эпоха уже исчерпана и среди протестированных нет ставки под текущий
  resolve CPO, нога Авто запущена, и нет свежего producer-события
  (условие уже true до тика)
- **WHEN** на периодическом тике shelf/activity reconcile срабатывает
  terminal shelf-exhausted detect
- **THEN** нога Авто на Wildberries оказывается на паузе с причиной
  shelf-exhausted / нет ставки под план
- **AND** **«Управление ставкой в полках»** остаётся включённым

#### Scenario: Search leg not paused by shelf-exhausted

- **GIVEN** paid авто-настройка с ногами Auto и Search и срабатывает
  shelf-exhausted terminal path
- **WHEN** система применяет паузу по этой причине
- **THEN** нога Search MUST NOT быть поставлена на паузу этим path

#### Scenario: Still have bids to test — no terminal pause

- **GIVEN** paid кампания с **«Управление ставкой в полках»** ON и **«Best plan»**,
  и в эпохе ещё есть ставка для тестирования по минимальному шагу
- **WHEN** выполняется цикл управления ставкой в полках
- **THEN** система MUST NOT ставить Авто на паузу по причине shelf-exhausted

### Requirement: Distinct reason and recorded resolve CPO

Пауза shelf-exhausted MUST иметь отдельную причину активности, отличную от
empty-keywords, расписания, бюджета, баланса и ordinary cost / себестоимость
(`cost_rule_failed` или эквивалент) как единственного durable reason.
Система MUST зафиксировать, какой resolve CPO использовали при решении
(цель или макс и значение). Пользовательский интерфейс MUST показывать
причину и учтённый CPO так, чтобы их нельзя было спутать с паузой по
расписанию, бюджету или обычной себестоимости. При сложности MUST быть
доступна ссылка на поддержку (`const.SUPPORT_LINK` / эквивалент в UX).

#### Scenario: Reason is not masked as cost or empty-keywords

- **GIVEN** нога Авто на паузе по shelf-exhausted / нет ставки под план
- **WHEN** пользователь или система читает причину паузы
- **THEN** причина идентифицируется как отдельная shelf-exhausted / no-plan
  причина, а не как empty-keywords, schedule, budget или единственный
  ordinary cost_rule_failed

#### Scenario: Resolve CPO used for terminal is visible

- **GIVEN** система приняла terminal pause решение по resolve CPO
- **WHEN** пользователь получает уведомление или читает учёт причины
- **THEN** видно, какой допустимый CPO учли (цель или макс и значение)

### Requirement: Clear only our pause block; start only if nothing else blocks

Пока висит блок паузы shelf-exhausted, система MUST на тиках пересчитывать
текущий resolve CPO. Если появились проходные ставки среди протестированных —
система MUST снять только наш блок этой причины (без ожидания полного
календарного интервала) и MUST NOT форсировать старт Авто, если другие блоки
паузы (бюджет, расписание, баланс, авария и т.п.) ещё держат Авто.
Календарный перетест: по истечении заданного числа суток система MUST снять
только наш блок. Кнопка **«Сбросить паузу»** MUST снимать только наш блок
этой причины. Старт Авто на Wildberries MUST происходить только если после
снятия нашего блока больше нечему держать паузу. Новая эпоха тестирования
MUST начинаться только когда Авто **реально** стартует после снятия нашего
блока — MUST NOT считать новый цикл начатым одним лишь clear при чужих
blockers. Окно покрытия новой эпохи MUST NOT мгновенно закрывать ставки
историей до старта эпохи; MUST быть совместимо с окном статистики ≤7 дней
(например нижняя граница окна = максимум из «сейчас минус 7 дней» и старта
эпохи, или эквивалент).

#### Scenario: Calendar due clears our block only

- **GIVEN** Авто на паузе с блоком shelf-exhausted и одновременно активен
  более приоритетный блок (например расписание или бюджет)
- **WHEN** наступает интервал перетеста в сутках
- **THEN** блок shelf-exhausted снят
- **AND** Авто MUST NOT быть принудительно запущено, пока жив другой блок

#### Scenario: Reset pause button clears our block only

- **GIVEN** Авто на паузе с блоком shelf-exhausted и другим активным блоком
- **WHEN** пользователь нажимает **«Сбросить паузу»**
- **THEN** снят только блок shelf-exhausted / нет ставки под план
- **AND** Авто остаётся на паузе из‑за другого блока

#### Scenario: Pass points on tick clear our block without forced start

- **GIVEN** висит блок shelf-exhausted и на тике при текущем resolve CPO
  появились проходные протестированные ставки, при этом есть другой blocker
- **WHEN** система пересчитывает resolve CPO на тике
- **THEN** наш блок снят
- **AND** система MUST NOT форсировать старт Авто вопреки другому blocker

#### Scenario: No fit on tick keeps our pause block

- **GIVEN** висит блок shelf-exhausted, календарный интервал перетеста ещё
  не наступил, и на тике при текущем resolve CPO проходных протестированных
  ставок нет
- **WHEN** система пересчитывает resolve CPO на тике
- **THEN** наш блок shelf-exhausted / нет ставки под план сохраняется
- **AND** система MUST NOT снимать наш блок только из‑за факта тика

#### Scenario: Auto starts and new epoch when only our block held pause

- **GIVEN** Авто на паузе только из‑за блока shelf-exhausted
- **WHEN** блок снят (календарь, кнопка или проходные на тике) и нет других
  blockers
- **THEN** нога Авто MAY быть запущена
- **AND** начинается новая эпоха теста, чьё окно покрытия не считается
  полностью закрытым только историей до старта этой эпохи

### Requirement: Retest interval setting with default seven days

В настройках **«Управление ставкой в полках»** пользователь MUST иметь
возможность задать число суток до календарного снятия нашего блока паузы.
Product default MUST быть 7 суток. Календарный перетест MUST ждать полный
заданный интервал (не стартовать «наш clear» раньше срока только по таймеру).

#### Scenario: Default interval is seven days

- **GIVEN** пользователь включает path без явной смены интервала
- **WHEN** система применяет product default
- **THEN** интервал календарного перетеста равен 7 суткам

### Requirement: Paid notify about pause and next retest

При входе в shelf-exhausted pause paid Telegram UX MUST уведомить
пользователя: почему пауза Авто, какой resolve CPO учли, когда ожидается
следующий календарный перетест; MUST предоставить **«Сбросить паузу»**.
Free MUST NOT получать этот automation write/notify path как бесплатный core.

#### Scenario: Notify explains why and when

- **GIVEN** система ставит Авто на паузу по shelf-exhausted
- **WHEN** отправляется paid уведомление
- **THEN** в сообщении понятны причина, учтённый допустимый CPO и срок
  следующего перетеста
- **AND** доступна кнопка **«Сбросить паузу»**

### Requirement: No mid-cycle cost pause while shelf module is on

Пока **«Управление ставкой в полках»** включено, контроль активности MUST NOT
ставить ногу Авто на паузу по ordinary себестоимости mid-cycle (в т.ч. когда
лучшая ожидаемая CPO и фактическая CPO выше порога) как замену или обход
terminal shelf-exhausted path. Когда **«Управление ставкой в полках»**
выключено, прежняя пауза Авто по себестоимости из контроля активности MAY
сохраняться. Terminal shelf-exhausted MUST NOT маскироваться под единственный
durable ordinary cost reason.

#### Scenario: Shelf module on — mid-cycle cost does not pause Auto

- **GIVEN** **«Управление ставкой в полках»** включено, тест ставок ещё не
  исчерпан (или terminal path не сработал), и показатели себестоимости
  превышали бы порог ordinary cost-паузы
- **WHEN** срабатывает контроль активности по себестоимости
- **THEN** система MUST NOT ставить Авто на паузу ordinary cost reason
  mid-cycle из‑за этого

#### Scenario: Shelf module off — legacy cost pause may apply

- **GIVEN** **«Управление ставкой в полках»** выключено и срабатывают условия
  ordinary cost-паузы Авто
- **WHEN** контроль активности применяет правило себестоимости
- **THEN** Авто MAY быть поставлено на паузу по ordinary cost reason как
  раньше

### Requirement: Coexistence of bid writers remains valid

Этот capability MUST NOT нарушать контракт: когда **«Управление ставкой в
полках»** включено, путь **«управление ставкой для Авто»** MUST NOT успешно
менять ставку Авто. Terminal pause MUST NOT подменять собой этот gate.

#### Scenario: Shelves on — legacy Auto bid path still ignored

- **GIVEN** **«Управление ставкой в полках»** включено и **«управление
  ставкой для Авто»** включено
- **WHEN** срабатывает автоматическое управление ставкой
- **THEN** путь **«управление ставкой для Авто»** MUST NOT успешно изменить
  ставку Авто
