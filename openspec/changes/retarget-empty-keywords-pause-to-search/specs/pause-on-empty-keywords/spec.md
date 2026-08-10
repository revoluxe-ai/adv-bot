## MODIFIED Requirements

### Requirement: Pause campaign after last keyword off by bot

На paid автокампании с активным ботом выключение ключей — **текущий** шаг
автоматики. Когда после такого выключения выключать больше нечего (активных
ключей не остаётся), система MUST поставить на паузу на Wildberries **ногу
Search** того же комплекта авто-настройки как **следующий** шаг — после
завершения OFF, не в том же шаге, что выключение ключа, и не вместо OFF.
Система MUST NOT ставить на паузу ногу Auto по причине empty-keywords.
Остальная логика выбора и ставок ключей MUST NOT меняться этим требованием
за пределами этого упорядоченного перехода к паузе Search. Это Paid
automation write-path; Free MUST NOT получать это поведение как бесплатный
automation core.

#### Scenario: Nothing left to turn off → Search pause is next step

- **GIVEN** paid авто-настройка с ботом, ногой Search и ровно одним активным ключом
- **WHEN** автоматика завершает выключение этого последнего активного ключа (текущий шаг = OFF)
- **THEN** система ставит ногу Search на паузу на Wildberries как следующий шаг после OFF, а не как часть текущего шага выключения ключа

#### Scenario: Auto leg is not paused for empty-keywords

- **GIVEN** paid авто-настройка с ботом, ногами Auto и Search, и срабатывает empty-keywords pause path
- **WHEN** система применяет паузу по причине empty-keywords
- **THEN** нога Auto MUST NOT быть поставлена на паузу этим path, а нога Search MUST быть на паузе (если Search присутствует и была активна)

#### Scenario: Pause is not concurrent with keyword off

- **GIVEN** paid автокампания с ботом, где автоматика выключает последний активный ключ
- **WHEN** выполняется текущий шаг выключения ключа
- **THEN** pause ноги Search MUST NOT считаться тем же текущим шагом, что OFF ключа

#### Scenario: Non-empty keyword set does not trigger empty-keywords pause

- **GIVEN** paid автокампания с ботом и двумя активными ключами
- **WHEN** автоматика выключает только один из них и остаётся хотя бы один активный ключ (выключать ещё есть что)
- **THEN** система MUST NOT ставить ногу Search на паузу по причине empty-keywords

### Requirement: Distinct pause reason for empty keywords

Пауза из-за отсутствия активных ключей MUST иметь отдельную причину
активности со значением empty-keywords (или эквивалент «нет активных ключей»),
отличную от бюджета, лимитов расхода, расписания показов и insufficient
balance. Причина MUST относиться к паузе **ноги Search** для этого path.
Пользовательский интерфейс MUST показывать эту причину так, чтобы её нельзя
было спутать с паузой по расписанию или бюджету.

#### Scenario: Reason is not masked as schedule or budget

- **GIVEN** нога Search поставлена на паузу из-за отсутствия активных ключей после действий бота
- **WHEN** пользователь или система читает причину паузы
- **THEN** причина идентифицируется как empty-keywords (или эквивалент «нет активных ключей»), а не как schedule/budget/cost/balance

### Requirement: Periodic recheck while paused for empty keywords

Пока нога Search на паузе по причине empty-keywords, система MUST периодически
снова запускать **ту же ногу Search** и перепроверять возможность работы
автоматики. Recheck MUST NOT считаться выполненным, если запущена только нога
Auto, а Search остаётся на паузе исключительно из-за empty-keywords. Если
после перепроверки активных ключей снова нет, система MUST снова поставить
ногу Search на паузу с той же причиной empty-keywords. Более приоритетные
причины паузы Search (расписание, бюджет, баланс) MUST NOT быть тихо
перезаписаны так, будто empty-keywords их отменяет.

#### Scenario: Recheck resumes Search then re-pauses when still empty

