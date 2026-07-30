## Why

При A/B-тесте карточки (инфографика / главное фото) CTR и конверсия зависят не только от креатива, но и от рекламного профиля РК: состав ключей, целевые позиции, Auto-участие/ставка и минус-профиль. Пока идёт обычный автоапдейтер — или пользователь меняет ключи/минус-фразы в боте/кабинете WB — тест становится «грязным»: непонятно, что дало прирост — креатив или смена рекламного профиля. Клиентам нужен self-service сценарий: явно выбрать и подтвердить ключи и целевые позиции, прогреть кампанию перед фиксацией, зафиксировать разрешённый минус-профиль, отдельно подтвердить участие и ставку Auto, отключить обновление ЦП, оставить биддер работающим — без ручной сборки legacy-флагов и без полного отключения бота.

Ранее (confirmed prod bug) Excel мог выставить `card_ab_hold_mode=active` без ENTER allowed-set snapshot; это уже устранено (§9 write-path decision, Excel write-path режима убран из MVP).

**Owner-approved обновление (этот `/opsx-update`, semantic SoT = owner-approved product requirements + CONTROL decisions, НЕ `REQ-AB-HOLD-BUDGET-SAFETY-001`):** ранее применённая MVP-1 модель фиксировала целевую позицию синхронно с автоматической классификацией ключа на ENTER — без отдельной стадии прогрева и без явных подтверждений пользователя. Владелец продукта требует другой флоу: явное подтверждение набора ключей → durable WARM_UP (не короче 24 часов) → раздельные подтверждения целевой позиции и Auto-параметров → durable намерение о запуске → синхронизация с WB → активный hold. Это отдельный слой над уже применённым MVP-1 enforcement (freeze минус-профиля, freshness/V3-only гейты, идемпотентный Enable) — этот change обновляет план (proposal/design/spec/decisions/tasks), не отменяя уже реализованное.

## What Changes

### Intent

Один paid automation-режим **A/B Hold**: явно подтверждённый пользователем набор ключей и целевых позиций приводит кампанию к стабильному профилю для теста карточки. Перед фиксацией целевых позиций кампания проходит durable стадию прогрева (WARM_UP, не короче 24 часов); после прогрева пользователь видит по каждому ключу факт-позицию и отдельно предложенную целевую позицию и подтверждает её; отдельно подтверждается участие и ставка Auto; затем система один раз синхронизирует WB и переводит кампанию в активный hold — **биддер продолжает работать** к подтверждённым целям, а обновление целевых позиций и структурные ACT-пути заморожены. UI сообщает «можно запускать A/B» только после успешной синхронизации WB. Enable/disable — только через paid Telegram UI. Daily-budget/activity-control переиспользуется как есть (не новая финансовая safety-модель). Раскатка — через ручной тест владельца и ограниченную opt-in бету; широкое включение — только после решения OD-05.

### Current behavior

- Ранее применённая MVP-1 модель: paid-only Telegram enable → freshness-гейт → V3-только гейт → soft-gate по объёму показов → hard-gate по плану max CPO → автоматическая PASS/FAIL классификация ключа по `pay_for_order ≤ max CPO` и `views ≥ 100` → на PASS целевая позиция синхронно фиксируется как текущая факт-позиция → фиксация разрешённого (allowed) набора фраз как PG snapshot → одна setup-синхронизация WB → `ACTIVE`.
- В `ACTIVE`: обновление целевых позиций и структурные ACT-пути (whitelist/enable/emergency/ordinary minus recalculation) заморожены; биддер продолжает работать; hold-enforcement удерживает разрешённый набор фраз (исключает новые/не-разрешённые, восстанавливает снятые вручную, в пределах WB minus cap — иначе видимая деградация).
- **Известный конфликт (OP-004 / planning fix OP-006):** legacy `process_ab_setup` на первом тике после Enable всё ещё может → `ACTIVE` и фиксировать TP на PASS — это **гонится** с owner WARM_UP/confirm-флоу. Pre-apply REQUIRED gate: `tasks.md` §18.4; planned Alembic fields: §19.5 / §22.5; Auto bid freeze MUST покрывать `AutoResetBidService`.
- Отсутствует отдельная стадия прогрева перед фиксацией целевой позиции: фиксация происходит на том же тике, что и классификация ключа.
- Отсутствует явное отдельное подтверждение пользователем целевой позиции, участия Auto и ставки Auto: участие/ставка Auto не входят в MVP-1 явный confirm-флоу.
- Отсутствует durable понятие «эпоха»/«generation» подтверждённых параметров: retry синхронизации не описан как переиспользование того же набора параметров без пересчёта.
- Freeze при stale/missing статистике описан для enable-гейта (§2a) и для allowed-set enforcement (§8), но не описан явно как freeze Search/Auto bid-мутаций на протяжении всего жизненного цикла режима.
- Daily budget / activity-control controller уже переиспользуется ортогонально (пауза/запуск кампании по budget/balance/schedule/rec_system не считается нарушением freeze), но честное раскрытие overshoot/daily-reset поведения как часть A/B Hold плана не описано.
- Search common bid (общая ставка аукциона): ordinary continuous updater может быть Forbidden under Hold (PBH-004 structural gate), но **owned one-shot reset-to-min на ENTER отсутствует** — elevated common bid может застыть as-is (gap закрывается decision §19 / tasks §27).

