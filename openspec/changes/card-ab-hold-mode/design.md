## Context

Клиентам нужен paid self-service режим для «чистого» A/B-теста карточки: зафиксировать целевые позиции по текущей фактической позиции, отключить обновление ЦП, оставить биддер работающим, не полагаясь на полный `bot_active=False` и не на хрупкую комбинацию legacy-флагов.

Сегодня ordinary V3 (`adv_settings_auto_update` → `process_adv_v3`) и параллельные ACT-корутины (whitelist top-key, individual target place, emergency, и т.д.) могут менять ключи/БС/ЦП в любой тик. Bot и shop-runner крутятся в разных подах — нужен Redis cooperative interrupt, чтобы ENTER не смешался с уже идущим normal apply.

Стек: Python 3.11, SQLAlchemy + PostgreSQL, Redis (паттерн `AdvSettingRedisCache` / `RedisCacheBase`, lock через `RedisLockManager`), Telegram paid UI. Режим — paid automation core: enable/disable только через Telegram при `bot_active is True`. Excel roundtrip **не** является write-path режима в MVP (future).

## Goals / Non-Goals

**Goals:**

- Durable режим кампании: OFF / PENDING_SETUP / ACTIVE в PG.
- ENTER: setup по `pay_for_order ≤ max CPO` и `views ≥ 100` (окно как в карточке ключа); FAIL → OFF; PASS → ЦП := текущая фактическая; БС фиксируется по итогу setup.
- ENTER minus: одна setup sync/mutation минус-фраз → PG snapshot (новая Alembic migration) → только затем setup MAY → ACTIVE.
- HOLD: обновление ЦП выкл; биддер ON; structural ACT freeze (WL/TP/enable/emergency + ordinary minus recalc); drift минус-фраз → restore snapshot; только guard перерасхода vs max CPO.
- UI readiness: «режим включён / можно запускать A/B» только после ACTIVE (полный setup, в т.ч. минус + snapshot); не на PENDING; без гонки.
- EXIT: снова обновление ЦП + ordinary апдейтеры + ordinary minus auto-update; clear/archive PG minus snapshot; без restore keyword-profile / Excel snapshot.
- Cross-pod Redis: signal ENTER/EXIT, last-abort ack, setup lock NX.
- Paid-only Telegram UI (скрыть при `bot_active is False`) + reject enable.
- Enable gate на stats freshness/health (тот же класс, что `advs_filtred`); UI: причина + ограничение + `const.SUPPORT_LINK`.
- После PENDING/ACTIVE: setup/hold scheduling не зависит от попадания в `advs_filtred`.
- **Excel: колонка/apply `card_ab_hold_mode` убраны из MVP** (ignore leftover payload; future option).
- Instruction: минус-фразы фиксируются; ручные правки в WB MAY быть возвращены; изменить минус → отключить A/B Hold.
- Tests-first gates: structural freeze, minus snapshot/restore, UI not-ready on PENDING, paid visibility, interrupt до apply, freshness enable + post-enter schedule + Excel ignore.

**Non-Goals:**

- Встроенный A/B WB, price management, hard-block полок, Safe mode.
- Free path / enable при `bot_active is False`.
- Переписывание ordinary V3 preamble вне отдельного hold/setup path.
- Обязательный Excel backup / restore keyword-settings при EXIT (минус snapshot — отдельный freeze-механизм, не Excel backup).
- **Excel enable/disable/edit A/B Hold** — future / out of MVP (идея сохранена; текущий контракт — только Telegram).

## Architecture Decision References

Architecture Decisions Found:

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — Status: Accepted. Дефолт «A/B Hold выкл» при paid/free overlays принадлежит declarative mode policy overlays, не transition-helper / UI.
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — Status: Proposed. Ownership setup/hold write-path, exclusion из ordinary V3, structural freeze (вкл. минус-фразы), PG vs Redis, paid-only Telegram enable, bidder MUST оставаться работающим; stats freshness asymmetry; **§8** minus PG snapshot + restore + UI readiness только после ACTIVE; **§9** Excel write-path out of MVP; **§10** Telegram Enable idempotent while PENDING/ACTIVE; **§11** keyboard MAY hide Enable while PENDING/ACTIVE (Disable/Back remain).

Architecture Decision Missing: нет (для этого change placement закрыт proposed decision выше; при archive — promo в `openspec/decisions/`).

