## Why

При A/B-тесте карточки (инфографика / главное фото) CTR и конверсия зависят не только от креатива, но и от рекламного профиля РК: состав ключей, белый список, целевые позиции, ставки и **минус-фразы**. Пока идёт обычный автоапдейтер — или пользователь меняет минус-фразы в боте / кабинете WB — тест становится «грязным»: непонятно, что дало прирост — креатив или смена рекламного профиля. Клиентам нужен self-service сценарий: зафиксировать целевые позиции и минус-профиль, отключить обновление ЦП, оставить биддер работающим — без ручной сборки legacy-флагов и без полного отключения бота.

Дополнительно (confirmed prod bug): Excel мог выставить `card_ab_hold_mode=active` без ENTER allowed-set snapshot — hold enforcement и UI ready становились небезопасными. Excel write-path режима убираем из MVP.

## What Changes

### Intent

Один paid automation-режим **A/B Hold**: один раз привести РК к стабильному профилю для теста карточки; на период теста **зафиксировать позиции** (целевая позиция = текущая фактическая), **зафиксировать разрешённый (relevant) набор фраз** (PG allowed-set snapshot; во время hold исключать любые новые/не-разрешённые фразы, чтобы поверхность трат оставалась постоянной — минус как производный enforcement) и **отключить обновление целевых позиций**, при этом **биддер продолжает работать**; UI сообщает «можно запускать A/B» **только после** полного setup (ACTIVE); enable/disable **только через paid Telegram UI**; при выключении режима снова включить обновление ЦП, ordinary апдейтеры и ordinary minus auto-update — без restore keyword-profile / Excel snapshot (allowed-set snapshot clear).

### Current behavior

- Автоапдейтер (V2/V3) на каждом тике может менять whitelist, целевые позиции, режимы ключей и включать новые ключи.
- Ordinary auto-update минус-фраз и ручные правки в боте / кабинете WB могут менять минус-набор во время теста без привязки к hold.
- Типичный «ручной» обход — выключить `bot_active` целиком: тогда останавливается и updater. Это не подходит для A/B: **биддер в режиме A/B Hold останавливать нельзя — он MUST продолжать работать**; полный off бота как способ «заморозить» РК недопустим.
- Ручное выключение отдельных auto-флагов для V3 не даёт явного «ЦП зафиксированы + обновление ЦП выкл + биддер ON + минус зафиксирован» и не гарантирует чистый setup; между подами bot и shop-runner нет согласованного прерывания текущего тика.

### Desired behavior

