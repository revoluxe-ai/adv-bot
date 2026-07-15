## Context

Клиентам нужен paid self-service режим для «чистого» A/B-теста карточки: зафиксировать целевые позиции по текущей фактической позиции, отключить обновление ЦП, оставить биддер работающим, не полагаясь на полный `bot_active=False` и не на хрупкую комбинацию legacy-флагов.

Сегодня ordinary V3 (`adv_settings_auto_update` → `process_adv_v3`) и параллельные ACT-корутины (whitelist top-key, individual target place, emergency, и т.д.) могут менять ключи/БС/ЦП в любой тик. Bot и shop-runner крутятся в разных подах — нужен Redis cooperative interrupt, чтобы ENTER не смешался с уже идущим normal apply.

Стек: Python 3.11, SQLAlchemy + PostgreSQL, Redis (паттерн `AdvSettingRedisCache` / `RedisCacheBase`, lock через `RedisLockManager`), Telegram paid UI. Режим — paid automation core: enable/disable только через Telegram при `bot_active is True`. Excel roundtrip **не** является write-path режима в MVP (future).

## Goals / Non-Goals

**Goals:**

- Durable режим кампании: OFF / PENDING_SETUP / ACTIVE в PG.
- ENTER: setup по `pay_for_order ≤ max CPO` и `views ≥ 100` (окно как в карточке ключа); FAIL → OFF; PASS → ЦП := текущая фактическая; БС фиксируется по итогу setup.
- ENTER allowed-set: зафиксировать разрешённый набор фраз → PG allowed-set snapshot (новая Alembic migration) → одна setup sync привести WB к allowed-set → только затем setup MAY → ACTIVE.
- HOLD: обновление ЦП выкл; биддер ON; structural ACT freeze (WL/TP/enable/emergency + ordinary allowed-set recalc); hold enforcement исключает новые/не-разрешённые фразы к замороженному allowed-set (минус как enforcement, WB cap → иначе видимая деградация); только guard перерасхода vs max CPO.
- UI readiness: «режим включён / можно запускать A/B» только после ACTIVE (полный setup, в т.ч. allowed-set snapshot); не на PENDING; без гонки.
- EXIT: снова обновление ЦП + ordinary апдейтеры + ordinary minus auto-update + allowed-set recalc; clear/archive PG allowed-set snapshot; без restore keyword-profile / Excel snapshot.
- Cross-pod Redis: signal ENTER/EXIT, last-abort ack, setup lock NX.
- Paid-only Telegram UI (скрыть при `bot_active is False`) + reject enable.
- Enable gate на stats freshness/health (тот же класс, что `advs_filtred`); UI: причина + ограничение + `const.SUPPORT_LINK`.
- A/B Hold — только V3 auto-updater: enable при `automatic_version != 3` blocked (mode остаётся OFF + причина); пока PENDING/ACTIVE — запрет переключения на V2 (сначала EXIT → OFF). V2 `change_adv_strategy` (MIN_CPO/MAX_CONV) — вне A/B Hold freeze; held V3-профиль не управляется этим полем.
- После PENDING/ACTIVE: setup/hold scheduling не зависит от попадания в `advs_filtred`.
- **Excel: колонка/apply `card_ab_hold_mode` убраны из MVP** (ignore leftover payload; future option).
- Instruction: набор рекламных фраз зафиксирован (новые исключаются); ручные правки в WB MAY быть возвращены; изменить набор → отключить A/B Hold; без обещания полной заморозки вне scope типа РК / WB cap.
- Tests-first gates: structural freeze, allowed-set snapshot/enforcement (вкл. WB cap visible degradation), UI not-ready on PENDING, paid visibility, interrupt до apply, freshness enable + post-enter schedule + Excel ignore.

**Non-Goals:**

