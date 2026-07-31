## Context

Клиентам нужен paid self-service режим для «чистого» A/B-теста карточки: явно выбрать и подтвердить набор ключей и целевые позиции, прогреть кампанию перед фиксацией, отключить обновление ЦП, оставить биддер работающим, отдельно управлять участием и ставкой Auto — не полагаясь на полный `bot_active=False` и не на хрупкую комбинацию legacy-флагов.

Ранее применённая MVP-1 реализация (`card-ab-hold-write-path-ownership` §1–§14, tasks §1–§18) уже закрыла: paid-only Telegram enable/disable, freshness/V3-only/max-CPO/soft-volume гейты на enable, allowed-set PG snapshot + hold enforcement минус-профиля, Excel write-path removal, idempotent Enable, hide-Enable keyboard, shared-defaults guard, PENDING_SETUP liveness. Эта реализация остаётся действующим фундаментом.

**Owner-approved обновление (этот `/opsx-update`; semantic SoT = owner-approved product requirements + CONTROL decisions, НЕ `REQ-AB-HOLD-BUDGET-SAFETY-001`):** MVP-1 фиксировала целевую позицию синхронно с автоматической PASS/FAIL классификацией на ENTER — без отдельного прогрева и без явных подтверждений пользователя (keyword/TP/Auto). Владелец продукта требует другой флоу поверх существующего фундамента: keyword confirm → durable WARM_UP (не короче 24ч) → раздельное отображение факт-позиции/предложенной целевой позиции → явный TP confirm → явный Auto participation confirm → явный Auto bid confirm → durable PENDING intent → WB sync → активный hold. Этот design обновляет план (не код — `/opsx:apply` в рамках этого обновления заблокирован до авторизации владельцем); реализация должна происходить строго по цитируемым ниже decisions.

Стек: Python 3.11, SQLAlchemy + PostgreSQL, Redis (`AdvSettingRedisCache` / `RedisCacheBase`, `RedisLockManager`), Telegram paid UI, существующий daily-budget/activity-control controller (`ensure_campaigns_active` / auto-budget watchdog).

## Goals / Non-Goals

**Goals:**

- Обновить план (proposal/design/spec/decisions/tasks) так, чтобы явно кодировать: durable WARM_UP (default/min 24ч, увеличение разрешено, уменьшение запрещено, без авто-add/авто-return, safety-исключение допускается, TP не фиксируется); раздельное отображение факт-позиции и предложенной целевой позиции (`ab_hold_target_place_from_keyword(position)`) как двух семантических полей; явные раздельные подтверждения TP / Auto participation / Auto bid; durable immutable TP в пределах эпохи (ENTER/retry не пересчитывают; дрейф не переоткрывает подтверждение); durable PENDING intent строго до WB-мутации; partial sync → восстановимое не-активное состояние; retry того же generation без пересчёта и без новой эпохи; freeze keyword inclusion/exclusion и Search/Auto bid-мутаций при stale/missing статистике на всём жизненном цикле (без остановки кампании только по этой причине); честное описание daily-budget/activity-control reuse (stop threshold, overshoot без гарантированной границы, суточный сброс); Telegram UX на уровне плана (пагинация 10, «Назад» сохраняет черновик, «Отмена» — отдельное действие); раскатку через ручной тест владельца → лимитированную opt-in бету → OD-05 как единственный гейт широкого включения.
- Устранить перечисленные владельцем противоречия (см. Decisions → «Устранённые противоречия»).
- Сохранить согласованность с уже применённым MVP-1 фундаментом (не откатывать §1–§14/tasks §1–§18).

**Non-Goals:**

- Полный UX-контракт и Telegram storyboard нового confirm-флоу — не этот design; создан отдельным последующим `/opsx-continue` в `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` и `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md` (планирующие UX-документы; не разблокируют `/opsx:apply` §19–25).
- Monitoring/alerting и evidence-driven emergency stop — OUT_OF_SCOPE_FOLLOW_ON, не артефакт этого обновления.
- Абсолютный тестовый бюджет, epoch spend cap, velocity cap, generic financial latch, новая emergency-stop подсистема, global refill/restart suppression, отдельная финансовая safety-ownership decision.
- Изменение самого daily-budget/activity-control controller — только честное описание его существующего поведения.
- `/opsx:apply` в рамках этого обновления — реализация заблокирована до авторизации владельцем.
- Owned авто-abort зависшего PENDING — остаётся SHOULD/future (не меняется этим обновлением).

