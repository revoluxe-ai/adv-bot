# Decision: Card A/B Hold Write-Path Ownership

## Status

Proposed

## Context

Режим A/B Hold затрагивает write-path рекламы: setup ключей/whitelist, фиксацию и запрет обновления целевых позиций, guard перерасхода, freeze минус-фраз (PG snapshot + restore при drift), а также координацию bot-пода и shop-runner-пода через Redis. Ordinary V3 preamble, minus-phrase auto-update и параллельные ACT-корутины уже пишут в те же сущности (ключ / БС / ЦП / ставки / минус-фразы). Без reusable правила ownership любой «if в orchestrator» или ручное переключение legacy-флагов снова смешает normal updater с hold и сделает A/B-тест карточки нестабильным.

Accepted decision `openspec/decisions/mode-defaults-policy-ownership/decision.md` закрывает только placement дефолтов paid/free overlays (в т.ч. `auto_update_minus_phrases`). Он не отвечает, кто владеет setup/hold write-path, какие ACT-пути должны быть заморожены (включая минус-фразы), когда UI может заявить готовность A/B, как PG-состояние режима / snapshot соотносится с Redis-прерыванием между подами, и **запрещён ли Excel как write-path режима** в MVP.

Production bug: Excel `import_apply` мог выставить `card_ab_hold_mode=active` (или `pending_setup`) без ENTER minus sync+snapshot; `process_ab_setup` не бежит для уже ACTIVE → freeze/restore пустой или stale; UI ready-after-ACTIVE может врать.

## Decision

A/B Hold — отдельный paid automation write-path с durable состоянием в кампании и cross-pod interrupt в Redis.

1. **Ownership pipeline:** setup ENTER и hold-тик принадлежат выделенному A/B Hold automation path в shop-runner (отдельные entrypoints / pipeline для setup и hold). Ordinary V3 NORMAL preamble не является владельцем структурных изменений на время PENDING_SETUP / ACTIVE.
2. **Scheduling:** при состоянии режима PENDING_SETUP или ACTIVE кампания MUST NOT планироваться в ordinary V3 structural update; запускаются только setup (пока PENDING_SETUP) или hold (пока ACTIVE).
2a. **Stats freshness asymmetry:** включение режима (**paid Telegram UI** → PENDING_SETUP) MUST быть запрещено, если кампания не проходит тот же класс проверки свежести/доступности статы, что `_split_advs_by_stats_freshness` / попадание в `advs_filtred` (проблемы получения статистики по РК). После успешного переключения (PENDING_SETUP или ACTIVE) setup/hold MUST планироваться из полного eligible списка кампаний и MUST NOT блокироваться отсутствием в `advs_filtred` — сбои свежести статы после входа не должны оставлять РК в вечном PENDING и не должны отменять hold-тик только из‑за freshness gate.
2b. **Enable UX on stats block:** при отказе enable из‑за проблем статы пользователь MUST сразу видеть причину, текст ограничения и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (в кодовой базе нет singular `ADMIN`; whitelist админов — `ADMINS`; публичная ссылка поддержки для пользователя — `SUPPORT_LINK`).
3. **Structural freeze:** пока режим PENDING_SETUP или ACTIVE, структурные ACT-пути MUST NOT менять whitelist, целевые позиции, разгон/enable ключей, emergency structural mutations и ordinary recalculation минус-фраз (см. §8: snapshot + restore). Bidder path (ставки к уже зафиксированным ЦП) MUST оставаться разрешённым.
4. **Durable vs ephemeral:** PG-состояние режима (OFF / PENDING_SETUP / ACTIVE) — source of truth «в каком режиме живёт кампания». Redis signal / last-abort / setup-lock — только cross-pod координация прерывания и single-flight setup; Redis не заменяет PG-режим.
5. **Interrupt:** cooperative abort normal/hold тика через Redis signal читается в shop-runner; штатный early return до apply считается безопасным («остановлено, можно продолжать»). Abort mid-apply недопустим как штатный путь.
6. **Paid boundary:** enable / UI режима — только при `bot_active is True`. При `bot_active is False` UI скрыт, enable MUST NOT выполняться.
7. **Defaults:** дефолт режима «выкл» при paid/free overlays подчиняется `openspec/decisions/mode-defaults-policy-ownership/decision.md` (declarative overlays), не transition-helper и не UI-handler.
8. **Minus-phrases freeze + PG snapshot + UI readiness:** минус-фразы входят в structural freeze режима; snapshot хранится durable в PG; UI «можно запускать A/B» только после полного setup.
   - **ENTER / PENDING_SETUP (жёсткий порядок до ACTIVE):** (1) успешно довести минус-фразы до актуального состояния одной setup-мутацией / sync (не ordinary recalculation loop); (2) сохранить snapshot минус-фраз в PG (новое durable поле — **новая Alembic migration**, т.к. upgrade поля режима уже был); (3) завершить остальной setup профиля (критерии ключей / ЦП / БС); (4) только после всего выше setup MAY считаться завершённым и mode → **ACTIVE**.
   - **UI readiness (исключая гонку):** интерфейс MUST NOT сообщать, что режим включён и можно запускать A/B-тесты, пока mode ≠ **ACTIVE** после успешного завершения setup (включая минус-фразы + snapshot). Ответ «можно тестировать» на одном PENDING_SETUP / «запрос принят» без полного setup — Forbidden. Redis interrupt / setup lock MUST исключать готовность UI при незавершённом или прерванном setup.
   - **PENDING_SETUP / ACTIVE:** ordinary recalculation / auto-update минус-фраз MUST NOT; при drift текущих минус-фраз от snapshot бот MUST вернуть snapshot на WB; ручные правки в боте или кабинете WB считаются нарушением freeze и перезаписываются.
   - **EXIT → OFF:** ordinary auto-update минус-фраз снова разрешён; snapshot clear/archive; UI снимает статус готовности теста.
   - Snapshot минус-фраз — durable SoT в PG рядом с mode; Redis не заменяет PG-snapshot списка минус-фраз.