- Встроенный A/B WB, price management, hard-block полок, Safe mode.
- Free path / enable при `bot_active is False`.
- Переписывание ordinary V3 preamble вне отдельного hold/setup path.
- Обязательный Excel backup / restore keyword-settings при EXIT (allowed-set snapshot — отдельный freeze-механизм, не Excel backup).
- **Excel enable/disable/edit A/B Hold** — future / out of MVP (идея сохранена; текущий контракт — только Telegram).

## Architecture Decision References

Architecture Decisions Found:

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — Status: Accepted. Дефолт «A/B Hold выкл» при paid/free overlays принадлежит declarative mode policy overlays, не transition-helper / UI.
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — Status: Proposed. Ownership setup/hold write-path, exclusion из ordinary V3, structural freeze (вкл. минус-фразы), PG vs Redis, paid-only Telegram enable, bidder MUST оставаться работающим; stats freshness asymmetry; **§2c** launch validity soft-gate (низкий объём показов 24ч → warn + raise-max-CPO recommendation + launch-anyway/cancel); **§8** allowed-set PG snapshot + hold enforcement (минус — derived; WB cap visible degradation) + UI readiness только после ACTIVE; **§9** Excel write-path out of MVP; **§10** Telegram Enable idempotent while PENDING/ACTIVE; **§11** keyboard MAY hide Enable while PENDING/ACTIVE (Disable/Back remain).

Architecture Decision Missing: нет (для этого change placement закрыт proposed decision выше; при archive — promo в `openspec/decisions/`).

## Ownership & Placement

**Owner layer:**

- Shop-runner A/B Hold automation path: `process_ab_setup` / `process_ab_hold` (отдельные entrypoints рядом с V3, не «ветка глубоко внутри NORMAL preamble» как единственный контроль).
- PG durable mode на `AdvSetting` (или эквивалентное поле кампании): source of truth OFF / PENDING_SETUP / ACTIVE.
- PG durable allowed-set snapshot на кампании (новое поле, **новая migration**): SoT зафиксированного разрешённого набора фраз; Redis не SoT snapshot.
- Allowed-set freeze path: capture allowed-set → snapshot → setup sync привести WB к allowed-set; во время PENDING/ACTIVE — без ordinary recalculation allowed-set; hold-protection исключает не-разрешённые фразы (минус как enforcement) в пределах WB cap, иначе видимая деградация (owner: A/B Hold path + gate на `MinusPhraseManager` / manager coroutine).
- Redis coordination layer: `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project patterns.
- Paid UI / handlers: **единственный** enable/disable write-path MVP; экран инструкции (вкл. текст про минус-freeze) + вкл/выкл; gate `bot_active` **и** stats freshness на enable; alert с reason + `SUPPORT_LINK`; **ready-to-test только после ACTIVE**. Manual «Обновить минус-слова» при PENDING/ACTIVE: manager skip → Telegram non-success (blocked / отключите A/B Hold), не «Минус-слова обновлены».
- Mode policy overlays: default «выкл».
- Excel schema: **remove** `card_ab_hold_mode` EDIT column; import ignore/no-op если поле всё же пришло; `can_apply_card_ab_hold_mode_via_excel` → always deny non-absent / remove enable path.

**Allowed layers:** scheduling exclusion в `adv_settings_auto_update` (или единый dispatcher), ACT structural guards на whitelist/target-place/emergency/minus ordinary recalc, hold guard executors (overspend / PFO > max), allowed-set enforcement (minus non-allowed), bidder/cluster bids, Apply path только для setup/hold allowed mutations.

**Forbidden layers:**

- Ordinary V3 NORMAL preamble как sole controller hold без exclusion scheduling.
- Прямое присваивание mode default в transition-helper/handler.
- Остановка биддера / `bot_active=False` как реализация hold.
- Structural ACT (БС / ЦП update / enable / ordinary minus recalculation) во время PENDING_SETUP / ACTIVE.
- UI «можно запускать A/B» на PENDING_SETUP или до успешного allowed-set snapshot.
- Redis как единственный source of truth режима или minus snapshot без PG.
- Excel export/import/apply `card_ab_hold_mode` (вкл. direct ACTIVE / PENDING / OFF).
- Любой non-setup переход в ACTIVE (§8 / §9).

**Rationale:** соответствует proposed `card-ab-hold-write-path-ownership` (§3 + §8 + §9) и accepted `mode-defaults-policy-ownership`.

## Decisions

### 1. Durable PG enum + Redis interrupt (не start/end tick flags)

**Выбор:** PG `card_ab_hold_mode` ∈ {OFF, PENDING_SETUP, ACTIVE}; Redis signal/last-abort/setup-lock для multi-pod.

**Почему:** bot и shop-runner в разных подах; mid-tick normal нужно прервать до apply. Start/end флаги тика не abort’ят in-flight и stuck при краше.

**Альтернатива:** только `if` в orchestrator по PG — отклонена (гонка mid-tick). Только Redis без PG — отклонена (нет durable режима).

### 2. Scheduling exclusion + отдельные entrypoints

**Выбор:** при PENDING_SETUP → только setup; при ACTIVE → только hold; ordinary V3 structural не schedule’ится. Setup/hold ставятся из **полного** eligible списка `advs` (как ordinary V3), а не только из `advs_filtred`. Freshness-фильтр ordinary V2 / cluster-bids остаётся своим контрактом.

**Почему:** Bugbot/продукт — PENDING не должен вечно висеть из‑за stale после ENTER; после переключения сбои статы «уже не так критичны» для продолжения setup/hold. Вход в тест при больной стате запрещён отдельно (см. §2a / UI).

**Альтернатива:** один `process_adv_v3` с огромной внутренней веткой — отклонена decision’ом (forbidden «sole if»). Setup только из `advs_filtred` — отклонена (stuck PENDING).

### 2a. Stats freshness gate на enable (не на post-enter)

**Выбор:** enable (**Telegram UI only** → PENDING) MUST NOT, если РК не проходит freshness/health класс `_split_advs_by_stats_freshness` (не попала бы в fresh automation set). UI при блокировке MUST сразу показать: (1) причину, (2) что включение теста ограничено, (3) рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK`. В репозитории нет `const.ADMIN`; whitelist админов — `const.ADMINS`; публичная ссылка для пользователя — `SUPPORT_LINK` (как в других handler’ах: «обратитесь в поддержку → {SUPPORT_LINK}»). Excel не enable-path в MVP.