- **GIVEN** нога Search на паузе по empty-keywords и интервал перепроверки наступил
- **WHEN** система выполняет перепроверку и активных ключей по-прежнему нет
- **THEN** нога Search снова оказывается на паузе с причиной empty-keywords

#### Scenario: Recheck allows continue when keywords become active

- **GIVEN** нога Search на паузе по empty-keywords
- **WHEN** система выполняет перепроверку и автоматика снова имеет хотя бы один активный ключ без нарушения других pause-правил Search
- **THEN** нога Search MUST NOT оставаться на паузе исключительно из-за устаревшего empty-keywords состояния

#### Scenario: Auto-only start does not satisfy empty-keywords recheck

- **GIVEN** нога Search на паузе по empty-keywords
- **WHEN** система запускает только ногу Auto, не запуская Search
- **THEN** это MUST NOT считаться выполненной перепроверкой empty-keywords для ноги Search

### Requirement: User notification on empty-keywords pause

При входе в паузу по empty-keywords система MUST уведомить **всех**
пользователей, связанных с магазином через `WBUserCabinet` и имеющих
непустой `user.user_telegram_id` (тот же recipient resolution, что
`get_wb_user_cabinets_for_shop` / `load_telegram_chat_ids_for_shop`;
семантика «all users of a shop» как у token `NotificationManager`).
Система MUST NOT ограничивать доставку одним «primary» получателем, если
у магазина несколько таких Telegram chat_id.

Сообщение MUST быть понятным: кампания (Search-нога) на паузе из-за
отсутствия активных ключей после работы бота, и будет периодическая
перепроверка. Сообщение MUST укладываться в лимиты Telegram Bot API. Если
указывается помощь поддержки, MUST использоваться существующий
`SUPPORT_LINK` администратора, без нового канала поддержки в этом change.

Debounce once-per-enter (эпизод / adv) остаётся: система MUST пытаться
доставить **всем** resolved chat_id; debounce-ключ MUST сохраняться, если
доставка подтверждена **хотя бы одному** получателю; если ни одному не
доставлено — debounce MUST быть снят, чтобы повтор в том же окне мог
доставить. Частичный failure (часть chat_id False) при хотя бы одном
успехе MUST NOT снимать debounce.

#### Scenario: User is informed about pause and recheck

- **GIVEN** кампания впервые переходит в паузу по empty-keywords в данном эпизоде
  и у магазина есть хотя бы один shop-linked пользователь с Telegram chat_id
- **WHEN** пауза применена
- **THEN** каждый такой resolved получатель получает сообщение с причиной
  (нет активных ключей) и упоминанием периодической перепроверки

#### Scenario: Multi-recipient fanout to all shop-linked Telegram users

- **GIVEN** paid авто-настройка с ботом, empty-keywords Search pause впервые
  применяется в эпизоде, и у `shop_id` два (или более) `WBUserCabinet` с
  различными непустыми `user.user_telegram_id`
- **WHEN** система выполняет notify empty-keywords pause
- **THEN** `send_message` MUST быть вызван для **каждого** такого chat_id
  (не только для одного), с тем же текстом причины + перепроверки

### Requirement: User notification on empty-keywords resume/re-enable

После **доставленного** empty-keywords pause notify (эпизод входа в паузу
по empty-keywords), когда нога Search / keywords **возобновляются или
снова включаются** после этого pause episode (recheck Search start с
активными ключами, либо эквивалентный resume/re-enable той же Search-ноги
после empty-keywords pause), система MUST уведомить пользователей о
возобновлении.

Получатели MUST совпадать с recipient scope pause notify: **все**
пользователи, связанные с магазином через `WBUserCabinet` и имеющие
непустой `user.user_telegram_id` (тот же resolution, что
`get_wb_user_cabinets_for_shop` / `load_telegram_chat_ids_for_shop`;
Owner `B_MUST_NOTIFY_ALL_SHOP_LINKED_USERS`).

Сообщение resume/re-enable MUST быть **отличным** от:
1. pause-entry notify (причина «нет активных ключей» + вход в паузу);
2. упоминания периодической перепроверки **внутри** pause-entry текста
   (recheck-mention в pause message ≠ отдельный resume notify).