- Режим доступен **только paid** и **только через Telegram UI**: при `bot_active is False` пункт меню / экран A/B Hold MUST быть **скрыт**; enable MUST NOT выполняться. При `bot_active is True` — экран инструкции; **Disable / Back всегда**; **Enable обязательно при mode `OFF`**; при `PENDING_SETUP` / `ACTIVE` Enable **MAY быть скрыт** (Disable/Back остаются); если Enable всё же нажат — **idempotent no-op** (§10).
- **Excel MUST NOT** экспортировать / импортировать / применять `card_ab_hold_mode` в MVP (колонки нет; leftover payload ignored). Идея Excel-колонки — **future**, не текущий контракт.
- **Включение (enable) дополнительно ограничено здоровьем статы РК:** если кампания не проходит тот же класс проверки свежести/получения статистики, что `_split_advs_by_stats_freshness` / `advs_filtred`, enable MUST NOT выполняться. В UI пользователь MUST сразу видеть **причину**, текст **ограничения** и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (в коде нет `ADMIN`; whitelist — `ADMINS`; публичная ссылка — `SUPPORT_LINK`).
- **После успешного переключения** (PENDING_SETUP / ACTIVE) сбои свежести статы **не** должны блокировать scheduling `process_ab_setup` / `process_ab_hold` (не оставлять вечный PENDING из‑за `advs_filtred`).
- **Жёсткий гейт плана max CPO на enable:** если план `max_price_for_order` отсутствует или ≤ 0, enable MUST NOT переводить в `PENDING_SETUP` (mode остаётся `OFF`) — иначе setup-тик детерминированно не сможет завершиться, а кампания уже исключена из ordinary automation (вечный semi-frozen PENDING). Пользователь видит **причину** (нужен положительный план max CPO) и **рекомендацию** задать и повторить. Гейт рядом с freshness (§2a) и V3-only (§12), **до** soft-gate объёма (§2c).
- **Мягкое предупреждение о слабом объёме теста (soft-gate):** при enable, если **измеренная** Σ показов keyword-clusters кампании (**campaign-level proxy** через `get_keywords_views_by_days` / `mv_clusters_daily_agg`; зерно — календарные дни MV, покрывающие last-24h wall-clock) ниже порога, система MUST NOT включать молча — показывает **причину** (мало показов для надёжного A/B), **рекомендацию** поднять план max CPO и повторить, и **выбор** «всё равно запустить» / «отмена» (пользователь MAY продолжить на свой риск). При CH unavailable / query error — **отдельный soft reason** (объём временно недоступен), mode `OFF`, без ENTER; MUST NOT трактовать ошибку как 0 показов. Keyword-filtered Σ по setup-кандидатам и true rolling 24h — out of MVP / future. Это отдельный soft-gate, не hard block (в отличие от freshness) и не пустой allowed-set.
- **ENTER:** система один раз готовит профиль РК (включая минус-фразы), затем переводит кампанию в hold (**ACTIVE**). Прямой `ACTIVE` любым non-setup путём — Forbidden. Telegram Enable при уже `PENDING_SETUP` / `ACTIVE` — **no-op** (не demote в PENDING, не rewrite Redis ENTER, не re-run ENTER force allowed-set sync); новый ENTER только после EXIT → `OFF`.
- **Критерий setup (ENTER):**
  - PASS: `pay_for_order` ключа **≤ max CPO плана** (не resolve) **и** показов за недельное окно статистики ключа (тот же источник, что в карточке ключа) **≥ 100**;
  - FAIL (иначе, включая отсутствие `pay_for_order`): ключ **OFF** (выключается / снимается с БС);
  - для PASS: целевая позиция фиксируется на **текущей** позиции; состав БС после setup считается зафиксированным;
  - **разрешённые фразы (allowed-set freeze):** зафиксировать разрешённый набор фраз кампании (relevant-фразы + получившийся GOOD/whitelist профиль ключей) как durable PG allowed-set snapshot (**новая Alembic migration**); одной setup sync/mutation привести WB к этому состоянию (исключить всё вне allowed-set в пределах WB minus cap, не ordinary recalculation loop); только после успешной записи snapshot и остального setup mode MAY → **ACTIVE**. Заморозке подлежит **источник** (allowed-set); минус-фразы — производный механизм исключения.
- **UI readiness:** интерфейс MUST NOT сообщать, что режим включён и можно запускать A/B, пока mode ≠ **ACTIVE** после полного setup (включая allowed-set snapshot). PENDING / «запрос принят» без ACTIVE — не «можно тестировать»; координация исключает гонку с незавершённым setup.
- **Liveness PENDING_SETUP:** кампания MUST NOT застревать в молчаливом вечном PENDING (semi-frozen: вне ordinary automation, не ACTIVE). Детерминированный блок setup, видимый только на тике (пустой allowed-set / нет non-BAD ключей; либо пропавший после enable max CPO), MUST surфейситься **actionable-причиной и действием** (поднять max CPO / нет подходящих ключей / отключить A/B Hold), а не generic «Подготовка…»; **EXIT доступен всегда** (→ OFF, возврат ordinary automation). Owned авто-abort зависшего PENDING → **future**.
- **HOLD:** целевые позиции остаются теми, что зафиксированы на ENTER; **обновление целевых позиций выключено**; **биддер продолжает работать**; структурные изменения БС / разгон / enable ключей не выполняются; ordinary recalculation (пересчёт GOOD/BAD по свежей стате и изменение allowed-set) **не** выполняется — allowed-set заморожен; **отдельно** hold-protection исключает любые новые/не-разрешённые фразы, появившиеся после ENTER, и восстанавливает разрешённые фразы, снятые вручную, — удерживая поверхность трат равной замороженному allowed-set (минус как enforcement, в пределах WB minus cap; при превышении cap или open-match РК — видимая деградация, а не тихий чистый hold); ручные правки = нарушение freeze, перезаписываются; допускаются только защиты от перерасхода относительно max CPO; manual bot refresh «Обновить минус-слова» при freeze MUST NOT врать success — MUST сообщить blocked / отключите A/B Hold.
- **EXIT:** режим снимается (Telegram disable) — снова **включается обновление целевых позиций**, ordinary structural апдейтеры и ordinary minus auto-update; PG allowed-set snapshot clear; restore keyword-profile / Excel snapshot **не** требуется.
- **Manual Telegram target_place write-path:** при `PENDING_SETUP`/`ACTIVE` ручная запись `KeywordSetting.target_place` блокируется до PG write/commit, FSM очищается и пользователь получает объяснение; при `OFF` поведение manual target_place остаётся прежним.
- Координация между bot-подом и shop-runner-подом идёт через Redis-сигнал прерывания: текущий normal-тик может быть остановлен до apply с ответом «остановлено, безопасно, можно продолжать».
- В справке MUST быть: перед включением прогреть РК с не зажатым max CPO и запасом плана продаж; полки рекомендуется выключить (не hard block); не менять цену на период теста; **«Во время A/B Hold набор рекламных фраз зафиксирован: новые фразы автоматически исключаются, а ручные изменения в кабинете WB могут быть возвращены ботом к зафиксированному набору. Чтобы изменить набор фраз, отключите A/B Hold.»** (текст MUST оставаться scoped/best-effort и не обещать полную заморозку всех фраз вне зависимости от типа РК / лимита минус-фраз WB)