**Почему:** ENTER/setup на «мёртвой» стате даёт массовый FAIL→OFF и грязный старт теста; после входа блокировать hold/setup freshness’ом хуже, чем слабее overspend на stale.

### 2c. Launch validity soft-gate (низкий объём показов за 24ч)

**Выбор:** новый шаг enable-потока (**Telegram UI only**), decision §2c: **попытка запуска → оценка → при проблеме → информация + рекомендация + выбор**. После прохождения freshness (§2a), но до записи `PENDING_SETUP` + Redis ENTER, handler агрегирует суммарные показы ключей-кандидатов теста за окно последних 24ч. Источник — существующая CH-инфраструктура показов по ключам `get_keywords_views_by_days(adv_ids, start, end)` в `app/modules/shop_runner/wb_stat_manager/clickhouse_manager/full_wb_adv_stat.py` (MV `default_db.mv_clusters_daily_agg`), с окном последних суток; кандидаты — те же ключи, что фигурируют в setup (non-BAD / would-carry-test набор, полученный тем же UI-источником, что карточка ключей `fetch_keywords_from_database`). Порог — константа `AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000` (суммарно за 24ч). Если `Σ показов < порога`: mode остаётся `OFF`, а пользователю показывается сообщение с (1) причиной (мало показов для надёжного A/B), (2) рекомендацией поднять план max CPO и повторить попытку, (3) inline-выбором «Всё равно запустить» / «Отмена». «Всё равно запустить» (отдельный confirm-callback) → `PENDING_SETUP` + Redis ENTER; «Отмена» → остаётся `OFF`, ENTER не пишется. При `Σ ≥ порога` предупреждение не показывается, enable идёт обычным путём (§7). Это **soft-gate** (пользователь MAY продолжить на свой риск), в отличие от freshness hard-block (§2a) и пустого allowed-set (не-ready, §8).

