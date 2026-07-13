## Context

Клиентам нужен paid self-service режим для «чистого» A/B-теста карточки: зафиксировать целевые позиции по текущей фактической позиции, отключить обновление ЦП, оставить биддер работающим, не полагаясь на полный `bot_active=False` и не на хрупкую комбинацию legacy-флагов.

Сегодня ordinary V3 (`adv_settings_auto_update` → `process_adv_v3`) и параллельные ACT-корутины (whitelist top-key, individual target place, emergency, и т.д.) могут менять ключи/БС/ЦП в любой тик. Bot и shop-runner крутятся в разных подах — нужен Redis cooperative interrupt, чтобы ENTER не смешался с уже идущим normal apply.

Стек: Python 3.11, SQLAlchemy + PostgreSQL, Redis (паттерн `AdvSettingRedisCache` / `RedisCacheBase`, lock через `RedisLockManager`), Telegram paid UI, Excel roundtrip. Режим — paid automation core: UI и enable только при `bot_active is True`.

## Goals / Non-Goals

**Goals:**

- Durable режим кампании: OFF / PENDING_SETUP / ACTIVE в PG.
- ENTER: setup по `pay_for_order ≤ max CPO` и `views ≥ 100` (окно как в карточке ключа); FAIL → OFF; PASS → ЦП := текущая фактическая; БС фиксируется по итогу setup.
- HOLD: обновление ЦП выкл; биддер ON; structural ACT freeze; только guard перерасхода vs max CPO.
- EXIT: снова обновление ЦП + ordinary апдейтеры; без restore snapshot.
- Cross-pod Redis: signal ENTER/EXIT, last-abort ack, setup lock NX.
- Paid-only UI (скрыть при `bot_active is False`) + reject enable.
- Enable gate на stats freshness/health (тот же класс, что `advs_filtred`); UI: причина + ограничение + `const.SUPPORT_LINK`.
- После PENDING/ACTIVE: setup/hold scheduling не зависит от попадания в `advs_filtred`.
- Excel-колонка режима (paid-only + freshness gate).
- Tests-first gates: structural freeze, paid visibility, interrupt до apply, freshness enable + post-enter schedule.

**Non-Goals:**

- Встроенный A/B WB, price management, hard-block полок, Safe mode.
- Free path / enable при `bot_active is False`.
- Переписывание ordinary V3 preamble вне отдельного hold/setup path.
- Обязательный Excel backup настроек при EXIT.

## Architecture Decision References

Architecture Decisions Found:

- `openspec/decisions/mode-defaults-policy-ownership/decision.md` — Status: Accepted. Дефолт «A/B Hold выкл» при paid/free overlays принадлежит declarative mode policy overlays, не transition-helper / UI.
- `openspec/changes/card-ab-hold-mode/decisions/card-ab-hold-write-path-ownership/decision.md` — Status: Proposed. Ownership setup/hold write-path, exclusion из ordinary V3, structural freeze, PG vs Redis, paid-only enable, bidder MUST оставаться работающим; **дополнен** асимметрией stats freshness (gate на enable; post-enter setup/hold не режутся `advs_filtred`) и UI-ответом с `SUPPORT_LINK`.

Architecture Decision Missing: нет (для этого change placement закрыт proposed decision выше; при archive — promo в `openspec/decisions/`).

## Ownership & Placement

**Owner layer:**

- Shop-runner A/B Hold automation path: `process_ab_setup` / `process_ab_hold` (отдельные entrypoints рядом с V3, не «ветка глубоко внутри NORMAL preamble» как единственный контроль).
- PG durable mode на `AdvSetting` (или эквивалентное поле кампании): source of truth OFF / PENDING_SETUP / ACTIVE.
- Redis coordination layer: `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project patterns.
- Paid UI / handlers: экран инструкции + вкл/выкл; gate `bot_active` **и** stats freshness на enable; alert с reason + `SUPPORT_LINK`.
- Mode policy overlays: default «выкл».
- Excel schema: EDIT-колонка режима, apply только paid **и** при прохождении freshness gate.

**Allowed layers:** scheduling exclusion в `adv_settings_auto_update` (или единый dispatcher), ACT structural guards на whitelist/target-place/emergency, hold guard executors (overspend / PFO > max), bidder/cluster bids, Apply path только для setup/hold allowed mutations.

**Forbidden layers:**

- Ordinary V3 NORMAL preamble как sole controller hold без exclusion scheduling.
- Прямое присваивание mode default в transition-helper/handler.
- Остановка биддера / `bot_active=False` как реализация hold.
- Structural ACT (БС / ЦП update / enable) во время PENDING_SETUP / ACTIVE.
- Redis как единственный source of truth режима без PG.

**Rationale:** соответствует proposed `card-ab-hold-write-path-ownership` и accepted `mode-defaults-policy-ownership`.

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

**Выбор:** enable (UI / Excel / любой write → PENDING) MUST NOT, если РК не проходит freshness/health класс `_split_advs_by_stats_freshness` (не попала бы в fresh automation set). UI при блокировке MUST сразу показать: (1) причину, (2) что включение теста ограничено, (3) рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK`. В репозитории нет `const.ADMIN`; whitelist админов — `const.ADMINS`; публичная ссылка для пользователя — `SUPPORT_LINK` (как в других handler’ах: «обратитесь в поддержку → {SUPPORT_LINK}»).