Сообщение MUST укладываться в лимиты Telegram Bot API. Если указывается
помощь поддержки, MUST использоваться существующий `SUPPORT_LINK`.
Система MUST NOT считать pause-entry notify или recheck-mention достаточным
замещением resume/re-enable notify.

#### Scenario: User is informed when Search resumes after empty-keywords pause notify

- **GIVEN** в данном эпизоде уже доставлен empty-keywords pause notify
  хотя бы одному shop-linked получателю, и затем Search/keywords
  resume или re-enable после этой паузы (активные ключи / Search start
  после empty-keywords pause)
- **WHEN** resume/re-enable фиксируется для этой Search-ноги
- **THEN** каждый resolved shop-linked получатель (тот же scope, что
  pause notify) MUST получить отдельное resume/re-enable сообщение

#### Scenario: Resume notify uses same shop-linked recipients as pause notify

- **GIVEN** у `shop_id` два (или более) `WBUserCabinet` с различными
  непустыми `user.user_telegram_id`, и empty-keywords pause notify был
  доставлен в эпизоде
- **WHEN** система выполняет notify empty-keywords resume/re-enable
- **THEN** `send_message` MUST быть вызван для **каждого** такого chat_id
  (не только для одного), с текстом resume/re-enable (не pause-entry)

#### Scenario: Resume notify is distinct from pause-entry and recheck-mention

- **GIVEN** доставлен empty-keywords pause notify (причина + упоминание
  перепроверки) и затем Search resumes / keywords re-enabled
- **WHEN** система формирует resume/re-enable notify
- **THEN** текст MUST NOT быть тем же, что pause-entry notify, и MUST NOT
  считаться выполненным одним лишь recheck-mention внутри pause message

#### Scenario: No resume notify without prior delivered pause notify episode

- **GIVEN** Search start / keywords active без предшествующего
  доставленного empty-keywords pause notify в эпизоде
- **WHEN** система обрабатывает ordinary Search start / keyword enable
- **THEN** empty-keywords resume/re-enable notify MUST NOT отправляться
  «за эту причину» (не спамить ordinary start)

## ADDED Requirements

### Requirement: Empty-keywords pause targets Search leg only

Для причины empty-keywords целевая сущность паузы и перепроверки — нога
Search комплекта. Система MUST использовать Search pause/start write-path и
MUST NOT использовать Auto pause write-path для этой причины. Отсутствие
ноги Search MUST NOT приводить к паузе Auto «вместо» Search.

#### Scenario: Wrong adapter Auto pause is forbidden

- **GIVEN** срабатывает empty-keywords pause path
- **WHEN** система выбирает WB pause adapter для этой причины
- **THEN** Auto pause adapter MUST NOT быть использован; MUST быть использован Search pause adapter при наличии Search

#### Scenario: Missing Search leg does not pause Auto

- **GIVEN** paid авто-настройка с ботом без ноги Search и empty-keywords условие выполнено
- **WHEN** система обрабатывает empty-keywords pause path
- **THEN** система MUST NOT ставить ногу Auto на паузу по причине empty-keywords

### Requirement: Settled empty vs Redis warmup false-empty

Empty-keywords pause ноги Search MUST вооружаться и исполняться только при
**settled empty** — подтверждённом пустом наборе активных ключей после
bot-driven OFF (или эквивалентном durable settled-empty / recheck после
уже settled empty-keywords pause). Система MUST NOT трактовать Redis
warmup-маркер `__empty__` или transient zero-active keyword read (пока
snapshot warmup ещё может заполнить keywords) как settled empty и MUST NOT
в этом окне ставить empty-keywords intent / паузить Search через
`pause_auction_campaign` на no-prior-intent path.

#### Scenario: Warmup __empty__ marker does not arm Search pause

- **GIVEN** paid авто-настройка с ботом, нога Search в STARTED, Redis keywords
  hash содержит warmup-маркер `__empty__` (или эквивалентный transient empty
  read), prior V3 empty-keywords intent отсутствует, bot-driven last-key OFF
  в этом тике не завершался