**Почему:** тест на ключах с крайне низким объёмом показов даёт статистически ненадёжный A/B; но объём — не повод жёстко блокировать (в отличие от больной статы), поэтому предупреждение + осознанный выбор + практичная рекомендация (поднять max CPO → больше ключей проходят ENTER-критерий и больше трафика набегает → выше объём для теста). Реюз `full_wb_adv_stat` / `mv_clusters_daily_agg` избегает нового CH-контракта.

**Альтернатива:** hard-block enable при низком объёме — отклонена (пользователь должен иметь право запустить на свой риск). Молчаливый enable без предупреждения — отклонена (finding: пользователь не видит, что тест заведомо слабый).

### 3. ENTER criterion

**Выбор:** PASS iff `pay_for_order is not None` и `pay_for_order ≤ plan.max_pay_for_order` и `views ≥ 100` (тот же источник показов, что карточка ключа / CalculatedKeyword за недельное окно). FAIL → OFF. PASS → set target_place = current WB position; зафиксировать БС-состав по итогу setup.

**Почему:** max (не resolve) — рабочий потолок после прогрева; 100 показов снижает ложный PASS на шуме. Equality на max = PASS (`≤`).

**Альтернатива:** filter по resolve — отклонена (слишком жёстко при выполненном плане). Keep-as-is на FAIL — отклонена пользователем.

### 4. HOLD invariants

**Выбор:** ЦП не обновляются; биддер продолжает работать к зафиксированным ЦП; нет WL add/remove/trim/enable/calibration UP; нет ordinary minus recalculation (allowed-set заморожен); hold-protection исключает новые/не-разрешённые фразы и восстанавливает снятые разрешённые к замороженному allowed-set (минус как enforcement, в пределах WB minus cap; иначе видимая деградация); только guard перерасхода vs max CPO (reuse overspend/PFO-off семантику).

**Почему:** позиции и разрешённый набор фраз стабильны для теста; трафик не обрывается отключением биддера; новые фразы и ручные правки в WB/боте не должны «загрязнять» A/B.

### 4a. Allowed-phrase-set freeze + hold enforcement

**Выбор:** primary invariant — замораживается **разрешённый (relevant) набор фраз** (relevant-фразы + получившийся GOOD/whitelist профиль ключей), а не список минус-фраз; минус — производный enforcement. Переиспользуется существующая модель `auto_add_only_relevant_phrase` / `relevant_phrases` / `NOT_RELEVANT_PHRASE` (не-разрешённая фраза → BAD → минус). На ENTER до ACTIVE — жёсткий порядок: (1) зафиксировать allowed-set и записать durable PG allowed-set snapshot (новое поле, новая migration); (2) одной setup sync/mutation привести WB к allowed-set (исключить всё вне набора в пределах WB minus cap); (3) остальной setup (ключи/ЦП/БС); (4) ACTIVE. Во время PENDING/ACTIVE ordinary `update_minus_phrases` recalc (изменение allowed-set по свежей стате) MUST NOT — allowed-set заморожен; **отдельно** hold-protection исключает любые новые/не-разрешённые фразы и восстанавливает снятые разрешённые, удерживая поверхность трат = allowed-set. EXIT → clear/archive snapshot; ordinary minus + recalc снова разрешены.

**Почему:** новые фразы появляются постоянно (стата пересчитывает GOOD/BAD); заморозка одного минус-листа не мешает новым фразам откручиваться и загрязнять тест. Замораживать надо источник (allowed-set), а минус применять как enforcement. PG snapshot переживает рестарт; Redis не SoT набора.