**Почему:** ENTER/setup на «мёртвой» стате даёт массовый FAIL→OFF и грязный старт теста; после входа блокировать hold/setup freshness’ом хуже, чем слабее overspend на stale.

### 3. ENTER criterion

**Выбор:** PASS iff `pay_for_order is not None` и `pay_for_order ≤ plan.max_pay_for_order` и `views ≥ 100` (тот же источник показов, что карточка ключа / CalculatedKeyword за недельное окно). FAIL → OFF. PASS → set target_place = current WB position; зафиксировать БС-состав по итогу setup.

**Почему:** max (не resolve) — рабочий потолок после прогрева; 100 показов снижает ложный PASS на шуме. Equality на max = PASS (`≤`).

**Альтернатива:** filter по resolve — отклонена (слишком жёстко при выполненном плане). Keep-as-is на FAIL — отклонена пользователем.

### 4. HOLD invariants

**Выбор:** ЦП не обновляются; биддер продолжает работать к зафиксированным ЦП; нет WL add/remove/trim/enable/calibration UP; только guard перерасхода vs max CPO (reuse overspend/PFO-off семантику).

**Почему:** позиции стабильны для теста; трафик не обрывается отключением биддера.

### 5. EXIT

**Выбор:** PG → OFF; снова разрешены обновление ЦП и ordinary апдейтеры; без restore.

**Почему:** простой контракт для пользователя.

### 6. Redis classes (project patterns)

| Prefix | Role | Writer | TTL |
|--------|------|--------|-----|
| `CardAbHoldSignal` | ENTER/EXIT/CANCEL JSON snapshot | bot | ~15 мин |
| `CardAbHoldLastAbort` | `{safe, can_continue, reason, at}` | shop-runner | ~1 ч |
| `CardAbHoldSetupLock` | NX lock via `RedisLockManager` | shop-runner | ~5 мин |

Классы: `AdvSettingRedisCache` + `RedisCacheBase`, ключ `{prefix}:{adv_id}`; Pydantic/JSON как у `LastV3UpdaterAction`.

Check-points interrupt: после load и **обязательно до apply**; early return без WB structural apply.

### 7. Paid UI write-path

**Выбор:** кнопка «Включить» → явный экран с инструкцией (confirmation через отдельный экран + действие); при клике: gate `bot_active`, **gate stats freshness**, при fail — alert (причина + ограничение + `SUPPORT_LINK`) без PENDING; при ok — PG PENDING_SETUP, Redis ENTER, poll last-abort / ACTIVE; «Выключить» → EXIT signal + PG OFF.

**Affected records:** KeywordsSetting (status/БС/ЦП) на ENTER; AdvSetting mode field; bidder продолжает писать ставки в HOLD.

**Recovery:** EXIT всегда доступен paid-пользователю; TTL Redis; при зависшем PENDING_SETUP — повторный setup под lock или EXIT (setup не режется freshness filter после enter).

### 8. Defaults

Default OFF через mode overlays (`mode-defaults-policy-ownership`); free overlay удерживает OFF / не включает режим.

## Affected components (ориентир)

- PG migration: поле режима на кампании + default OFF.
- Shop-runner: dispatcher `adv_settings_auto_update`; setup/hold pipelines; interrupt checks; ACT guards (top-key WL, individual TP, WL trim non-v3, stats emergency structural).
- Redis caches + lock.
- Telegram: отдельное сообщение/экран A/B + keyboard; hide when `bot_active is False`.
- Excel roundtrip schema/column.
- Unit/gate tests (`ab_hold_gates` по духу `bot_active_gates`).