### Scope in

- Paid-only access: UI скрыт при `bot_active is False`; Telegram enable/disable гейтятся тем же условием.
- Enable gate на freshness/health статы РК + явный UI-ответ (причина, ограничение, `SUPPORT_LINK`).
- Enable soft-gate на объём теста: campaign-level proxy Σ (calendar-day MV cover last-24h) + рекомендация поднять max CPO + выбор «всё равно запустить / отмена»; CH-error → distinct soft reason (реюз `get_keywords_views_by_days`).
- Enable hard-gate плана max CPO (`> 0`): при отсутствии / ≤ 0 — mode остаётся `OFF` + actionable причина (нужен положительный план max CPO).
- Liveness PENDING_SETUP: actionable non-ready причина при детерминированном блоке setup (пустой allowed-set / нет non-BAD ключей / пропавший max CPO) + всегда доступный EXIT (owned авто-abort — future, без новой миграции в MVP).
- После PENDING/ACTIVE: setup/hold не зависят от `advs_filtred` freshness filter.
- Paid bot UI: экран инструкции (вкл. текст минус-freeze) + Disable/Back; Enable при OFF (MAY hide при PENDING/ACTIVE); ready-to-test только после ACTIVE; Enable handler idempotent; honest UX на manual minus refresh при freeze (не «Минус-слова обновлены»).
- Состояния режима кампании (выкл / подготовка / активен).
- Setup ENTER + hold + exit для V3 (paid automation), включая allowed-set capture → PG snapshot → ACTIVE.
- PG durable allowed-set snapshot (**новая migration**) + hold enforcement (исключение новых/не-разрешённых фраз, в пределах WB minus cap; иначе видимая деградация) + clear на EXIT.
- Gate ordinary `update_minus_phrases` / recalculation при PENDING_SETUP / ACTIVE.
- Cross-pod Redis coordination (signal / abort ack / setup lock) по project Redis-паттернам.
- ACT-защита параллельных structural write-путей на время режима (WL/TP/enable/emergency + minus).
- **Удаление Excel `card_ab_hold_mode` column/apply** (ignore leftover payload).
- Тесты-first: structural freeze + allowed-set snapshot/enforcement (вкл. WB cap visible degradation) + UI not-ready on PENDING + paid visibility + freshness enable + post-enter schedule + Excel import ignore.

### Out of scope

- Встроенный A/B инструмент Wildberries и интерпретация его метрик.
- Управление ценой товара и price-management клиента.
- Hard-block режима полок (только рекомендация в справке).
- Обязательный backup/restore keyword-settings / Excel snapshot при выходе (allowed-set PG snapshot — **in scope**, это freeze-механизм, не Excel backup).
- Safe mode / pull-down при ухудшении экономики (отдельная идея из WORKLOG).
- Free bot / `bot_active is False`: режим — paid automation core; UI MUST быть скрыт; enable MUST NOT выполняться.
- Изменение алгоритма обычного V3 preamble вне ветки A/B Hold.
- **Excel enable/disable/edit A/B Hold** — **future** (идея сохранена; не MVP).
- Keyword-filtered launch-validity Σ только по setup non-BAD / would-carry-test ключам — **future** (MVP = campaign-level proxy).
- True rolling 24h hour-buckets для soft-gate объёма поверх daily MV — **future** (MVP = calendar-day cover last-24h wall-clock).