9. **Excel write-path (MVP — out):** Excel roundtrip MUST NOT экспортировать, импортировать или применять `card_ab_hold_mode` (колонки нет; если значение всё же попало в payload — apply MUST NO-OP / ignore). Excel MUST NOT переводить режим в `pending_setup`, `active` или `off`. Единственный enable/disable write-path в MVP — **paid Telegram UI** (ENABLE → PENDING_SETUP + Redis ENTER → setup → ACTIVE; DISABLE → OFF + clear minus snapshot). Прямой переход в `ACTIVE` любым non-setup путём (в т.ч. бывший Excel setattr) — **Forbidden** (§8). Excel-колонка / Excel enable A/B Hold — **future / out of MVP** (идея сохранена, не текущий контракт).

## Applies to

- Capability `card-ab-hold-mode`.
- Shop-runner ACT paths, затрагивающие whitelist, target place, keyword enable/mode ladder, overspend guards, bidder/cluster bids, **minus-phrase auto-update / set**.
- Paid Telegram UI экрана A/B Hold (вкл. readiness «можно запускать A/B») — **единственный** user-facing enable/disable path в MVP.
- Excel `adv_excel_roundtrip` — **запрет** колонки/apply `card_ab_hold_mode` в MVP (future option).
- Cross-pod координация bot ↔ shop-runner для ENTER/EXIT.
- PG durable snapshot минус-фраз (новая migration) и restore-write на WB при drift.

## Allowed