## Ownership & Placement

**Owner layer:**

- Shop-runner A/B Hold automation path: `process_ab_setup` / `process_ab_hold` (отдельные entrypoints рядом с V3, не «ветка глубоко внутри NORMAL preamble» как единственный контроль).
- PG durable mode на `AdvSetting` (или эквивалентное поле кампании): source of truth OFF / PENDING_SETUP / ACTIVE.
- PG durable minus-phrase snapshot на кампании (новое поле, **новая migration**): SoT зафиксированного набора для freeze/restore; Redis не SoT snapshot.
- Minus freeze path: setup sync → snapshot; во время PENDING/ACTIVE — без ordinary `update_minus_phrases` recalculation; при drift — restore snapshot на WB (owner: A/B Hold path + gate на `MinusPhraseManager` / manager coroutine).
- Redis coordination layer: `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project patterns.
- Paid UI / handlers: **единственный** enable/disable write-path MVP; экран инструкции (вкл. текст про минус-freeze) + вкл/выкл; gate `bot_active` **и** stats freshness на enable; alert с reason + `SUPPORT_LINK`; **ready-to-test только после ACTIVE**. Manual «Обновить минус-слова» при PENDING/ACTIVE: manager skip → Telegram non-success (blocked / отключите A/B Hold), не «Минус-слова обновлены».
- Mode policy overlays: default «выкл».
- Excel schema: **remove** `card_ab_hold_mode` EDIT column; import ignore/no-op если поле всё же пришло; `can_apply_card_ab_hold_mode_via_excel` → always deny non-absent / remove enable path.

**Allowed layers:** scheduling exclusion в `adv_settings_auto_update` (или единый dispatcher), ACT structural guards на whitelist/target-place/emergency/minus ordinary recalc, hold guard executors (overspend / PFO > max), minus restore-to-snapshot, bidder/cluster bids, Apply path только для setup/hold allowed mutations.

**Forbidden layers:**

- Ordinary V3 NORMAL preamble как sole controller hold без exclusion scheduling.
- Прямое присваивание mode default в transition-helper/handler.
- Остановка биддера / `bot_active=False` как реализация hold.
- Structural ACT (БС / ЦП update / enable / ordinary minus recalculation) во время PENDING_SETUP / ACTIVE.
- UI «можно запускать A/B» на PENDING_SETUP или до успешного minus snapshot.
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

### 3. ENTER criterion

**Выбор:** PASS iff `pay_for_order is not None` и `pay_for_order ≤ plan.max_pay_for_order` и `views ≥ 100` (тот же источник показов, что карточка ключа / CalculatedKeyword за недельное окно). FAIL → OFF. PASS → set target_place = current WB position; зафиксировать БС-состав по итогу setup.

**Почему:** max (не resolve) — рабочий потолок после прогрева; 100 показов снижает ложный PASS на шуме. Equality на max = PASS (`≤`).

**Альтернатива:** filter по resolve — отклонена (слишком жёстко при выполненном плане). Keep-as-is на FAIL — отклонена пользователем.

### 4. HOLD invariants

**Выбор:** ЦП не обновляются; биддер продолжает работать к зафиксированным ЦП; нет WL add/remove/trim/enable/calibration UP; нет ordinary minus recalculation; при drift минус-фраз от PG snapshot — restore на WB; только guard перерасхода vs max CPO (reuse overspend/PFO-off семантику).

**Почему:** позиции и минус-профиль стабильны для теста; трафик не обрывается отключением биддера; ручные правки в WB/боте не должны «загрязнять» A/B.

### 4a. Minus-phrases: setup snapshot + freeze restore

**Выбор:** на ENTER до ACTIVE — жёсткий порядок: (1) одна setup sync/mutation минус-фраз до актуального состояния; (2) PG snapshot (новое поле, новая migration); (3) остальной setup (ключи/ЦП/БС); (4) ACTIVE. Во время PENDING/ACTIVE ordinary `update_minus_phrases` recalc MUST NOT; drift → restore snapshot. EXIT → clear/archive snapshot; ordinary minus снова разрешён.

**Почему:** минус-фразы меняют выдачу так же, как состав БС; без freeze тест карточки грязный. PG snapshot переживает рестарт; Redis не SoT списка.

**Альтернатива:** только «не трогать минус без snapshot» — отклонена (drift в кабинете WB остаётся). Хранить snapshot только в Redis — отклонена (нет durable SoT).

### 4b. UI readiness after ACTIVE only

**Выбор:** UI MUST показывать PENDING/«подготовка» пока setup идёт; сообщение «режим включён / можно запускать A/B» — только после PG mode == ACTIVE (полный setup, в т.ч. минус + snapshot). Setup lock / interrupt исключают ready при abort.

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

**Выбор:** кнопка «Включить» → явный экран с инструкцией (confirmation через отдельный экран + действие; текст MUST включать freeze минус-фраз / restore / «чтобы изменить минус — отключите A/B Hold»); при клике: gate `bot_active`, **gate stats freshness**, при fail — alert (причина + ограничение + `SUPPORT_LINK`) без PENDING; если mode уже `PENDING_SETUP` или `ACTIVE` — **no-op** (не demote, не Redis ENTER, не re-ENTER force sync; decision §10); при ok и mode `OFF` — PG PENDING_SETUP, Redis ENTER, poll last-abort / **ACTIVE**; UI «можно запускать A/B» только после ACTIVE; «Выключить» → EXIT signal + PG OFF + clear minus snapshot (единственный MVP путь обратно в `OFF` перед новым ENTER). Клавиатура экрана: **Disable + Back всегда**; **Enable MUST при `OFF`**; при `PENDING_SETUP` / `ACTIVE` UI **MAY скрыть** Enable (decision §11) — сахар против случайного нажатия; handler no-op (§10) остаётся обязательным при stale callback.

**Affected records:** KeywordsSetting (status/БС/ЦП) на ENTER; AdvSetting mode field; AdvSetting minus-phrase snapshot field; bidder продолжает писать ставки в HOLD; WB minus set на setup sync / restore.

**Recovery:** EXIT всегда доступен paid-пользователю; TTL Redis; при зависшем PENDING_SETUP — повторный setup под lock или EXIT (setup не режется freshness filter после enter); UI не показывает ready, пока не ACTIVE.

### 8. Defaults

Default OFF через mode overlays (`mode-defaults-policy-ownership`); free overlay удерживает OFF / не включает режим.

### 9. Excel out of MVP (decision §9)

**Выбор:** убрать `card_ab_hold_mode` из Excel schema export/import/apply целиком. Leftover payload → ignore. Future change может вернуть колонку с корректным path только → PENDING (не ACTIVE) + interrupt/setup; сейчас — out.

**Почему:** prod bug — Excel `active` обходил ENTER minus sync+snapshot; `process_ab_setup` не бежит на ACTIVE; restore/ready врут. Полное удаление из Excel проще и безопаснее coercion.

**Альтернатива:** coerce Excel enable → `pending_setup` only — отклонена пользователем (убераем Excel совсем на сейчас).

## Affected components (ориентир)

- PG migration #1 (уже): поле режима на кампании + default OFF.
- PG migration #2 (**новая**): durable snapshot минус-фраз на кампании + clear на EXIT.
- Shop-runner: dispatcher `adv_settings_auto_update`; setup/hold pipelines (вкл. minus sync+snapshot); interrupt checks; ACT guards (top-key WL, individual TP, WL trim non-v3, stats emergency structural, ordinary minus recalc); minus restore-on-drift.
- Redis caches + lock.
- Telegram: отдельное сообщение/экран A/B + keyboard; hide when `bot_active is False`; instruction minus-freeze copy; ready only after ACTIVE.
- Excel roundtrip: **remove** column + ignore apply for `card_ab_hold_mode`.
- Unit/gate tests (`ab_hold_gates` по духу `bot_active_gates`).

## Side effects

- ENTER может массово OFF ключи с `views < 100` или PFO > max.
- HOLD снижает «подстройку» экономики (нет calibraton/enable) — ожидаемо для теста.
- Bidder продолжает траты по зафиксированным позициям.
- Ручные правки минус-фраз в WB/боте во время hold будут перезаписаны snapshot’ом.
- Пользователи больше не смогут включать/выключать A/B Hold через Excel (только Telegram).

## Access guards

| Path | Gate |
|------|------|
| UI / enable | `bot_active is True` **и** stats freshness/health pass |
| UI enable blocked by stats | show reason + restriction + `const.SUPPORT_LINK` |
| UI ready-to-test copy | mode == ACTIVE after full setup (incl. minus snapshot) |
| Excel apply `card_ab_hold_mode` | **MUST NOT** (ignore / no column) |
| Ordinary V3 schedule | mode == OFF |
| A/B setup / hold schedule | mode PENDING/ACTIVE; **не** требовать `advs_filtred` |
| Structural ACT (WL/TP/enable/emergency keys) | mode not in PENDING_SETUP, ACTIVE |
| Ordinary minus recalculation | mode not in PENDING_SETUP, ACTIVE |
| Minus restore-to-snapshot | PENDING_SETUP / ACTIVE when drift detected |
| Bidder / cluster bids | allowed if paid bot+bidder flags as today |
| Hold guards | ACTIVE only |
| Non-setup ACTIVE write | Forbidden |

## Validation plan

- Unit: ENTER pass/fail matrix (PFO, views, None).
- Unit: interrupt → no apply when signal ENTER.
- Gate: ACTIVE → top-key / individual TP / trim not called; cluster bids still eligible.
- Gate: PENDING/ACTIVE → ordinary minus recalc not applied; drift → restore snapshot.
- Gate: setup failure on minus sync/snapshot → no ACTIVE; UI not ready.
- Gate: UI ready-to-test only after ACTIVE; PENDING never shows ready-to-test.
- Gate: EXIT → ordinary minus eligible again; snapshot cleared/archived.
- Gate: `bot_active=False` → UI hidden / enable no-op.
- Gate: enable blocked when stats freshness fails; UI contains reason + restriction + `SUPPORT_LINK`.
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
- [Risk] Restore минус перезапишет осознанную ручную правку. → Acceptable: инструкция + «чтобы менять минус — отключите Hold».
- [Risk] Нет Excel bulk enable. → Acceptable MVP; Telegram-only; Excel return = future change.
- [Risk] Случайный Enable mid-hold. → Mitigation: §10 handler no-op + §11 MAY hide Enable на PENDING/ACTIVE.

## Migration Plan

1. Deploy migration режима (field default OFF) — уже в change.
2. Deploy **новая** migration minus-phrase snapshot field — no freeze behavior until runner/UI wired.
3. Deploy runner (setup snapshot + restore + gate ordinary minus) + Redis + UI (instruction + ready after ACTIVE).
4. Rollout paid UI entry; **remove** Excel `card_ab_hold_mode` column/apply if still present.
5. Rollback: mode OFF + disable UI; clear snapshots; Redis TTL cleanup; ordinary V3 / minus без exclusion.

## Open Questions

1. ~~Точный source field views~~ — **Resolved in apply:** `CalculatedKeyword.views` ← `cluster_stat.views` (тот же источник карточки ключа / calculated keywords cache).
2. ~~Immediate setup job~~ — **Resolved MVP:** immediate setup job **не** запускается из bot; UI ставит `PENDING_SETUP`, пишет Redis ENTER, poll `LastAbort`/PG mode; setup на тике shop-runner. UX показывает PENDING; **ready-to-test только после ACTIVE** (уточнено update минус-freeze).
3. ~~Hold guard executors~~ — **Resolved MVP:** hold использует deep-overspend + PFO>max OFF (`hold_guards.py`), без resolve clamp / без полного `ResetOverMaxCpo` ladder trim. Полный V3 executor pair — optional follow-up, не blocker archive.
4. ~~Setup vs stale `advs_filtred`~~ — **Resolved (update):** enable блокируется freshness/health статы + UI reason/`SUPPORT_LINK`; после PENDING/ACTIVE setup/hold schedule из полного `advs`, не только `advs_filtred`.
5. ~~Minus freeze storage~~ — **Resolved (update):** durable PG snapshot на кампании (новая migration); sync→snapshot до ACTIVE; restore on drift; clear/archive on EXIT.
6. ~~Excel A/B Hold column~~ — **Resolved (update):** убрать из Excel schema/apply в MVP (decision §9); enable/disable только Telegram; future option отдельно.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`card-ab-hold-write-path-ownership`; дополнен §8 minus + §9 Excel out + §10 Enable idempotent + §11 hide Enable keyboard)
- [x] implementation layer matches decision *(plan delta §9 Excel remove — applied; §10 Enable idempotent — code applied; §11 hide Enable — code applied via `/opsx:apply`)*
