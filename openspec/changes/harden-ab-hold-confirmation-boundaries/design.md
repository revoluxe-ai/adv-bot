## Context

Change усиливает уже существующий paid Telegram flow A/B Hold. Сейчас
callback содержит идентификатор кампании, шаг и revision/generation, но не
содержит доказательство принадлежности кампании текущему Telegram-пользователю.
Часть callback-хендлеров загружает `AdvSetting` только по идентификатору и после
проверки `bot_active` вызывает durable write-path или EXIT-cleanup.

В W3 экран строит строки из live read-model позиций. Для отсутствующей позиции
строка получает факт `0`, а текущая сборка `tp_map` может передать такую строку
в `confirm_target_places`. Поэтому проверка только наличия непустого словаря
подтверждённых позиций недостаточна.

Ограничения change:

- lifecycle WARM_UP → подтверждения → durable PENDING intent → WB sync → ACTIVE
  не меняется;
- существующие PG-поля confirmed epoch-параметров и текущая Redis-координация
  сохраняются;
- новые миграции и новый идентификатор владельца в callback не нужны;
- изменение не распространяется на billing, Pricer preview, обычные updater
  paths, migration tooling, performance optimization или deployment.

## Goals / Non-Goals

**Goals:**

- Перед любым подтверждающим или отключающим действием проверять, что
  `query.from_user.id` имеет доступ к кабинету, которому принадлежит
  `AdvSetting`.
- Делать stale/foreign callback fail-closed: не выполнять PG-write,
  Redis-cleanup, изменение FSM-черновика или переход lifecycle.
- Не допускать записи target place `0`, отрицательного, отсутствующего или
  нечислового значения.
- Сохранить разрешённый flow владельца и раздельное подтверждение
  keyword-set, target places, Auto participation и Auto bid.
- Обновить инструкцию и error-state так, чтобы они описывали фактический порядок
  подтверждения без раскрытия данных чужой кампании.

**Non-Goals:**

- Не менять модель ownership кабинета и не добавлять новую durable ACL.
- Не менять смысл WARM_UP, generation, PENDING intent, retry или ACTIVE.
- Не менять факт-позицию как live read-model и не превращать её в durable SoT.
- Не менять обычные A/B Hold structural freeze, bidder, budget или WB sync
  правила.

## Architecture Decision References

1. `openspec/decisions/card-ab-hold-write-path-ownership/decision.md`
   определяет paid A/B Hold write-path, разделение Telegram enable/disable и
   shop-runner setup/hold paths, а также запрет обходных writers.
2. `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md`
   определяет durable PG lifecycle, `FOR UPDATE` для epoch writes, порядок
   durable PENDING intent → WB sync и recovery partial sync.
3. `openspec/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md`
   определяет confirmed target places как durable PG SoT, отдельный от factual
   position, и обязательность отдельного явного подтверждения.

Новый reusable ownership или write-path decision не требуется: проверка
Telegram-владельца является access gate существующего paid UI write-path, а
валидация target place усиливает уже принятый invariant confirmed epoch
parameters.

## Ownership & Placement

**Owner layer.** Авторизация callback и user-facing отказ принадлежат
Telegram A/B Hold handlers. Они получают actor identity из
`CallbackQuery.from_user`, загружают кампанию и проверяют связь текущего
Telegram-пользователя с её `WBCabinet` через существующий
`get_wb_user_cabinet_for_adv_and_telegram`.

**Allowed layers:**

- Telegram handlers: actor/access gate, stale gate, preview/error rendering и
  запуск уже существующих write functions.
- Чистый A/B Hold lifecycle helper: проверка finite positive positions,
  исключение невалидных ключей с причиной и построение candidate `tp_map` для
  оставшегося валидного набора.
- A/B Hold epoch write-path: финальная защита durable payload и атомарная
  фиксация confirmed target places под существующим row lock.
- PG: существующий durable SoT режима и confirmed epoch parameters.
- Redis: только существующая cross-pod координация и cleanup после разрешённого
  EXIT.

**Forbidden layers:**

- `callback_data` как источник авторизации;
- FSM draft как источник ownership или durable confirmation;
- обычный V3 preamble, bidder, shared defaults, Excel и display-renderer как
  владельцы подтверждения;
- отдельная проверка только на видимости paid UI без проверки actor identity.

**Rationale.** Callback-поля являются недоверенным адресом действия и нужны для
маршрутизации, но не доказывают право на кампанию. Связь Telegram user →
`WBUserCabinet` → `WBCabinet` уже существует и проверяется в read-session без
новой схемы. Durable write остаётся в A/B Hold epoch write-path, поэтому
handlers не получают право менять SoT в обход принятых решений.