**WB minus cap (видимая деградация):** enforcement ограничен лимитом WB (~1000 фраз/nmid). Если для удержания allowed-set нужно исключить больше, чем допускает cap (или тип РК — open-match без доказанной controllability), система деградирует **видимо** (лог + честный статус, что hold не гарантирован), не заявляя чистый hold молча.

**Альтернатива:** snapshot минус-листа + restore-on-drift (изначальный дизайн) — отклонена: замораживает производный негатив, новые фразы протекают и тест грязный. Хранить allowed-set только в Redis — отклонена (нет durable SoT).

### 4b. UI readiness after ACTIVE only

**Выбор:** UI MUST показывать PENDING/«подготовка» пока setup идёт; сообщение «режим включён / можно запускать A/B» — только после PG mode == ACTIVE (полный setup, в т.ч. allowed-set snapshot). Setup lock / interrupt исключают ready при abort.

**Почему:** иначе пользователь стартует тест на незафиксированном минус-профиле (гонка с PENDING).

### 5. EXIT

**Выбор:** PG → OFF; снова разрешены обновление ЦП, ordinary structural апдейтеры и ordinary minus auto-update; minus PG snapshot clear/archive; без restore keyword-profile / Excel snapshot.

**Почему:** простой контракт для пользователя; minus freeze снят явно.

### 6. Redis classes (project patterns)

| Prefix | Role | Writer | TTL |
|--------|------|--------|-----|
| `CardAbHoldSignal` | ENTER/EXIT/CANCEL JSON snapshot | bot | ~15 мин |
| `CardAbHoldLastAbort` | `{safe, can_continue, reason, at}` | shop-runner | ~1 ч |
| `CardAbHoldSetupLock` | NX lock via `RedisLockManager` | shop-runner | ~5 мин |

Классы: `AdvSettingRedisCache` + `RedisCacheBase`, ключ `{prefix}:{adv_id}`; Pydantic/JSON как у `LastV3UpdaterAction`.

Check-points interrupt: после load и **обязательно до apply**; early return без WB structural apply.

### 7. Paid UI write-path

**Выбор:** кнопка «Включить» → явный экран с инструкцией (confirmation через отдельный экран + действие; текст MUST включать фиксацию набора фраз [новые исключаются] / restore из WB / «чтобы изменить набор — отключите A/B Hold», scoped/best-effort без обещания полной заморозки вне типа РК / WB cap); при клике: gate `bot_active`, **gate stats freshness**, при fail — alert (причина + ограничение + `SUPPORT_LINK`) без PENDING; если mode уже `PENDING_SETUP` или `ACTIVE` — **no-op** (не demote, не Redis ENTER, не re-ENTER force sync; decision §10); при ok и mode `OFF` — PG PENDING_SETUP, Redis ENTER, poll last-abort / **ACTIVE**; UI «можно запускать A/B» только после ACTIVE; «Выключить» → EXIT signal + PG OFF + clear allowed-set snapshot (единственный MVP путь обратно в `OFF` перед новым ENTER). Клавиатура экрана: **Disable + Back всегда**; **Enable MUST при `OFF`**; при `PENDING_SETUP` / `ACTIVE` UI **MAY скрыть** Enable (decision §11) — сахар против случайного нажатия; handler no-op (§10) остаётся обязательным при stale callback.

**Affected records:** KeywordsSetting (status/БС/ЦП) на ENTER; AdvSetting mode field; AdvSetting allowed-set snapshot field; bidder продолжает писать ставки в HOLD; WB minus set на setup sync / hold enforcement.

**Recovery:** EXIT всегда доступен paid-пользователю; TTL Redis; при зависшем PENDING_SETUP — повторный setup под lock или EXIT (setup не режется freshness filter после enter); UI не показывает ready, пока не ACTIVE.

### 8. Defaults

Default OFF через mode overlays (`mode-defaults-policy-ownership`); free overlay удерживает OFF / не включает режим.

### 9. Excel out of MVP (decision §9)