### Risk

High-risk зона: ставки, CPO/CPA, V3 updater, ApplyManager, WB write actions (вкл. set minus), перерасход / отсутствие трафика, гонка UI ready vs PENDING, Excel→ACTIVE без snapshot (mitigated by removing Excel path). Ошибки setup могут массово выключить ключи с малой статистикой; ошибки hold могут «протечь» в normal updater / ordinary recalc allowed-set, не исключить новые фразы (грязный тест) или перезаписать осознанные ручные правки; при превышении WB minus cap / open-match РК чистота hold не гарантирована (нужна видимая деградация); слишком ранний UI «можно тестировать» загрязняет эксперимент. Нужна координация multi-pod и regression gates.

### Rollback idea

Выключить режим на кампании (Telegram EXIT) или не включать на новых; при проблеме — откат релиза: поле режима по умолчанию выкл, allowed-set snapshot cleared, Redis-ключи с TTL сами истекают, ordinary V3 и ordinary minus scheduling восстанавливаются.

### Architecture Decision References

- Relevant accepted: `openspec/decisions/mode-defaults-policy-ownership/decision.md` — дефолт режима A/B Hold (выкл) и related paid/free overlays (в т.ч. minus defaults) принадлежат declarative mode policy overlays, а не transition-helper.
- Proposed (this change): `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — ownership setup/hold write-path, structural freeze ACT, **§2c launch-validity soft-gate (campaign-level proxy + calendar-day MV cover last-24h → warn + max-CPO recommendation + launch-anyway/cancel; CH-error → distinct soft reason)**, **§8 allowed-set PG snapshot + hold enforcement (минус — derived; WB cap visible degradation) + UI readiness after ACTIVE**, **§9 Excel write-path out of MVP**, **§10 Telegram Enable idempotent while PENDING/ACTIVE**, **§11 MAY hide Enable keyboard while PENDING/ACTIVE**, **§14 PENDING_SETUP liveness (max-CPO enable hard-gate + actionable PENDING reason + EXIT recovery; owned auto-abort future)**, PG vs Redis, paid-only Telegram enable.

## Capabilities

### New Capabilities

- `card-ab-hold-mode`: paid-only режим A/B Hold (`bot_active is True`; при False — UI скрыт, enable запрещён) — Telegram-only enable/disable, **Enable idempotent while PENDING/ACTIVE**, **keyboard MAY hide Enable while PENDING/ACTIVE (Disable/Back remain)**, enable gate freshness статы + UI reason/`SUPPORT_LINK`, ENTER (PFO ≤ max CPO + ≥100 показов, FAIL→OFF, ЦП := текущая; allowed-set capture → PG snapshot → ACTIVE), HOLD (ЦП freeze, биддер ON, allowed-set freeze + enforcement исключения новых/не-разрешённых фраз [WB cap → visible degradation], guard перерасхода; post-enter без блокировки только из‑за `advs_filtred`), UI ready только после ACTIVE, EXIT (снова ЦП + апдейтеры + ordinary minus + allowed-set recalc; clear allowed-set snapshot; без keyword-profile restore), UI-инструкция (текст фиксации набора фраз, scoped/best-effort), **без Excel column**, cross-pod interrupt.

### Modified Capabilities

- Нет (в `openspec/specs/` пока нет связанных capabilities с requirement-level изменениями).

## Impact

Затрагивает paid automation shop-runner (планирование V3 vs hold/setup, gate `update_minus_phrases`), координацию bot ↔ runner через Redis, состояние кампании в БД (allowed-set snapshot), Telegram UI (инструкция + ready after ACTIVE + Enable idempotent + hide Enable on PENDING/ACTIVE), **Excel roundtrip (remove column/apply)**, тестовый контур write-gates. Не расширяет Free path.