### Desired behavior

- Режим доступен **только paid** и **только через Telegram UI**; existing card_ab_hold UI (текущий MVP-1 экран) **не является референсом** для нового флоу — UX-контракт и Telegram storyboard создаются отдельно (см. Deferred).
- **Явное подтверждение набора ключей** запускает WARM_UP; ручное изменение набора ключей во время WARM_UP завершает текущий таймер и запускает новый (тот же попытки-цикл, не новая подтверждённая эпоха).
- **WARM_UP** — отдельная durable pre-epoch стадия: default длительность = 24 часа, минимум = 24 часа; пользователь MAY увеличить длительность, MUST NOT уменьшить её ниже 24 часов. Во время WARM_UP: без автоматического добавления новых ключей, без автоматического возврата исключённых ключей; safety-исключение (защита от перерасхода и подобные защитные причины) допускается; целевая позиция не фиксируется. Существующие пороги «≥100 показов/ключ» (eligibility) и «≥1000 суммарных показов кампании» (soft-gate объёма при enable) сохраняют текущую семантику и **не являются** длительностью WARM_UP.
- **После WARM_UP** экран/сообщение показывает по каждому ключу: факт (текущая фактическая позиция) → предложенная целевая позиция через `ab_hold_target_place_from_keyword(position)`. Факт-позиция и целевая позиция — отдельные семантические поля, отображаемые раздельно; их числовые значения могут совпасть после округления/сlamping, но это не повод сливать поля.
- Пользователь **явно подтверждает** предложенные целевые позиции. Подтверждённые целевые позиции — durable и immutable в пределах текущей эпохи; повторный запуск/ENTER их не пересчитывает; обычный дрейф факт-позиции после подтверждения не переоткрывает подтверждение.
- **Отдельно** от Search-подтверждений пользователь явно подтверждает **участие Auto** в тесте и, отдельным явным действием, **ставку Auto** на эпоху. Ни одно из этих подтверждений не подразумевается другим.
- После всех подтверждений система фиксирует **durable намерение о запуске (PENDING intent)** в базе — до какой-либо записи в WB. Затем один раз синхронизирует WB с подтверждёнными параметрами. Только после подтверждённо успешной синхронизации кампания переходит в активный hold; UI сообщает «можно запускать A/B» только на этом шаге.
- Частичная синхронизация WB (часть подтверждённых изменений применилась, часть — нет) — восстановимое состояние: кампания остаётся не-активной (не hold), сохраняя то же durable намерение; повторная попытка переиспользует тот же набор подтверждённых параметров без пересчёта целевых позиций/ставки Auto и без открытия новой эпохи.
- **В активном hold:** целевые позиции ключей не обновляются автоматически; биддер продолжает работать к подтверждённым целям и не добавляет/не возвращает ключи и не меняет целевые позиции самостоятельно; структурные ACT-пути (whitelist/enable/разгон/emergency) заморожены; hold-enforcement удерживает разрешённый набор фраз (как в MVP-1); мутаторы ставки Auto заморожены — их не меняет ordinary auto-update; **Search common bid (общая ставка аукциона)** сброшена на WB minimum на ENTER и дальше не меняется ordinary updater’ом (bidder/cluster ≠ common bid).
- **На ENTER** (`OFF` → `PENDING_SETUP`): owned A/B Hold path **один раз** сбрасывает Search common bid на WB minimum (холодные ключи + каталог); continuous ordinary `update_common_bid_in_search_adv` под Hold Forbidden.
- **При устаревшей/отсутствующей статистике** (по ключу или по кампании) во время WARM_UP, ожидания подтверждения или активного hold: включение/исключение ключей и мутации ставки Search/Auto замирают (freeze) — решения на «неизвестных» данных не принимаются; при этом устаревшая/отсутствующая статистика сама по себе **не является** причиной остановки кампании — это отдельное, более сильное действие, не выполняемое только из-за freeze.
- **Daily-budget / activity-control** переиспользуется как существующий контроллер без изменений: это стоп-порог (stop threshold), а не жёсткий лимит; перерасход относительно порога возможен (задержка статы, каданс воркера, in-flight траты, конкурентные write-пути, top-up без обрезки до остатка) и не имеет гарантированной числовой верхней границы; суточный сброс и возобновление трат на следующий день — ожидаемое поведение. Абсолютный тестовый бюджет, epoch spend cap, velocity cap, обобщённый financial latch, новая emergency-stop подсистема, global refill/restart suppression или отдельное «владение» финансовой безопасностью — **не** вводятся этим change.
- **Telegram UX** (планировочный уровень, без полного сторибоарда — см. Deferred): пагинация списков ключей с размером страницы 10; кнопка «Назад» сохраняет черновик текущего шага подтверждения; «Отмена» — отдельное явное действие (не совмещается с «Назад»).
- **Раскатка:** ручной тест владельца → ограниченная opt-in бета → структурированный сбор фидбэка → широкое включение только после принятия решения **OD-05**. OD-05 — единственное открытое owner-решение в этом обновлении.