## Architecture Decision References

Architecture Decisions Found:

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — Status: **Accepted**. Дефолт «A/B Hold выкл» при paid/free overlays принадлежит declarative mode policy overlays, не transition-helper/UI. Применяется без изменений.
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — Status: **Proposed**. §1–§14 — применённый MVP-1 фундамент (ownership setup/hold write-path, structural freeze, allowed-set snapshot + enforcement, Excel-removal, idempotent Enable, V3-only, shared-defaults guard, PENDING liveness). **Обновлено этим change**: §15 (WARM_UP/epoch/generation — ссылка на новый decision ниже), §16 (confirmed epoch-parameters SoT — ссылка на новый decision ниже), §17 (stale/missing stats freeze для keyword inclusion/exclusion **и** Search/Auto bid-мутаторов, не только enable-гейта §2a; **PBH-005 carve-out:** after durable PENDING intent, apply snapshot PG/WB MUST NOT be stale-blocked; MVP default = soft), §18 (daily-budget/activity-control — ортогональный reuse существующего controller, без новой финансовой safety-модели). **Дополнительно обновлено (`/opsx-update` Search common-bid):** §3 (ordinary continuous Search common-bid Forbidden under Hold; bidder остаётся Allowed) + **§19** (Search common bid = рабочая механика холодных ключей/каталога; one-shot reset-to-min на ENTER; затем freeze; owned path ≠ ordinary updater ≠ bidder).
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` — Status: **Proposed (новый в этом change)**. WARM_UP как durable pre-epoch стадия (default/min 24ч); epoch/generation модель; durable PENDING intent строго до WB-мутации; partial sync → non-ACTIVE recoverable; retry того же generation/параметров без пересчёта и без новой эпохи; дрейф позиции не переоткрывает подтверждение.
- `openspec/changes/card-ab-hold-mode/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md` — Status: **Proposed (новый в этом change)**. Confirmed keyword set / confirmed target places / confirmed Auto participation / confirmed Auto bid — durable SoT, отдельный от факт-состояния WB; факт-позиция и target place — раздельные семантические поля; immutable TP в пределах эпохи; Auto bid мутаторы заморожены в активном hold; owner — A/B Hold confirmation write-path, не display-слой и не ordinary auto-updaters.

Architecture Decision Missing: нет для этого обновления — placement закрыт тремя proposed decisions выше (одна обновлена, две новые); при archive reusable часть промотится в `openspec/decisions/`.

## Ownership & Placement

**Owner layer:**

- A/B Hold epoch/setup write-path (shop-runner, тот же owner, что существующие `process_ab_setup` / `process_ab_hold` entrypoints): владеет WARM_UP-таймером, epoch/generation-нумерацией, durable PENDING intent → WB sync → активный hold порядком, retry-логикой (тот же generation, без пересчёта); **также** one-shot Search common-bid reset-to-min на ENTER (`OFF`→`PENDING_SETUP`, decision §19) — не ordinary `update_common_bid_in_search_adv` и не bidder.
- A/B Hold confirmation write-path (Telegram confirm-хендлеры → durable PG запись): владеет confirmed keyword set / confirmed target places / confirmed Auto participation / confirmed Auto bid; читает факт-позицию из существующего read-model, не хранит её как подтверждённый параметр.
- PG durable поля: режим кампании (OFF/PENDING/ACTIVE-класс, уже существует), allowed-set snapshot (уже существует), + **planned Alembic fields** (см. `tasks.md` §19.5 / §22.5): `card_ab_hold_phase`, `card_ab_hold_warmup_started_at`, `card_ab_hold_warmup_duration_hours`, `card_ab_hold_generation`, `card_ab_hold_wb_sync_idempotency_key`, `card_ab_hold_pending_intent_json`, `card_ab_hold_sync_status`, `card_ab_hold_confirmed_keywords_json`, `card_ab_hold_confirmed_target_places_json`, `card_ab_hold_confirmed_auto_participation`, `card_ab_hold_confirmed_auto_bid`. Owner и порядок фиксируются здесь; имена колонок — planning SoT для apply (не код). **Legacy rows:** NULL/0 defaults on new columns MUST NOT activate epoch lifecycle (§18.5 / Migration Plan).
- **Legacy gate (pre-apply REQUIRED):** `process_ab_setup` → auto-ACTIVE и `setup_apply` TP-write на ENTER PASS — Forbidden относительно owner-флоу; MUST быть phase-gated до apply §19+ (`tasks.md` §18.4).
- Redis coordination layer (уже существует: `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock`) — координация cross-pod, не SoT для confirmed-параметров или generation.
- Существующий daily-budget/activity-control controller (`ensure_campaigns_active` / auto-budget watchdog) — не меняется этим change; A/B Hold только честно описывает его поведение (stop threshold, overshoot без гарантированной границы, суточный сброс) как ортогональный путь.
- Mode policy overlays — дефолт «выкл» (без изменений, Accepted decision).

**Allowed layers:** scheduling exclusion в `adv_settings_auto_update` (существует), ACT structural guards (существуют), hold guard executors (существуют), allowed-set enforcement (существует), bidder/cluster bids (существуют, теперь явно как holder confirmed target places), Telegram confirm-хендлеры как triggers epoch/generation write-path (не как SoT), owned ENTER Search common-bid reset-to-min (`common_bid_enter_reset`, applied §27 / decision §19).

**Forbidden layers:**

- Фиксация целевой позиции в момент автоматической классификации ключа (ENTER-тик) без прошедшего durable WARM_UP и без явного TP confirm.
- Хранение/пересчёт confirmed target place или confirmed Auto bid в display/formatting-слое, в ordinary auto-updater или в Telegram-хендлере напрямую (мимо epoch write-path).
- WB-мутация confirmed-параметров эпохи до записи durable PENDING intent в PG.
- Продвижение generation, пересчёт TP/Auto bid на retry WB-синхронизации.
- Остановка кампании исключительно по причине stale/missing статистики (freeze мутаций — да; остановка кампании — нет, это отдельное более сильное действие).
- Введение нового финансового safety-механизма (абсолютный бюджет, velocity cap, emergency-stop подсистема, global refill suppression) в A/B Hold write-path.
- Continuous ordinary Search common-bid mutate (`update_common_bid_in_search_adv`) во время `PENDING_SETUP` / `ACTIVE`; leave elevated common bid frozen as-is on ENTER without owned reset-to-min; выполнить ENTER reset через ordinary updater или bidder (§19).

**Rationale:** соответствует обновлённому proposed `card-ab-hold-write-path-ownership` (§15–§19) и двум новым proposed decisions (`ab-hold-epoch-lifecycle-and-generation-ownership`, `ab-hold-confirmed-epoch-parameters-sot`), а также accepted `mode-defaults-policy-ownership`. Ownership placement для WARM_UP/epoch/confirm-слоя и Search common-bid ENTER reset не пересекается с ordinary common-bid updater и bidder — дополняющие слои, не замена.

## Decisions

### 1. WARM_UP как отдельная durable pre-epoch стадия (см. `ab-hold-epoch-lifecycle-and-generation-ownership`)

**Выбор:** явное подтверждение набора ключей запускает WARM_UP; длительность — durable параметр эпохи, default = 24 часа, минимум = 24 часа; пользователь MAY увеличить, MUST NOT уменьшить ниже 24 часов. Во время WARM_UP: без авто-добавления новых ключей, без авто-возврата исключённых, safety-исключение Allowed, целевая позиция не фиксируется. Существующие пороги «≥100 показов/ключ» и «≥1000 показов кампании» (soft-gate объёма) сохраняют текущую семантику как условия eligibility/enable, а не длительность WARM_UP.

**Почему:** без durable прогрева перед фиксацией целевой позиции тест начинается на «холодном» или ещё не устоявшемся профиле; фиксация синхронно с классификацией (MVP-1) не даёт пользователю время убедиться в стабильности набора ключей и не даёт возможности осознанно подтвердить именно то, что будет заморожено.

**Альтернатива:** оставить фиксацию TP синхронно с ENTER-классификацией (MVP-1 как есть) — отклонена владельцем: silent auto-ENTER без warm-up и без confirm — explicit contradiction to remove. Сделать WARM_UP настраиваемым без минимума — отклонена (риск слишком короткого/нулевого прогрева).

### 2. Ручное изменение набора ключей во время WARM_UP сбрасывает таймер

**Выбор:** любое ручное изменение состава подтверждённого набора ключей во время WARM_UP завершает текущий таймер и запускает новый отсчёт (снова ≥ выбранной длительности, не короче 24 часов); остаток прежнего таймера не переносится.

**Почему:** прогрев измеряет стабильность именно того набора, который в итоге будет заморожен; изменение набора обесценивает уже прошедшее время прогрева для нового состава.

**Альтернатива:** переносить остаток таймера на новый набор — отклонена (не гарантирует полноценный прогрев нового состава).

### 3. Факт-позиция и предложенная/подтверждённая целевая позиция — раздельные семантические поля (см. `ab-hold-confirmed-epoch-parameters-sot`)

**Выбор:** после WARM_UP экран/сообщение показывает по каждому ключу факт (текущая наблюдаемая позиция, read-model) и отдельно предложенную целевую позицию через `ab_hold_target_place_from_keyword(position)`; пользователь явно подтверждает целевую позицию; подтверждённое значение становится durable и immutable в пределах эпохи. ENTER/setup/retry не пересчитывают подтверждённое значение; обычный дрейф факт-позиции после подтверждения не переоткрывает подтверждение.

**Почему:** слияние факт-позиции и целевой позиции в одно поле мешает пользователю осознанно оценить предложение и делает подтверждение неотличимым от простого чтения текущего состояния; фиксация без возможности пересмотра после подтверждения нужна, чтобы тест оставался «чистым» на протяжении эпохи.

**Альтернатива:** пересчитывать target place при каждом отображении статуса (текущая факт-позиция) — отклонена (эквивалент «TP fixed без confirm», прямое противоречие).

### 4. Отдельные явные подтверждения Auto participation и Auto bid

**Выбор:** участие Auto в тесте и ставка Auto подтверждаются двумя отдельными явными действиями пользователя, независимыми друг от друга и от Search-подтверждений (keyword set, TP). После активного hold ordinary auto-update мутаторы ставки Auto не изменяют подтверждённое значение.

**Почему:** Auto и Search — разные рекламные механизмы с разными рисками (широкий матчинг Auto); слияние подтверждений в одно действие скрывает от пользователя, что он в действительности разрешает автоматике по ставке.

**Альтернатива:** подразумевать участие/ставку Auto из Search-подтверждения — отклонена владельцем (silent auto-TP/Auto без явного confirm — explicit contradiction to remove).

### 5. Durable PENDING intent строго до WB-мутации; partial sync — восстановимое не-активное состояние; retry без пересчёта и без новой эпохи (см. `ab-hold-epoch-lifecycle-and-generation-ownership`)

**Выбор:** после всех подтверждений write-path фиксирует durable намерение (все confirmed-параметры + generation) в PostgreSQL перед первой попыткой WB-мутации этой generation. Если синхронизация WB завершилась частично, кампания остаётся не-активной с сохранённым тем же durable намерением; повторная попытка переиспользует тот же generation/параметры без пересчёта TP/Auto bid и без создания новой эпохи. Активный hold достигается только после подтверждённо полной успешной синхронизации.

**Почему:** без durable-before-WB порядка потеря процесса/сети между подтверждением и WB-записью оставляет систему без источника правды о том, что пользователь на самом деле разрешил; пересчёт на retry обесценивает уже сделанные подтверждения и повторяет прежний класс проблем (ACTIVE без честного snapshot).

**Альтернатива:** пересчитывать TP/Auto bid на каждый retry по свежей стате — отклонена владельцем (retry, который пересчитывает TP/Auto bid или продвигает generation — explicit contradiction to remove).

### 6. Stale/missing статистика замирает Search/Auto bid-мутации и keyword inclusion/exclusion, но не останавливает кампанию (см. обновлённый §17 write-path decision)

**Выбор:** пока кампания в WARM_UP, ожидании подтверждения или активном hold, при stale/missing статистике по ключу/кампании замирают **decide-class** пути: (a) включение/исключение ключей (в т.ч. WARM_UP safety-исключение, hold-enforcement, **и ENTER/setup FAIL→OFF**), (b) мутации ставки Search и мутации ставки/участия Auto. Freeze не пересчитывает уже подтверждённые (durable, immutable) параметры эпохи. **Apply snapshot ≠ decide:** после записи durable PENDING intent применение confirmed-параметров в PG и синхронизация в WB (`apply_confirmed_intent_to_pg` / `sync_intent_to_wb`) **MUST NOT** блокироваться только из‑за stale/missing stats (PBH-005 carve-out). На том же тике decide-class пути MAY оставаться заморожены. MVP default safety stance = **soft** (freeze decide; не abort/reset эпохи только из‑за stale; EXIT — явное действие пользователя). Stale/missing статистика сама по себе не является причиной остановки кампании. **UX:** при Enable и/или в статусе теста — краткий soft-policy disclaimer: временные сбои статы обычно безобидны; ради ровного теста бот не меняет состав ключей/ставки наугад; пользователь сам контролирует ход (формулировка freeze-decide, не «ослабим защиту»).

**Почему:** решения на «неизвестных» данных хуже временной заморозки; но уже согласованный PENDING intent — исполнение снимка, а не новое решение по стате. Блокировать sync stale-гейтом смешивает decide и apply и оставляет кампанию в «подготовке» при периодическом stale. Disclaimer снимает ложное ожидание, что soft = «бот сам всё разрулит при любой дыре в стате».

**Альтернатива:** останавливать кампанию при stale-стате как safety-мера — отклонена владельцем. Pre-start picker hard|soft|self, anti-drain и mid-sync UX (wait|force|EXIT) — **не** owed design work этого change; см. `DOTO/WORKLOG.md` `[deferred-from:card-ab-hold-mode]` (parked via `/opsx-bound-scope`).

### 7. Daily-budget / activity-control — честный reuse существующего controller, не новая финансовая safety-модель (см. обновлённый §18 write-path decision)

**Выбор:** A/B Hold переиспользует существующий daily-budget/activity-control controller как есть. Это стоп-порог (stop threshold), а не жёсткий лимит: перерасход возможен из-за задержки статы, каданса воркера, in-flight трат, конкурентных write-путей и top-up без обрезки до остатка бюджета; нет гарантированной числовой верхней границы overshoot; суточный сброс и возобновление трат на следующий день — ожидаемое поведение, честно раскрываемое пользователю (уровень плана; конкретный текст — Telegram storyboard, DEFERRED). Абсолютный тестовый бюджет / epoch spend cap / velocity cap / financial latch / новая emergency-stop подсистема / global refill suppression не вводятся.

**Почему:** владелец явно запретил параллельную финансовую safety-модель и `REQ-AB-HOLD-BUDGET-SAFETY-001` как текущий scope; честное раскрытие существующего поведения контроллера снижает риск того, что пользователь примет daily-budget за гарантированный потолок теста.

**Альтернатива:** ввести отдельный epoch spend cap специально для A/B Hold — отклонена владельцем (explicit out-of-scope item).

### 8. Telegram UX на уровне плана: пагинация 10, «Назад» сохраняет черновик, «Отмена» — отдельное действие

**Выбор:** список ключей на экранах подтверждения пагинируется по 10 элементов на страницу; кнопка «Назад» сохраняет текущий черновик подтверждения (не отбрасывает прогресс); «Отмена» — отдельное явное действие, отличное от «Назад», приводящее к отказу от текущей попытки без сохранения черновика. Существующий MVP-1 экран `card_ab_hold` — не референс для нового флоу.

**Почему:** это планировочные, стабильные ограничения UX (размер страницы, различие «Назад»/«Отмена»), достаточные для дальнейшего дизайна конкретных экранов; полный сторибоард — отдельная задача с собственным review.

**Альтернатива:** сразу проектировать полный сторибоард в этом обновлении — отклонена владельцем; выполнено отдельным последующим `/opsx-continue` (см. `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md`, `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md`).

### 9. Раскатка: ручной тест владельца → лимитированная opt-in бета → OD-05 → широкое включение

**Выбор:** после реализации (отдельный будущий `/opsx:apply`, заблокированный в этом обновлении) первый этап — ручной тест владельцем на собственных/тестовых кампаниях; второй этап — ограниченная opt-in бета с структурированным сбором фидбэка; широкое включение для всех paid-пользователей возможно только после явного принятия владельцем решения **OD-05**. OD-05 — единственное открытое owner-решение этого обновления.

**Почему:** WARM_UP/confirm/epoch-слой меняет ключевой пользовательский флоу поверх уже работающего MVP-1; владелец явно запросил постепенную, управляемую раскатку с одной точкой принятия решения (OD-05), а не немедленное широкое включение.

**Альтернатива:** включить для всех paid-пользователей сразу после реализации — отклонена владельцем.

### 10. Search common bid: reset-to-min on ENTER, then freeze (см. write-path §19)

**Выбор:** при ENTER (`OFF` → `PENDING_SETUP`) A/B Hold owned path **один раз** сбрасывает Search common bid (общая ставка аукциона / `SetCommonBids`) на WB minimum по nm кампании; пока `PENDING_SETUP`/`ACTIVE`, continuous ordinary `update_common_bid_in_search_adv` Forbidden; bidder/cluster bids в ACTIVE продолжает держать ставки к confirmed ЦП. Повторный reset — только после EXIT → новый ENTER.

**Почему:** common bid — рабочая механика (холодные ключи до порога показов + каталог), не мёртвый legacy и не bidder. Freeze-as-is оставлял бы завышенную общую ставку; ordinary up/reset цикл под Hold загрязняет тест. Owner product: min + freeze.

**Альтернатива A:** только freeze ordinary updater без reset — отклонена (elevated common bid остаётся).  
**Альтернатива B:** reset при переходе в ACTIVE / после TP confirm — отклонена владельцем (тайминг = ENTER → PENDING_SETUP).  
**Альтернатива C:** поручить reset ordinary `update_common_bid_in_search_adv` — отклонена (continuous Forbidden under Hold; нужен owned one-shot).

### Устранённые противоречия (сверка с owner-approved списком)

- Тихая авто-классификация ENTER / авто-TP без явных подтверждений keyword+TP+Auto — устранено decisions §3, §4 выше и `ab-hold-confirmed-epoch-parameters-sot`.
- TP, зафиксированная на ENTER без WARM_UP и без раздельного отображения факт-позиции vs предложенного TP — устранено decisions §1, §3.
- HOLD без durable WARM_UP — устранено decision §1 (WARM_UP предшествует любому TP confirm, который предшествует hold).
- Абсолютный тестовый бюджет / velocity cap / emergency-stop / financial-safety-ownership из прежнего PLAN_ONLY — устранено decision §7 (явно out of scope).
- Daily budget как hard cap / epoch cap / гарантированная граница overshoot — устранено decision §7 (честное stop-threshold описание).
- ACTIVE без durable PENDING intent + успешной WB sync — устранено decision §5.
- Retry, пересчитывающий TP/Auto bid или продвигающий generation — устранено decision §5.
- Framing, будто `REQ-AB-HOLD-BUDGET-SAFETY-001` или параллельная финансовая safety-модель — текущий scope — явно исключено (Context, decision §7, Non-Goals).
- Search common bid «забыт» / freeze-as-is без reset-to-min на ENTER — устранено decision §10 выше и write-path §19.

## Risks / Trade-offs

- [Risk] Пользователь подтверждает TP слишком быстро после короткого WARM_UP и не замечает нестабильность позиции. → Mitigation: минимум 24 часа не обходится; отображение факт-позиции отдельно от предложенной цели даёт пользователю сигнал перед подтверждением.
- [Risk] Ручной сброс WARM_UP-таймера при частых изменениях набора ключей затягивает вход в тест. → Acceptable trade-off: владелец явно требует полноценный прогрев именно финального набора.
- [Risk] Partial sync оставляет кампанию в подвешенном не-активном состоянии дольше, чем ожидает пользователь. → Mitigation: retry переиспользует тот же generation/параметры автоматически на следующем тике (детали планирования retry — предмет будущего `/opsx:apply`); EXIT остаётся доступным в любой момент (существующий MVP-1 инвариант).
- [Risk] Freeze Search/Auto bid-мутаций при stale-стате маскирует реальную проблему получения статистики. → Mitigation: существующий freshness-класс и honest-degradation паттерн (уже применён для allowed-set §8/§12–§13 write-path decision) переиспользуются, а не изобретаются заново.
- [Risk] Пользователь трактует daily-budget stop-threshold как гарантированный потолок расходов теста. → Mitigation: явное честное описание overshoot-факторов в плане (этот design) и, в дальнейшем, в Telegram-копирайте (DEFERRED, но обязано наследовать эту честность).
- [Risk] One-shot ENTER common-bid reset fails (WB/min unavailable) and campaign enters PENDING with elevated common bid. → Mitigation: visible degrade / retry on setup tick; MUST NOT silently claim reset done; continuous ordinary updater remains Forbidden under Hold (decision §19).
- [Risk] Широкая раскатка до валидации нового флоу повторяет паттерн «слишком рано ready» из MVP-1. → Mitigation: OD-05-гейт и двухэтапная раскатка (ручной тест → лимитированная бета) как единственный путь к broad enable.

## Migration Plan

1. Этот `/opsx-update` обновляет только планирующие артефакты (`proposal.md`, `design.md`, `specs/card-ab-hold-mode/spec.md`, `tasks.md`, три decision-файла); код/тесты/миграции не создаются и не изменяются. **OP-006 pre-apply planning fixes (2026-07-23):** §18.4 legacy gate; §4.1 TP wording; Alembic field names в §19.5/§22.5; AutoResetBidService в §21.3/§21.4; OD-05 остаётся единственным open owner decision. **OP-008 pre-apply planning fixes (2026-07-23):** PG idempotency/uniqueness contract (§22.5); legacy in-flight policy (§18.5); writer inventory; UX S3 keyboard; explicit test tasks.
2. `/opsx:apply` для новых задач (`tasks.md` §18.4 и §19+) заблокирован до явной авторизации владельцем.
3. При авторизации: реализация в порядке зависимостей — **§18.4 gate legacy auto-ACTIVE/auto-TP** → durable WARM_UP-таймер/эпоха/generation-поля → confirm-write-path (keyword/TP/Auto) → durable PENDING intent → WB sync/retry → freeze Search/Auto bid при stale-стате (вкл. `AutoResetBidService`) → **§27 ENTER Search common-bid reset-to-min + ordinary continuous freeze** → честный daily-budget disclosure в UI-копирайте (по UX-контракту) → ручной тест владельца → лимитированная бета.
4. Широкое включение для всех paid-пользователей — только после OD-05.
5. Rollback: как в применённом MVP-1 (EXIT → OFF, allowed-set snapshot clear, Redis TTL cleanup) плюс — durable WARM_UP-таймер/PENDING intent без завершённой синхронизации не создают побочных WB-эффектов и очищаются при EXIT/rollback. **Rollback migration MUST NOT** drop or null-out legacy `card_ab_hold_mode`, `allowed_phrases_snapshot`, or `card_ab_hold_degraded` in a way that destroys in-flight legacy hold state.

### Legacy / in-flight migration policy (OP-008)

Applies to campaigns already in MVP-1 hold at migration time and to any row where new epoch columns arrive via Alembic with NULL/0 defaults.

| Rule | Contract |
|---|---|
| No auto-conversion | Existing MVP-1 campaigns (`card_ab_hold_mode` ∈ {`PENDING_SETUP`, `ACTIVE`} with `card_ab_hold_phase` NULL) **MUST NOT** auto-convert to epoch-managed generation on migration or process restart. |
| NULL phase = legacy | `card_ab_hold_phase` NULL means **legacy-MVP-1 semantics** until EXIT or controlled re-enter under fail-closed feature flag (§25). |
| New flow entry | New epoch flow (WARM_UP → confirms → PENDING intent → WB sync → ACTIVE) only via fail-closed feature flag + explicit owner entry — not via migration defaults. |
| ACTIVE legacy continues | Already `ACTIVE` legacy campaigns continue legacy hold behavior (`process_ab_hold`, allowed-set enforcement, legacy setup path where still gated) until explicit EXIT; prefer EXIT-only transition to new flow for MVP (no silent in-place epoch upgrade). |
| Process restart | Process restart / shop-runner redeploy **MUST NOT** change flow version for a row; durable PG fields are SoT. |
| Migration defaults inert | New columns (`card_ab_hold_phase`, `card_ab_hold_generation`, `card_ab_hold_pending_intent_json`, `card_ab_hold_sync_status`, `card_ab_hold_wb_sync_idempotency_key`, confirmed-* columns, warmup timer fields) with NULL / 0 / `none` defaults **MUST NOT** activate the new lifecycle on existing rows. |
| No automatic backfill | Automatic backfill of confirmed parameters (keyword set, TP map, Auto participation/bid) from live WB/PG state **FORBIDDEN** for legacy rows — would fake user confirms. |
| Rollback safety | Downgrade migration MUST preserve legacy mode, allowed-set snapshot, and degraded flag; MUST NOT destroy in-flight legacy hold. |

## Open Questions

1. ~~Точные названия новых durable PG-полей~~ — **RESOLVED (OP-006 planning):** planned names зафиксированы в `tasks.md` §19.5 / §22.5 и Ownership & Placement выше; Alembic SQL создаётся только при `/opsx:apply`.
2. Ретрай-каденс и лимит попыток WB-синхронизации при partial sync (сколько раз/как часто повторять до эскалации actionable-статуса пользователю) — implementation-деталь будущего `/opsx:apply`; текущий design фиксирует только инвариант «тот же generation, без пересчёта».
3. Точный UX-контракт и тексты Telegram-сообщений (в т.ч. текст про честный overshoot) — создан отдельным последующим `/opsx-continue`: `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` (контракт) и `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md` (иллюстративные тексты, не binding — implementation MAY скорректировать формулировки при `/opsx:apply`, сохраняя инварианты).
4. Критерий/процедура принятия OD-05 (кто, когда, по каким метрикам бета-теста) — owner decision, вне scope этого design; фиксируется только то, что OD-05 — единственный гейт широкого включения.

## Practice Applicability Map (pilot v0.1)

```yaml
change_id: card-ab-hold-mode