## Semantic Write Target

SEMANTIC_WRITE_TARGET_STATUS: RESOLVED

BUSINESS_TERM: A/B Hold confirmation and disable durable write
TARGET_ENTITY_OR_LEG: Durable A/B Hold lifecycle and confirmed-epoch record of
the campaign; Redis coordination cleanup is only a secondary side effect of an
authorized EXIT and is not the source of truth.
ALLOWED_ADAPTERS: Telegram A/B Hold handlers for actor/access gating and action
triggering; the existing A/B Hold epoch/setup write-path for durable PostgreSQL
confirmation and lifecycle writes; existing Redis coordination cleanup for an
authorized EXIT.
FORBIDDEN_ADAPTERS: callback payload fields as authorization; ordinary V3
preamble or updater, bidder, shared defaults, Excel, FSM draft, display
renderer, and foreign callbacks as confirmation/disable writers or cleanup
owners.
TARGET_EVIDENCE: `owner-contract.md` D-001–D-004; `openspec/decisions/card-ab-hold-write-path-ownership/decision.md` §§1–9; `openspec/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` §§6–12; `openspec/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md` §§1–4.
OWNER_DECISION_SOURCE: `owner-contract.md` D-001–D-004
REQUIRED_PAIRED_TESTS: associated-user confirmation/authorized EXIT versus
foreign confirmation/disable with no state, PG, Redis, or lifecycle side
effects; positive factual positions versus missing/non-positive positions;
allowed A/B Hold writer versus forbidden ordinary/shared/Excel writers.

## Decisions

### 1. Единственный actor gate перед callback-действием

Для callback, который может подтвердить параметр, отменить текущий flow или
выполнить EXIT, общий loader сначала:

1. загружает `AdvSetting` по callback ID;
2. проверяет paid UI availability;
3. проверяет `query.from_user.id` через существующую связь с кабинетом;
4. только затем выполняет stale revision/generation check и разрешённое
   действие.

При отсутствии actor, кампании или связи с кабинетом callback считается
недоступным. В этом случае handler отправляет безопасное общее уведомление,
не сообщает состояние чужой кампании и не вызывает ни один write/cleanup path.
Кнопки и callback schema не расширяются user ID: это не является доверенным
механизмом авторизации и увеличило бы payload без необходимости.

Та же проверка применяется к прямому `CardAbHoldDisable` в основном Telegram
handler и к `CahConfirmDisable` в confirm-flow. Для read-only redraw после
разрешённого callback используется тот же actor-bound context, чтобы чужой
callback не превращался в канал чтения состояния кампании.

### 2. Двойная защита target place

Live factual positions остаются read-only данными, загружаемыми существующим
keyboard/CH+PG read-model. До вызова durable writer UI-bound validation:

- требует finite factual position строго больше `0` для включения ключа в
  подтверждаемый набор;
- исключает ключи без такой позиции из набора и показывает пользователю каждый
  исключённый ключ с причиной;
- строит proposed target place только из оставшихся валидных позиций;
- если после исключения валидных ключей не осталось, подтверждение не
  выполняется и пользователь получает понятное уведомление.

На durable write boundary дополнительно проверяется, что `tp_map` непуст,
содержит только положительные целочисленные target places и покрывает весь
оставшийся подтверждённый keyword-set. Проверка выполняется после загрузки строки с
существующим `SELECT ... FOR UPDATE` и до `UPDATE`/`COMMIT`. Невалидный payload
завершается без изменения PG и без перехода в следующую phase.

Так read-model проверяет происхождение предложения, а writer защищает
инвариант хранения от будущих callers и от случайной передачи `0`. Факт и
target остаются разными полями: факт может отображаться как отсутствующий, но
не становится подтверждённой целью.

### 3. Recovery и гонки

Порядок проверки — actor gate, затем stale gate, затем input validation, затем
existing write-path. Если между read и write phase или generation изменилась,
существующий `FOR UPDATE` writer отклоняет переход; handler обрабатывает это как
stale/non-ready callback, не объявляет подтверждение успешным и перерисовывает
текущий durable экран.

Foreign/stale/invalid callback не очищает Redis и не сбрасывает FSM. Разрешённый
EXIT сохраняет текущий атомарный PG reset и связанный Redis cleanup. Partial WB
sync и retry продолжают использовать тот же generation и confirmed parameters;
этот change не создаёт новую эпоху и не меняет recovery contract.

### 4. User-facing instruction

Текст confirm-flow явно сохраняет порядок:

`keyword-set → WARM_UP duration → WARM_UP → factual position/proposed target →
target confirm → Auto participation confirm → Auto bid confirm → durable
intent → WB sync → ACTIVE`.

Текст не обещает, что target place фиксируется автоматически на ENTER, и не
сообщает «успешно», если owner gate или positive-position validation не прошли.
Текст показывает исключённые ключи и причины; при пустом валидном наборе
подтверждение не продолжается.
Динамические тексты и callback payloads проверяются существующими Telegram
limit-тестами с worst-case данными.

## Derived Lifecycle

LIFECYCLE_STATUS: DERIVED

L1. Callback entry and actor gate
SOURCE: `owner-contract.md` §§ «Что хотим получить», «Как поймём, что получилось»;
`card-ab-hold-write-path-ownership/decision.md` §§6, 9–10.

L2. Current durable phase and stale revision/generation gate
SOURCE: `owner-contract.md` «Существующий lifecycle эксперимента и его durable
state»; `ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` §§7–9.

L3. Live factual-position preview, exclusion of invalid keys, and
positive-input validation
SOURCE: `owner-contract.md` «Отсутствующая или неположительная позиция»;
`ab-hold-confirmed-epoch-parameters-sot/decision.md` §§2–3.

L4. Explicit target-place confirmation through A/B Hold epoch write-path
SOURCE: `owner-contract.md` «Требование явного подтверждения»;
`ab-hold-confirmed-epoch-parameters-sot/decision.md` §§3, 8.

L5. Durable confirmed state or no-op on rejection
SOURCE: `ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` §§6–8;
`ab-hold-confirmed-epoch-parameters-sot/decision.md` §§1–4.

L6. Existing EXIT and retry recovery
SOURCE: `owner-contract.md` «Существующий lifecycle»;
`card-ab-hold-write-path-ownership/decision.md` §§9–10;
`ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` §§7–8.

## Risks / Trade-offs

- **[Risk]** Проверка владельца может ошибочно заблокировать разрешённого
  пользователя при неполной связи кабинета. → Использовать существующий
  relation helper и paired positive/foreign tests; не менять модель связи.
- **[Risk]** Позиция изменится между live read и PG write. → Writer повторно
  проверяет payload и phase под `FOR UPDATE`; новая нулевая или неполная цель не
  коммитится.
- **[Risk]** Слишком ранний stale отказ ухудшит UX. → После отказа показывать
  актуальный экран только разрешённому пользователю; foreign callback получает
  нейтральный отказ без redraw чужих данных.
- **[Trade-off]** Исключение ключей с отсутствующей или неположительной
  позицией позволяет подтвердить оставшийся валидный набор, но требует показать
  пользователю причины исключения. → Это не превращает отсутствие факта в
  target place `0`; при пустом валидном наборе подтверждение блокируется.

## Migration Plan

Новая миграция не требуется: используются существующие связи кабинета,
`AdvSetting` epoch-поля, FSM draft и Redis coordination keys.

Порядок реализации:

1. Добавить regression tests для actor gate, positive-position gate и paired
   allowed/blocked flows.
2. Вынести общий owner check на Telegram boundary и подключить его ко всем
   confirm/disable actions.
3. Добавить pure input validation и финальную проверку `tp_map` в existing
   epoch write boundary.
4. Обновить тексты и payload-limit assertions, затем прогнать targeted
   `card_ab_hold` tests и type/lint checks.

Rollback — удалить только новый actor/input gate и связанные тексты/тестовые
ожидания. Existing PG epoch fields, generation, Redis keys и durable campaign
state не откатываются и не очищаются rollback-операцией.

## Open Questions

Требуется определить только локальные имена нового validator/helper и
нейтральной строки отказа. SoT, ownership, write authority, positive-input
semantics и recovery contract уже разрешены выше и не откладываются до apply.

## Product Acceptance

PRODUCT_ACCEPTANCE_REQUIRED: true
PRODUCT_ACCEPTANCE_STATUS: BLOCKED
REASON: scenario coverage and side-effect evidence are not yet materialized

## DESIGN_READINESS

PRODUCT_SEMANTICS_RESOLVED: yes
STATE_OWNERSHIP_RESOLVED: yes
DURABLE_SOT_RESOLVED: yes
WRITE_AUTHORITY_RESOLVED: yes
RECOVERY_SEMANTICS_RESOLVED: yes
NORMATIVE_CONFLICTS: none
NORMATIVE_MODALITY_PRESERVED: yes
IMPLEMENTATION_CRITICAL_OPEN_QUESTIONS: none
DESIGN_STATUS: READY

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (не требуется: placement закрыт принятыми decisions)
- [x] implementation layer matches decision