### Scope in

- Explicit keyword-set confirmation как триггер WARM_UP; ручное изменение набора ключей во время WARM_UP сбрасывает таймер.
- Durable WARM_UP стадия: default/min 24 часа, увеличение разрешено, уменьшение ниже 24 часов запрещено; без авто-добавления/авто-возврата ключей; safety-исключение допускается; TP не фиксируется.
- После WARM_UP: раздельное отображение факт-позиции и предложенной целевой позиции (`ab_hold_target_place_from_keyword`); явное подтверждение целевых позиций; durable immutable TP в пределах эпохи; retry/дрейф не переоткрывают подтверждение.
- Отдельные явные подтверждения участия Auto и ставки Auto; заморозка ordinary auto-update мутаторов ставки Auto в активном hold.
- Durable PENDING intent до WB-мутации; одна WB-синхронизация подтверждённых параметров; переход в активный hold только после подтверждённо успешной синхронизации; partial sync — восстановимое не-активное состояние с сохранённым набором параметров; retry без пересчёта TP/Auto bid и без новой эпохи.
- Freeze keyword inclusion/exclusion и Search/Auto bid-мутаций при stale/missing статистике на протяжении WARM_UP/ожидания подтверждения/активного hold; без остановки кампании только по этой причине; **включая ENTER/setup FAIL→OFF** (decide-class; PBH-001); apply snapshot после durable PENDING intent — carve-out PBH-005.
- Soft-policy RU disclaimer (Enable и/или статус теста): временные сбои статы не должны ломать ровный тест через decide на «неизвестных» данных; пользователь следит за ходом; формулировка freeze-decide, не «ослабим защиту».
- **Search common bid:** ENTER one-shot reset-to-min (owned setup/ENTER path) + continuous ordinary common-bid freeze under Hold; bidder unchanged (decision §19 / tasks §27).
- Честное описание daily-budget/activity-control reuse (stop threshold, overshoot без гарантированной границы, суточный сброс) в плане; без новых бюджетных/emergency-stop механизмов.
- Telegram UX на уровне плана: пагинация 10, «Назад» сохраняет черновик, «Отмена» — отдельное действие.
- Ручной тест владельца + ограниченная opt-in бета как этапы раскатки; широкое включение блокируется до OD-05.
- Сохранение уже применённого MVP-1 enforcement (allowed-set freeze минус-профиля, Excel write-path removal, V3-only gate, idempotent Enable, hide-Enable keyboard, freshness/soft-volume/max-CPO gates, shared-defaults guard, PENDING liveness §14) как действующего фундамента, на который накладывается WARM_UP/confirm/epoch-слой.