practice_baseline:
  branch: operator/TASK-WB-AB-TESTING-COMPLETE-IMPLEMENTATION-001
  head_sha: bc2223605f53fb28539e761f13b6fa144fc9bea4
  date: 2026-07-26

baseline_note: >
  Dated pilot evidence based on draft Practices v0.1.
  This is not project-wide policy and does not affect archive readiness.

applicable_practices:
  - practice_id: call-chains
    applicability_reason: >
      Change owns multiple entrypoints and strategies (Telegram enable/confirm,
      shop-runner epoch/setup/hold, ordinary V3 interrupt) that reach PG, Redis,
      and WB write resources; canonical chains and owner bypass must stay
      traceable.
    selected_rule_ids:
      - CALL-001
      - CALL-002
    evidence_locators:
      - openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md
      - openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md
      - app/modules/shop_runner/service_manager/manager.py::adv_settings_auto_update
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/pipelines.py::process_ab_setup
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/pipelines.py::process_ab_hold
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_pipelines.py::process_ab_epoch
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_write.py
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py::enable_card_ab_hold
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_handlers.py
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/orchestrator.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_legacy_setup_epoch_gate.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_write_gates_boundary.py
    enforcement:
      - textual
      - ai_review
    result: not_verified
    deviations: []

  - practice_id: testing
    applicability_reason: >
      Change adds state-changing write gates, freezes, and failure/replay-sensitive
      epoch paths; write-gate and honesty-of-assurance evidence must be locatable
      without treating local tests as full CI or production proof.
    selected_rule_ids:
      - TEST-002
      - TEST-004
    evidence_locators:
      - openspec/changes/card-ab-hold-mode/tasks.md
      - tests/unit/auto_updater_v3/card_ab_hold/test_write_gates_boundary.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_epoch_write_gates.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_epoch_pipelines_sync.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_concurrent_generation.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_auto_bid_freeze.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_stale_stats_freeze.py
      - .cursor/rules/testing-rules.mdc
      - openspec/policies/VERIFY_POLICY.md
    enforcement:
      - textual
      - ai_review
    result: not_verified
    deviations: []

  - practice_id: data-integrity
    applicability_reason: >
      Epoch lifecycle persists durable PG intent before WB sync, uses generation
      and idempotency keys, and requires activate-only completion semantics across
      PG/Redis/WB stores.
    selected_rule_ids:
      - DATA-001
      - DATA-003
      - DATA-004
    evidence_locators:
      - openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md
      - openspec/changes/card-ab-hold-mode/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_write.py::create_pending_intent_for_generation
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_write.py::activate_after_successful_sync
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_pipelines.py::process_ab_epoch
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_pipelines.py::sync_intent_to_wb
      - app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/redis_coordination.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_epoch_pipelines_sync.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_concurrent_generation.py
      - tests/unit/auto_updater_v3/card_ab_hold/test_epoch_lifecycle_pure.py
    enforcement:
      - textual
      - ai_review
    result: not_verified
    deviations: []

practice_candidates: []

not_migrate:
  - OD-05
  - ROOT-001 and BUGCASE verdicts
  - absence of CI or pre-commit
  - monitoring scope
  - active task completion state
  - .tmp paths
  - raw extraction or Navigator dumps
  - proposed-but-not-accepted decisions as practices
```

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`ab-hold-epoch-lifecycle-and-generation-ownership`, `ab-hold-confirmed-epoch-parameters-sot`; обновлён `card-ab-hold-write-path-ownership` §15–§18)
- [ ] implementation layer matches decision *(не применяется в этом PLAN_ONLY обновлении — `/opsx:apply` заблокирован до owner-авторизации; применённая MVP-1 часть §1–§14 remains verified as before)*