- **WHEN** activity-control оценивает no-prior-intent empty-keywords arm
- **THEN** система MUST NOT вооружить empty-keywords intent и MUST NOT
  вызвать Search pause (`pause_auction_campaign`) по причине empty-keywords

#### Scenario: Bot-driven settled empty still pauses Search

- **GIVEN** paid авто-настройка с ботом и ногой Search, автоматика завершила
  bot-driven выключение последнего активного ключа (settled empty), V3
  empty-keywords intent установлен (или эквивалентный settled-empty сигнал)
- **WHEN** система применяет empty-keywords pause path
- **THEN** нога Search MUST быть поставлена на паузу с причиной
  empty-keywords (при наличии Search и допустимом статусе), без Auto pause

### Requirement: Two-tick empty confirmation before Search pause

Для no-prior-intent подтверждения settled-empty (когда нет prior V3
bot-driven empty-keywords intent) система MUST применять Owner rule
`TWO_TICK_EMPTY_CONFIRMATION_BEFORE_PAUSE`:

1. **Tick1** — активных ключей нет и нога Search в STARTED: система MUST
   только зафиксировать / установить latch (record/intent latch). Система
   MUST NOT в этом тике вызывать Search pause (`pause_auction_campaign`)
   и MUST NOT ставить Search на паузу по причине empty-keywords.
2. **Tick2** — активных ключей по-прежнему нет: система MUST THEN
   поставить ногу Search на паузу через `pause_auction_campaign` с
   причиной empty-keywords.
3. **Later tick** — активные ключи снова есть: путь start/resume Search
   MUST быть доступен (существующее recheck/resume поведение MAY
   остаться).
4. Тики MUST продолжаться across этого lifecycle (latch → pause →
   resume).

Redis warmup-маркер `__empty__` остаётся non-settled (см. Requirement
«Settled empty vs Redis warmup false-empty») и MUST NOT считаться
tick1 settled confirmation. Two-tick latch — Owner settled-empty
confirmation path для no-prior-intent.

#### Scenario: Tick1 empty only latches — no Search pause

- **GIVEN** paid авто-настройка с ботом, нога Search в STARTED, активных
  ключей нет, prior V3 empty-keywords intent отсутствует, Redis warmup
  `__empty__` не является единственным «settled» сигналом, и two-tick
  latch ещё не установлен
- **WHEN** activity-control оценивает no-prior-intent empty-keywords path
  на первом таком тике
- **THEN** система MUST установить record/latch (intent/confirmation
  latch) и MUST NOT вызвать `pause_auction_campaign` / MUST NOT поставить
  Search на паузу по empty-keywords в этом тике

#### Scenario: Tick2 still empty pauses Search

- **GIVEN** на предыдущем тике уже установлен two-tick / empty-confirmation
  latch при empty active keywords + Search STARTED, и на текущем тике
  активных ключей по-прежнему нет
- **WHEN** система обрабатывает empty-keywords path на втором
  подтверждающем тике
- **THEN** система MUST вызвать `pause_auction_campaign` и поставить ногу
  Search на паузу с причиной empty-keywords (при допустимом статусе),
  без Auto pause

#### Scenario: Later non-empty allows Search start/resume

- **GIVEN** lifecycle two-tick confirmation / empty-keywords Search pause
  (или latch) уже имел место, и на более позднем тике снова есть хотя бы
  один активный ключ без нарушения других pause-правил Search
- **WHEN** система обрабатывает этот тик
- **THEN** путь start/resume ноги Search MUST быть доступен (Search MUST
  NOT оставаться на паузе исключительно из-за устаревшего empty-keywords
  без возможности resume)

#### Scenario: Ticks continue across latch-pause-resume lifecycle

- **GIVEN** empty-keywords two-tick latch и/или Search pause по
  empty-keywords
- **WHEN** проходит последующий shop-runner / activity-control тик
- **THEN** тики MUST продолжаться (lifecycle не останавливает дальнейшие
  оценки empty/non-empty и resume)