### Out of scope

- Полный UX-контракт и Telegram storyboard для нового флоу подтверждений — создан этим `/opsx-continue`: `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` (экраны/состояния/клавиатуры/callback/переходы/Back-Cancel/pagination/stale-callback contract) и `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md` (сценарии по экранам); планирующие документы, не реализация — `/opsx:apply` для `tasks.md` §19–25 остаётся заблокирован до owner-авторизации.
- Pre-start safety policy picker (hard|soft|self) и anti-drain emergency kill switch — **не** текущий DoD; parked in `DOTO/WORKLOG.md` `[deferred-from:card-ab-hold-mode]` (future change, e.g. `ab-hold-safety-policy-modes`). Mid-sync stale UX (wait|force-apply|EXIT) — тоже parked, не owed.
- Monitoring/alerting и evidence-driven emergency stop — **OUT_OF_SCOPE_FOLLOW_ON**, не артефакт этого обновления.
- Абсолютный тестовый бюджет, epoch spend cap, velocity cap, generic financial latch, новая emergency-stop подсистема, global refill/restart suppression, отдельная финансовая safety-ownership decision — не вводятся; `REQ-AB-HOLD-BUDGET-SAFETY-001` и любая параллельная финансовая safety-модель — не текущий scope.
- Встроенный A/B инструмент Wildberries и интерпретация его метрик.
- Управление ценой товара и price-management клиента.
- Hard-block режима полок (только рекомендация в справке).
- Excel enable/disable/edit A/B Hold — уже вне MVP (см. применённый §9 write-path decision); не пересматривается этим обновлением.
- Owned авто-abort зависшего PENDING (после максимального числа неудачных retry) — по-прежнему SHOULD/future, вне текущего MVP.
- `/opsx:apply` в рамках этого `/opsx-update` — обновление только планирующих артефактов; реализация заблокирована до авторизации владельцем (см. `tasks.md`).

### Risk

Высокорисковая зона: ставки, целевые позиции, Auto-участие/ставка, V3 updater, WB write actions, перерасход/отсутствие трафика, гонка UI ready vs незавершённая синхронизация. Ошибки на этапе подтверждения могут привести к фиксации целевой позиции, которую пользователь не намеревался подтверждать; ошибки WARM_UP (слишком короткий прогрев, авто-добавление ключей) загрязняют тест; ошибки freeze при stale-стате могут либо принять решение на неизвестных данных, либо неправомерно остановить кампанию только из-за stale-статы; ошибка daily-budget disclosure может создать у пользователя ложное ощущение жёсткого лимита. Нужна координация между WARM_UP-таймером, подтверждениями и durable намерением, чтобы retry не пересчитывал уже подтверждённые параметры и не создавал новую эпоху без согласия пользователя.

### Rollback idea

Отключить режим на кампании (Telegram EXIT, как в применённом MVP-1) или не включать на новых; при проблеме с новым WARM_UP/confirm-слоем — не раскатывать широкий доступ (ручной тест владельца и лимитированная бета остаются единственными активными путями до OD-05); откат релиза — как в применённом MVP-1 (поле режима по умолчанию выкл, allowed-set snapshot cleared, Redis-ключи с TTL истекают, ordinary automation восстанавливается); durable WARM_UP-таймер и durable PENDING intent на кампании без активного hold не создают WB-побочных эффектов и очищаются при EXIT.

### Architecture Decision References

