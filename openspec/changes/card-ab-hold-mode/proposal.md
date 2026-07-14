## Why

При A/B-тесте карточки (инфографика / главное фото) CTR и конверсия зависят не только от креатива, но и от рекламного профиля РК: состав ключей, белый список, целевые позиции, ставки и **минус-фразы**. Пока идёт обычный автоапдейтер — или пользователь меняет минус-фразы в боте / кабинете WB — тест становится «грязным»: непонятно, что дало прирост — креатив или смена рекламного профиля. Клиентам нужен self-service сценарий: зафиксировать целевые позиции и минус-профиль, отключить обновление ЦП, оставить биддер работающим — без ручной сборки legacy-флагов и без полного отключения бота.

Дополнительно (confirmed prod bug): Excel мог выставить `card_ab_hold_mode=active` без ENTER minus sync+snapshot — hold restore и UI ready становились небезопасными. Excel write-path режима убираем из MVP.

## What Changes

### Intent

Один paid automation-режим **A/B Hold**: один раз привести РК к стабильному профилю для теста карточки; на период теста **зафиксировать позиции** (целевая позиция = текущая фактическая), **зафиксировать минус-фразы** (PG snapshot + restore при drift) и **отключить обновление целевых позиций**, при этом **биддер продолжает работать**; UI сообщает «можно запускать A/B» **только после** полного setup (ACTIVE); enable/disable **только через paid Telegram UI**; при выключении режима снова включить обновление ЦП, ordinary апдейтеры и ordinary minus auto-update — без restore keyword-profile / Excel snapshot (minus PG snapshot clear/archive).

### Current behavior

- Автоапдейтер (V2/V3) на каждом тике может менять whitelist, целевые позиции, режимы ключей и включать новые ключи.
- Ordinary auto-update минус-фраз и ручные правки в боте / кабинете WB могут менять минус-набор во время теста без привязки к hold.
- Типичный «ручной» обход — выключить `bot_active` целиком: тогда останавливается и updater. Это не подходит для A/B: **биддер в режиме A/B Hold останавливать нельзя — он MUST продолжать работать**; полный off бота как способ «заморозить» РК недопустим.
- Ручное выключение отдельных auto-флагов для V3 не даёт явного «ЦП зафиксированы + обновление ЦП выкл + биддер ON + минус зафиксирован» и не гарантирует чистый setup; между подами bot и shop-runner нет согласованного прерывания текущего тика.
- Excel roundtrip мог применять `card_ab_hold_mode` (в т.ч. `active`) минуя `process_ab_setup` / minus snapshot.

### Desired behavior

- Режим доступен **только paid** и **только через Telegram UI**: при `bot_active is False` пункт меню / экран A/B Hold MUST быть **скрыт**; enable MUST NOT выполняться. При `bot_active is True` — экран инструкции и кнопки включить / выключить / назад.
- **Excel MUST NOT** экспортировать / импортировать / применять `card_ab_hold_mode` в MVP (колонки нет; leftover payload ignored). Идея Excel-колонки — **future**, не текущий контракт.
- **Включение (enable) дополнительно ограничено здоровьем статы РК:** если кампания не проходит тот же класс проверки свежести/получения статистики, что `_split_advs_by_stats_freshness` / `advs_filtred`, enable MUST NOT выполняться. В UI пользователь MUST сразу видеть **причину**, текст **ограничения** и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (в коде нет `ADMIN`; whitelist — `ADMINS`; публичная ссылка — `SUPPORT_LINK`).
- **После успешного переключения** (PENDING_SETUP / ACTIVE) сбои свежести статы **не** должны блокировать scheduling `process_ab_setup` / `process_ab_hold` (не оставлять вечный PENDING из‑за `advs_filtred`).
- **ENTER:** система один раз готовит профиль РК (включая минус-фразы), затем переводит кампанию в hold (**ACTIVE**). Прямой `ACTIVE` любым non-setup путём — Forbidden.
- **Критерий setup (ENTER):**
  - PASS: `pay_for_order` ключа **≤ max CPO плана** (не resolve) **и** показов за недельное окно статистики ключа (тот же источник, что в карточке ключа) **≥ 100**;
  - FAIL (иначе, включая отсутствие `pay_for_order`): ключ **OFF** (выключается / снимается с БС);
  - для PASS: целевая позиция фиксируется на **текущей** позиции; состав БС после setup считается зафиксированным;
  - **минус-фразы:** сначала успешно довести до актуального состояния (одна setup sync/mutation, не ordinary recalculation loop); сохранить snapshot в PG (**новая Alembic migration**); только после этого (и остального setup) mode MAY → **ACTIVE**.
- **UI readiness:** интерфейс MUST NOT сообщать, что режим включён и можно запускать A/B, пока mode ≠ **ACTIVE** после полного setup (включая минус + snapshot). PENDING / «запрос принят» без ACTIVE — не «можно тестировать»; координация исключает гонку с незавершённым setup.
- **HOLD:** целевые позиции остаются теми, что зафиксированы на ENTER; **обновление целевых позиций выключено**; **биддер продолжает работать**; структурные изменения БС / разгон / enable ключей не выполняются; ordinary recalculation минус-фраз **не** выполняется; при drift от PG snapshot — restore на WB (ручные правки = нарушение freeze); допускаются только защиты от перерасхода относительно max CPO.
- **EXIT:** режим снимается (Telegram disable) — снова **включается обновление целевых позиций**, ordinary structural апдейтеры и ordinary minus auto-update; PG minus snapshot clear/archive; restore keyword-profile / Excel snapshot **не** требуется.
- Координация между bot-подом и shop-runner-подом идёт через Redis-сигнал прерывания: текущий normal-тик может быть остановлен до apply с ответом «остановлено, безопасно, можно продолжать».
- В справке MUST быть: перед включением прогреть РК с не зажатым max CPO и запасом плана продаж; полки рекомендуется выключить (не hard block); не менять цену на период теста; **«Во время A/B Hold минус-фразы фиксируются. Ручные изменения в кабинете WB могут быть возвращены ботом к зафиксированному состоянию. Чтобы изменить минус-фразы, отключите A/B Hold.»**