## Side effects

- ENTER может массово OFF ключи с `views < 100` или PFO > max.
- HOLD снижает «подстройку» экономики (нет calibraton/enable) — ожидаемо для теста.
- Bidder продолжает траты по зафиксированным позициям.

## Access guards

| Path | Gate |
|------|------|
| UI / enable / Excel apply | `bot_active is True` **и** stats freshness/health pass |
| UI enable blocked by stats | show reason + restriction + `const.SUPPORT_LINK` |
| Ordinary V3 schedule | mode == OFF |
| A/B setup / hold schedule | mode PENDING/ACTIVE; **не** требовать `advs_filtred` |
| Structural ACT (WL/TP/enable/emergency keys) | mode not in PENDING_SETUP, ACTIVE |
| Bidder / cluster bids | allowed if paid bot+bidder flags as today |
| Hold guards | ACTIVE only |

## Validation plan

- Unit: ENTER pass/fail matrix (PFO, views, None).
- Unit: interrupt → no apply when signal ENTER.
- Gate: ACTIVE → top-key / individual TP / trim not called; cluster bids still eligible.
- Gate: `bot_active=False` → UI hidden / enable no-op.
- Gate: enable blocked when stats freshness fails; UI contains reason + restriction + `SUPPORT_LINK`.
- Gate: PENDING/ACTIVE + not in fresh set → setup/hold всё ещё eligible; ordinary V2 по-прежнему может требовать fresh.
- EXIT → ordinary V3 снова в schedule.
- Не мокать decision function под тестом; write-gate доказывает фильтрацию до write boundary.

## Performance

- Redis get на check-point: дешёвый; TTL ограничивает leaks.
- Setup один раз на ENTER (lock NX); hold тик легче NORMAL preamble (узкий executor set).
- Массовые РК: mode filter в scheduler — O(advs), без N+1 Redis на всех OFF.

## Risks / Trade-offs

- [Risk] Ключи с малой статистикой уйдут в OFF на ENTER. → Mitigation: справка про прогрев; порог 100 views; max CPO не зажимать перед входом; **не пускать enable при проблемной стате РК**.
- [Risk] In-flight normal уже в apply при клике. → Mitigation: signal + check before apply; UI «Подготовка…»; короткий poll timeout.
- [Risk] Пропущенный ACT без guard. → Mitigation: gate-suite + decision Forbidden; review новых корутин.
- [Risk] Пользователь путает с Safe mode. → Mitigation: отдельный UI/название A/B Hold; out of scope Safe mode.
- [Risk] Setup/hold на stale после enter слабее охраняют overspend. → Acceptable trade-off vs stuck PENDING; enable уже отрезал «холодный» вход.

## Migration Plan

1. Deploy migration (field default OFF) — no behavior change.
2. Deploy runner + Redis + UI за feature defaults OFF.
3. Rollout paid UI entry.
4. Rollback: field OFF + disable UI; Redis TTL cleanup; ordinary V3 без exclusion.

## Open Questions

1. ~~Точный source field views~~ — **Resolved in apply:** `CalculatedKeyword.views` ← `cluster_stat.views` (тот же источник карточки ключа / calculated keywords cache).
2. ~~Immediate setup job~~ — **Resolved MVP:** immediate setup job **не** запускается из bot; UI ставит `PENDING_SETUP`, пишет Redis ENTER, poll `LastAbort`/PG mode; setup на тике shop-runner. UX обязан показывать PENDING (сделано).
3. ~~Hold guard executors~~ — **Resolved MVP:** hold использует deep-overspend + PFO>max OFF (`hold_guards.py`), без resolve clamp / без полного `ResetOverMaxCpo` ladder trim. Полный V3 executor pair — optional follow-up, не blocker archive.
4. ~~Setup vs stale `advs_filtred`~~ — **Resolved (update):** enable блокируется freshness/health статы + UI reason/`SUPPORT_LINK`; после PENDING/ACTIVE setup/hold schedule из полного `advs`, не только `advs_filtred`.

## Review Checklist

- [x] existing decisions searched
- [x] relevant decisions cited
- [x] new decision proposed if missing (`card-ab-hold-write-path-ownership`; дополнен stats freshness asymmetry)
- [x] implementation layer matches decision *(delta §7: enable freshness gate + schedule с полного advs)*