**Выбор:** убрать `card_ab_hold_mode` из Excel schema export/import/apply целиком. Leftover payload → ignore. Future change может вернуть колонку с корректным path только → PENDING (не ACTIVE) + interrupt/setup; сейчас — out.

**Почему:** prod bug — Excel `active` обходил ENTER allowed-set snapshot; `process_ab_setup` не бежит на ACTIVE; enforcement/ready врут. Полное удаление из Excel проще и безопаснее coercion.

**Альтернатива:** coerce Excel enable → `pending_setup` only — отклонена пользователем (убераем Excel совсем на сейчас).

## Affected components (ориентир)

- PG migration #1 (уже): поле режима на кампании + default OFF.
- PG migration #2 (**новая**): durable allowed-set snapshot на кампании + clear на EXIT.
- Shop-runner: dispatcher `adv_settings_auto_update`; setup/hold pipelines (вкл. allowed-set capture+snapshot+sync); interrupt checks; ACT guards (top-key WL, individual TP, WL trim non-v3, stats emergency structural, ordinary allowed-set recalc); allowed-set enforcement on drift (minus non-allowed, WB cap → visible degradation).
- Redis caches + lock.
- ClickHouse read (реюз `full_wb_adv_stat.get_keywords_views_by_days` / `mv_clusters_daily_agg`): суммарные показы ключей-кандидатов за 24ч для launch-validity soft-gate (§2c).
- Telegram: отдельное сообщение/экран A/B + keyboard; hide when `bot_active is False`; instruction minus-freeze copy; ready only after ACTIVE; **low-24h-views warning + confirm-callback «Всё равно запустить» / «Отмена»** (§2c).
- Excel roundtrip: **remove** column + ignore apply for `card_ab_hold_mode`.
- Unit/gate tests (`ab_hold_gates` по духу `bot_active_gates`).

## Side effects

- ENTER может массово OFF ключи с `views < 100` или PFO > max.
- HOLD снижает «подстройку» экономики (нет calibraton/enable) — ожидаемо для теста.
- Bidder продолжает траты по зафиксированным позициям.
- Новые/не-разрешённые фразы во время hold исключаются; ручные правки в WB/боте перезаписываются к замороженному allowed-set.
- При превышении WB minus cap / open-match РК hold — best-effort с видимой деградацией (лог + честный статус), не гарантированная чистая поверхность.
- Пользователи больше не смогут включать/выключать A/B Hold через Excel (только Telegram).

## Access guards

| Path | Gate |
|------|------|
| UI / enable | `bot_active is True` **и** stats freshness/health pass **и** `automatic_version == 3` |
| UI enable on non-V3 | no-op (mode stays `OFF`) + reason «A/B Hold требует V3» |
| Auto-updater version → V2 | blocked while mode ∈ {PENDING_SETUP, ACTIVE} (EXIT → OFF first) |
| V2 `change_adv_strategy` (MIN_CPO/MAX_CONV) | вне A/B Hold freeze; held V3-профиль не зависит от campaign strategy objective |
| UI enable blocked by stats | show reason + restriction + `const.SUPPORT_LINK` |
| UI enable low 24h views (Σ candidate keyword views < `AB_HOLD_MIN_TOTAL_VIEWS_24H`) | soft warn: reason + raise-max-CPO recommendation + choice launch-anyway/cancel; mode stays `OFF` until confirm (§2c) |
| UI ready-to-test copy | mode == ACTIVE after full setup (incl. minus snapshot) |
| Excel apply `card_ab_hold_mode` | **MUST NOT** (ignore / no column) |
| Ordinary V3 schedule | mode == OFF |
| A/B setup / hold schedule | mode PENDING/ACTIVE; **не** требовать `advs_filtred` |
| Structural ACT (WL/TP/enable/emergency keys) | mode not in PENDING_SETUP, ACTIVE |
| Ordinary minus recalculation / allowed-set recalc | mode not in PENDING_SETUP, ACTIVE |
| Allowed-set enforcement (minus non-allowed) | PENDING_SETUP / ACTIVE when drift detected; within WB minus cap else visible degradation |
| Bidder / cluster bids | allowed if paid bot+bidder flags as today |
| Hold guards | ACTIVE only |
| Non-setup ACTIVE write | Forbidden |