### Scope in

- Paid-only access: UI скрыт при `bot_active is False`; Telegram enable/disable гейтятся тем же условием.
- Enable gate на freshness/health статы РК + явный UI-ответ (причина, ограничение, `SUPPORT_LINK`).
- После PENDING/ACTIVE: setup/hold не зависят от `advs_filtred` freshness filter.
- Paid bot UI: экран инструкции (вкл. текст минус-freeze) + вкл/выкл; ready-to-test только после ACTIVE.
- Состояния режима кампании (выкл / подготовка / активен).
- Setup ENTER + hold + exit для V3 (paid automation), включая minus sync → PG snapshot → ACTIVE.
- PG durable minus-phrase snapshot (**новая migration**) + restore-on-drift + clear на EXIT.
- Gate ordinary `update_minus_phrases` / recalculation при PENDING_SETUP / ACTIVE.
- Cross-pod Redis coordination (signal / abort ack / setup lock) по project Redis-паттернам.
- ACT-защита параллельных structural write-путей на время режима (WL/TP/enable/emergency + minus).
- **Удаление Excel `card_ab_hold_mode` column/apply** (ignore leftover payload).
- Тесты-first: structural freeze + minus snapshot/restore + UI not-ready on PENDING + paid visibility + freshness enable + post-enter schedule + Excel import ignore.

### Out of scope

- Встроенный A/B инструмент Wildberries и интерпретация его метрик.
- Управление ценой товара и price-management клиента.
- Hard-block режима полок (только рекомендация в справке).
- Обязательный backup/restore keyword-settings / Excel snapshot при выходе (минус PG snapshot — **in scope**, это freeze-механизм, не Excel backup).
- Safe mode / pull-down при ухудшении экономики (отдельная идея из WORKLOG).
- Free bot / `bot_active is False`: режим — paid automation core; UI MUST быть скрыт; enable MUST NOT выполняться.
- Изменение алгоритма обычного V3 preamble вне ветки A/B Hold.
- **Excel enable/disable/edit A/B Hold** — **future** (идея сохранена; не MVP).

### Risk

High-risk зона: ставки, CPO/CPA, V3 updater, ApplyManager, WB write actions (вкл. set minus), перерасход / отсутствие трафика, гонка UI ready vs PENDING, Excel→ACTIVE без snapshot (mitigated by removing Excel path). Ошибки setup могут массово выключить ключи с малой статистикой; ошибки hold могут «протечь» в normal updater / ordinary minus или перезаписать ручные минус-правки; слишком ранний UI «можно тестировать» загрязняет эксперимент. Нужна координация multi-pod и regression gates.

### Rollback idea

Выключить режим на кампании (Telegram EXIT) или не включать на новых; при проблеме — откат релиза: поле режима по умолчанию выкл, minus snapshot unused/cleared, Redis-ключи с TTL сами истекают, ordinary V3 и ordinary minus scheduling восстанавливаются.

### Architecture Decision References

- Relevant accepted: `openspec/decisions/mode-defaults-policy-ownership/decision.md` — дефолт режима A/B Hold (выкл) и related paid/free overlays (в т.ч. minus defaults) принадлежат declarative mode policy overlays, а не transition-helper.
- Proposed (this change): `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — ownership setup/hold write-path, structural freeze ACT, **§8 minus PG snapshot + restore + UI readiness after ACTIVE**, **§9 Excel write-path out of MVP**, PG vs Redis, paid-only Telegram enable.

## Capabilities

### New Capabilities

- `card-ab-hold-mode`: paid-only режим A/B Hold (`bot_active is True`; при False — UI скрыт, enable запрещён) — Telegram-only enable/disable, enable gate freshness статы + UI reason/`SUPPORT_LINK`, ENTER (PFO ≤ max CPO + ≥100 показов, FAIL→OFF, ЦП := текущая; minus sync → PG snapshot → ACTIVE), HOLD (ЦП freeze, биддер ON, minus freeze+restore, guard перерасхода; post-enter без блокировки только из‑за `advs_filtred`), UI ready только после ACTIVE, EXIT (снова ЦП + апдейтеры + ordinary minus; clear minus snapshot; без keyword-profile restore), UI-инструкция (текст минус-freeze), **без Excel column**, cross-pod interrupt.

### Modified Capabilities

- Нет (в `openspec/specs/` пока нет связанных capabilities с requirement-level изменениями).

## Impact

Затрагивает paid automation shop-runner (планирование V3 vs hold/setup, gate `update_minus_phrases`), координацию bot ↔ runner через Redis, состояние кампании в БД (minus snapshot), Telegram UI (инструкция + ready after ACTIVE), **Excel roundtrip (remove column/apply)**, тестовый контур write-gates. Не расширяет Free path. План снова впереди кода: нужен `/opsx-apply` для delta «Excel out».