- Отдельные setup/hold entrypoints вне ordinary V3 NORMAL preamble.
- Exclusion кампании из ordinary structural V3 scheduling при PENDING_SETUP / ACTIVE.
- Hold: только overspend/guard-подобная защита относительно max CPO; bidder продолжает работать к зафиксированным ЦП.
- Redis `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project Redis-паттернам (`AdvSettingRedisCache` + `RedisLockManager`).
- UI и enable только при `bot_active is True` через paid Telegram handlers.
- Enable дополнительно gate’ится на fresh/healthy stats (тот же freshness-класс, что исключает РК из ordinary automation при stale).
- Setup/hold scheduling для PENDING_SETUP / ACTIVE из полного eligible `advs` (не только `advs_filtred`).
- Alert/текст при blocked enable: причина + ограничение + `const.SUPPORT_LINK`.
- Дефолт «режим выкл» через paid/free mode policy overlays.
- Одна setup-мутация / sync минус-фраз на ENTER до записи PG snapshot.
- PG snapshot минус-фраз + restore-to-snapshot write на WB при drift во время PENDING_SETUP / ACTIVE.
- UI «режим включён / можно запускать A/B» только после transition в ACTIVE (полный setup done).
- Clear/archive PG snapshot минус-фраз на EXIT → OFF.
- Ignore / no-op `card_ab_hold_mode` в Excel import/export schema (MVP).

## Forbidden

- Реализовывать hold только комбинацией legacy-флагов без durable режима и without exclusion из ordinary V3.
- Держать hold/setup structural логику внутри ordinary V3 NORMAL preamble как «ещё одну ветку if» без отдельного owner path.
- Останавливать биддер как способ «заморозить» позиции (в т.ч. через `bot_active=False` ради A/B).
- Менять whitelist / target place / enable / structural emergency ACT во время PENDING_SETUP / ACTIVE (кроме A/B setup/hold allowed paths и §8 restore-to-snapshot).
- Ordinary recalculation / auto-update минус-фраз во время PENDING_SETUP / ACTIVE (вместо freeze + restore-to-snapshot).
- Считать setup завершённым / переводить в ACTIVE без успешного актуального sync минус-фраз и записанного PG snapshot.
- Сообщать в UI, что режим включён и можно запускать A/B, пока mode ещё PENDING_SETUP или setup не завершён (гонка с незавершённым / прерванном setup).
- Считать Redis единственным source of truth режима кампании или snapshot минус-фраз без PG.
- Прерывать после успешного apply как штатный «safe abort».
- Отдавать UI или enable режима при `bot_active is False`.
- Задавать дефолт режима прямым присваиванием в transition-helper / handler в обход mode policy overlays.
- Включать A/B Hold (PENDING), когда кампания не проходит freshness/stats-health gate.
- Планировать setup/hold **только** из `advs_filtred`, оставляя PENDING без тика при stale stats.
- Silent enable-fail без причины и без рекомендации со `SUPPORT_LINK`.
- Excel export/import/apply колонки `card_ab_hold_mode` в MVP (включая enable `pending_setup`/`active` и disable `off` через Excel).
- Прямой setattr / import `card_ab_hold_mode=active` (или `pending_setup`) минуя Telegram ENTER + `process_ab_setup` (§8).

## Examples

Good:

- Клиент включает A/B Hold из Telegram при fresh stats → PG `PENDING_SETUP` + Redis signal ENTER → ordinary V3 тик abort до apply → setup: sync минус-фраз → PG snapshot → фиксация ЦП/БС → PG `ACTIVE` → UI: «режим включён, можно запускать A/B» → дальше hold + bidder + restore minus при drift.
- Во время ACTIVE пользователь меняет минус-фразы в кабинете WB → следующий hold/minus-freeze тик возвращает snapshot; ordinary recalculation не запускается.
- EXIT из Telegram → OFF → ordinary minus auto-update снова eligible; PG snapshot cleared/archived; UI больше не показывает «можно тестировать» по hold.
- Клиент жмёт «Включить» при stale/stats problem → enable no-op; alert с reason + «обратитесь в поддержку» + `SUPPORT_LINK`; PG остаётся OFF.
- Parallel `update_top_key_in_advs` / individual target-place updater видит ACTIVE и не выполняет structural write.
- PENDING_SETUP при последующем stale всё равно получает `process_ab_setup` (не застревает из‑за `advs_filtred`).
- Excel import с полем `card_ab_hold_mode` игнорируется / колонка отсутствует в schema; режим не меняется.

Bad:

- Только `if card_ab_hold_mode` внутри ordinary preamble без exclusion scheduling и без gates на соседних ACT-корутинах.
- Выключить `bot_active`, чтобы «не мешать тесту» (биддер тоже останавливается).
- Хранить режим только в Redis без PG.
- Enable при проблемах статы «втихую» или setup только для fresh → вечный PENDING.
- UI пишет «можно запускать A/B» сразу после PENDING_SETUP, до sync/snapshot минус-фраз и ACTIVE.
- Во время ACTIVE продолжает ordinary `update_minus_phrases` recalculation и игнорирует drift от snapshot.
- Excel import `card_ab_hold_mode=active` (или `pending_setup`) через `can_apply_card_ab_hold_mode_via_excel` + setattr — ACTIVE без ENTER minus sync/snapshot.

## Related specs

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md` (delta; создаётся в этом change)

## Related changes

- `openspec/changes/card-ab-hold-mode/`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`openspec/decisions/mode-defaults-policy-ownership/decision.md`)
- [x] new decision proposed because accepted decision was missing for hold write-path
- [x] implementation layer matches decision *(delta §9 Excel out — code via `/opsx-apply`)*
- [x] tests verify structural freeze without masking placement violations
- [x] paid-only gate enforced for UI and enable paths