## Validation plan

- Unit: ENTER pass/fail matrix (PFO, views, None).
- Unit: interrupt → no apply when signal ENTER.
- Gate: ACTIVE → top-key / individual TP / trim not called; cluster bids still eligible.
- Gate: PENDING/ACTIVE → ordinary allowed-set recalc not applied; new non-allowed phrase → excluded; removed allowed phrase → restored.
- Gate: enforcement exceeding WB minus cap / open-match → visible degradation (log + honest status), not silent clean hold.
- Gate: setup failure on allowed-set capture/snapshot → no ACTIVE; UI not ready.
- Gate: UI ready-to-test only after ACTIVE; PENDING never shows ready-to-test.
- Gate: EXIT → ordinary minus + allowed-set recalc eligible again; allowed-set snapshot cleared/archived.
- Gate: `bot_active=False` → UI hidden / enable no-op.
- Gate: enable blocked when stats freshness fails; UI contains reason + restriction + `SUPPORT_LINK`.
- Integration (real/test CH): 24h candidate-keyword views aggregate over `mv_clusters_daily_agg`; boundary around `AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000`.
- Gate (§2c): enable with Σ 24h views < threshold → mode stays `OFF`, message has reason + raise-max-CPO recommendation + launch-anyway/cancel choice; launch-anyway → PENDING_SETUP + ENTER; cancel → OFF, no ENTER; Σ ≥ threshold → enable without warning (paired).
- Telegram payload-limit: worst-case low-views warning text + confirm-callback `callback_data` within Bot API byte limits.
- Gate: PENDING/ACTIVE + not in fresh set → setup/hold всё ещё eligible; ordinary V2 по-прежнему может требовать fresh.
- Gate: Excel import `active` / `pending_setup` / `off` → mode unchanged; schema has no column.
- Gate: Enable while ACTIVE/PENDING → mode unchanged, no Redis ENTER rewrite; OFF → PENDING.
- Gate: keyboard while ACTIVE/PENDING → Disable+Back present; Enable MAY be absent; while OFF → Enable present.
- EXIT → ordinary V3 снова в schedule.
- Не мокать decision function под тестом; write-gate доказывает фильтрацию до write boundary.

## Performance

- Redis get на check-point: дешёвый; TTL ограничивает leaks.
- Setup один раз на ENTER (lock NX); hold тик легче NORMAL preamble (узкий executor set).
- Minus snapshot: один PG write на ENTER; restore только при drift.
- Массовые РК: mode filter в scheduler — O(advs), без N+1 Redis на всех OFF.

## Risks / Trade-offs

- [Risk] Ключи с малой статистикой уйдут в OFF на ENTER. → Mitigation: справка про прогрев; порог 100 views; max CPO не зажимать перед входом; **не пускать enable при проблемной стате РК**.
- [Risk] In-flight normal уже в apply при клике. → Mitigation: signal + check before apply; UI «Подготовка…»; короткий poll timeout.
- [Risk] Пропущенный ACT без guard (вкл. minus). → Mitigation: gate-suite + decision Forbidden; review `update_minus_phrases_in_advs`.
- [Risk] UI сообщает ready на PENDING. → Mitigation: poll только ACTIVE; decision §8 Forbidden; paired UI test.
- [Risk] Excel → ACTIVE без snapshot (prod). → Mitigation: decision §9 — remove Excel column/apply entirely; regression tests import ignore.
- [Risk] Пользователь путает с Safe mode. → Mitigation: отдельный UI/название A/B Hold; out of scope Safe mode.
- [Risk] Setup/hold на stale после enter слабее охраняют overspend. → Acceptable trade-off vs stuck PENDING; enable уже отрезал «холодный» вход.
- [Risk] Enforcement перезапишет осознанную ручную правку. → Acceptable: инструкция + «чтобы менять набор — отключите Hold».
- [Risk] Allowed-set требует > WB minus cap исключений / open-match РК → hold не гарантирован. → Mitigation: видимая деградация (лог + честный статус), scoped wording; не обещать полную заморозку.
- [Risk] Нет Excel bulk enable. → Acceptable MVP; Telegram-only; Excel return = future change.
- [Risk] Случайный Enable mid-hold. → Mitigation: §10 handler no-op + §11 MAY hide Enable на PENDING/ACTIVE.