- Relevant accepted: `openspec/decisions/mode-defaults-policy-ownership/decision.md` — дефолт режима A/B Hold (выкл) и related paid/free overlays принадлежат declarative mode policy overlays, а не transition-helper.
- Proposed (this change, применённая часть — MVP-1): `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — ownership setup/hold write-path, structural freeze ACT, launch-validity soft-gate, allowed-set PG snapshot + hold enforcement, Excel write-path out of MVP, Telegram Enable idempotent, hide-Enable keyboard, V3-only + V2 exclusion, shared-defaults not-a-disable-path, PENDING_SETUP liveness; **обновлено этим change** новыми §15–§18: WARM_UP/epoch/generation ссылка, confirmed epoch-parameters SoT ссылка, stale-stats freeze для Search/Auto bid-мутаторов, daily-budget/activity-control ортогональный reuse; **дополнительно §19** Search common bid reset-to-min on ENTER then freeze.
- Proposed (this change, новый слой): `openspec/changes/card-ab-hold-mode/decisions/ab-hold-epoch-lifecycle-and-generation-ownership/decision.md` — WARM_UP durable pre-epoch стадия, epoch/generation модель, durable PENDING-до-WB порядок, partial-sync recovery, idempotent same-generation retry.
- Proposed (this change, новый слой): `openspec/changes/card-ab-hold-mode/decisions/ab-hold-confirmed-epoch-parameters-sot/decision.md` — confirmed keyword set / confirmed target places / confirmed Auto participation / confirmed Auto bid как durable SoT, отдельно от факт-позиции; immutable TP в пределах эпохи; Auto bid мутаторы заморожены в активном hold.

## Capabilities

### New Capabilities

- `card-ab-hold-mode`: paid-only режим A/B Hold (`bot_active is True`; при False — UI скрыт, enable запрещён) — Telegram-only enable/disable; **обновлённый флоу**: явное подтверждение набора ключей → durable WARM_UP (default/min 24ч, ручное изменение набора сбрасывает таймер) → раздельное отображение факт-позиции/предложенной целевой позиции (`ab_hold_target_place_from_keyword`) → явное подтверждение целевых позиций (durable, immutable в пределах эпохи) → отдельное явное подтверждение участия Auto → отдельное явное подтверждение ставки Auto → durable PENDING intent → одна WB-синхронизация → активный hold только после успешной синхронизации (partial sync — восстановимое не-активное состояние; retry — тот же generation и параметры без пересчёта); в активном hold — ЦП зафиксированы, биддер работает, структурные ACT-пути и Auto bid мутаторы заморожены, hold-enforcement удерживает разрешённый набор фраз; freeze keyword inclusion/exclusion и Search/Auto bid-мутаций при stale/missing статистике без остановки кампании только по этой причине; daily-budget/activity-control переиспользуется как есть (stop threshold, честный overshoot, суточный сброс); UI ready только после активного hold; EXIT возвращает ordinary automation; Telegram UX на уровне плана — пагинация 10, «Назад» сохраняет черновик, «Отмена» — отдельное действие; раскатка через ручной тест владельца → лимитированную opt-in бету → OD-05 для широкого включения.

### Modified Capabilities

- Нет (в `openspec/specs/` пока нет связанных capabilities с requirement-level изменениями; delta продолжает жить в `specs/card-ab-hold-mode/spec.md` этого change).

## Impact

Затрагивает paid automation shop-runner (WARM_UP-таймер, планирование setup/hold/confirm-write-path, freeze Search/Auto bid-мутаций при stale stats), координацию bot ↔ runner через Redis/PG (durable epoch/generation, PENDING intent), состояние кампании в БД (WARM_UP-таймер, confirmed epoch-параметры, allowed-set snapshot), Telegram UI (новый confirm-флоу — контракт `openspec/changes/card-ab-hold-mode/ux/telegram-ux-contract.md` и сторибоард `openspec/changes/card-ab-hold-mode/ux/telegram-storyboard.md`, созданы этим `/opsx-continue`), daily-budget/activity-control disclosure (без изменения самого контроллера). Не расширяет Free path. Реализация (`/opsx:apply`) заблокирована до авторизации владельцем; широкое включение — только после OD-05.