## Migration Plan

1. Deploy migration режима (field default OFF) — уже в change.
2. Deploy **новая** migration allowed-set snapshot field — no freeze behavior until runner/UI wired.
3. Deploy runner (allowed-set snapshot + hold enforcement + gate ordinary recalc) + Redis + UI (instruction + ready after ACTIVE).
4. Rollout paid UI entry; **remove** Excel `card_ab_hold_mode` column/apply if still present.
5. Rollback: mode OFF + disable UI; clear snapshots; Redis TTL cleanup; ordinary V3 / minus без exclusion.

## Open Questions

1. ~~Точный source field views~~ — **Resolved in apply:** `CalculatedKeyword.views` ← `cluster_stat.views` (тот же источник карточки ключа / calculated keywords cache).
2. ~~Immediate setup job~~ — **Resolved MVP:** immediate setup job **не** запускается из bot; UI ставит `PENDING_SETUP`, пишет Redis ENTER, poll `LastAbort`/PG mode; setup на тике shop-runner. UX показывает PENDING; **ready-to-test только после ACTIVE** (уточнено update минус-freeze).
3. ~~Hold guard executors~~ — **Resolved MVP:** hold использует deep-overspend + PFO>max OFF (`hold_guards.py`), без resolve clamp / без полного `ResetOverMaxCpo` ladder trim. Полный V3 executor pair — optional follow-up, не blocker archive.
4. ~~Setup vs stale `advs_filtred`~~ — **Resolved (update):** enable блокируется freshness/health статы + UI reason/`SUPPORT_LINK`; после PENDING/ACTIVE setup/hold schedule из полного `advs`, не только `advs_filtred`.
5. ~~Minus freeze storage~~ — **Resolved (update):** durable PG **allowed-set** snapshot на кампании (новая migration); capture allowed-set→snapshot до ACTIVE; hold enforcement (исключение не-разрешённых фраз, в пределах WB cap; иначе видимая деградация); clear/archive on EXIT. Заморозка allowed-set — primary invariant, минус — derived enforcement.
6. ~~Excel A/B Hold column~~ — **Resolved (update):** убрать из Excel schema/apply в MVP (decision §9); enable/disable только Telegram; future option отдельно.
7. Launch validity soft-gate (decision §2c) — **Planned (update, not yet applied):** enable агрегирует показы ключей-кандидатов за 24ч (реюз `full_wb_adv_stat.get_keywords_views_by_days` / `mv_clusters_daily_agg`); Σ < `AB_HOLD_MIN_TOTAL_VIEWS_24H` (=1000) → warn + рекомендация поднять max CPO + выбор запустить/отмена. Реализация — tasks §13.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`card-ab-hold-write-path-ownership`; дополнен §2c launch-validity soft-gate + §8 minus + §9 Excel out + §10 Enable idempotent + §11 hide Enable keyboard)
- [x] implementation layer matches decision *(§8 REDEFINED applied: allowed-set snapshot (`card_ab_hold_allowed_phrases_snapshot`) + `MinusPhraseManager.enforce_frozen_allowed_set` hold enforcement + WB-cap visible degradation replace minus snapshot/restore; §9 Excel remove, §10 Enable idempotent, §11 hide Enable — previously applied)*
- [ ] §2c launch-validity soft-gate — **planned, not yet applied** (owner: bot enable write-path; impl + integration tests in tasks §13)
