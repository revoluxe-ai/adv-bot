# Decision: Card A/B Hold Write-Path Ownership

## Status

Proposed

## Context

Режим A/B Hold затрагивает write-path рекламы: setup ключей/whitelist, фиксацию и запрет обновления целевых позиций, guard перерасхода, а также координацию bot-пода и shop-runner-пода через Redis. Ordinary V3 preamble и параллельные ACT-корутины уже пишут в те же сущности (ключ / БС / ЦП / ставки). Без reusable правила ownership любой «if в orchestrator» или ручное переключение legacy-флагов снова смешает normal updater с hold и сделает A/B-тест карточки нестабильным.

Accepted decision `openspec/decisions/mode-defaults-policy-ownership/decision.md` закрывает только placement дефолтов paid/free overlays. Он не отвечает, кто владеет setup/hold write-path, какие ACT-пути должны быть заморожены и как PG-состояние режима соотносится с Redis-прерыванием между подами.

## Decision

A/B Hold — отдельный paid automation write-path с durable состоянием в кампании и cross-pod interrupt в Redis.

1. **Ownership pipeline:** setup ENTER и hold-тик принадлежат выделенному A/B Hold automation path в shop-runner (отдельные entrypoints / pipeline для setup и hold). Ordinary V3 NORMAL preamble не является владельцем структурных изменений на время PENDING_SETUP / ACTIVE.
2. **Scheduling:** при состоянии режима PENDING_SETUP или ACTIVE кампания MUST NOT планироваться в ordinary V3 structural update; запускаются только setup (пока PENDING_SETUP) или hold (пока ACTIVE).
2a. **Stats freshness asymmetry:** включение режима (UI / Excel / любой enable → PENDING_SETUP) MUST быть запрещено, если кампания не проходит тот же класс проверки свежести/доступности статы, что `_split_advs_by_stats_freshness` / попадание в `advs_filtred` (проблемы получения статистики по РК). После успешного переключения (PENDING_SETUP или ACTIVE) setup/hold MUST планироваться из полного eligible списка кампаний и MUST NOT блокироваться отсутствием в `advs_filtred` — сбои свежести статы после входа не должны оставлять РК в вечном PENDING и не должны отменять hold-тик только из‑за freshness gate.
2b. **Enable UX on stats block:** при отказе enable из‑за проблем статы пользователь MUST сразу видеть причину, текст ограничения и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (в кодовой базе нет singular `ADMIN`; whitelist админов — `ADMINS`; публичная ссылка поддержки для пользователя — `SUPPORT_LINK`).
3. **Structural freeze:** пока режим PENDING_SETUP или ACTIVE, структурные ACT-пути MUST NOT менять whitelist, целевые позиции, разгон/enable ключей и emergency structural mutations. Bidder path (ставки к уже зафиксированным ЦП) MUST оставаться разрешённым.
4. **Durable vs ephemeral:** PG-состояние режима (OFF / PENDING_SETUP / ACTIVE) — source of truth «в каком режиме живёт кампания». Redis signal / last-abort / setup-lock — только cross-pod координация прерывания и single-flight setup; Redis не заменяет PG-режим.
5. **Interrupt:** cooperative abort normal/hold тика через Redis signal читается в shop-runner; штатный early return до apply считается безопасным («остановлено, можно продолжать»). Abort mid-apply недопустим как штатный путь.
6. **Paid boundary:** enable / UI / Excel режима — только при `bot_active is True`. При `bot_active is False` UI скрыт, enable MUST NOT выполняться.
7. **Defaults:** дефолт режима «выкл» при paid/free overlays подчиняется `openspec/decisions/mode-defaults-policy-ownership/decision.md` (declarative overlays), не transition-helper и не UI-handler.

## Applies to

- Capability `card-ab-hold-mode`.
- Shop-runner ACT paths, затрагивающие whitelist, target place, keyword enable/mode ladder, overspend guards, bidder/cluster bids.
- Paid Telegram UI экрана A/B Hold и Excel roundtrip колонки режима.
- Cross-pod координация bot ↔ shop-runner для ENTER/EXIT.

## Allowed

- Отдельные setup/hold entrypoints вне ordinary V3 NORMAL preamble.
- Exclusion кампании из ordinary structural V3 scheduling при PENDING_SETUP / ACTIVE.
- Hold: только overspend/guard-подобная защита относительно max CPO; bidder продолжает работать к зафиксированным ЦП.
- Redis `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project Redis-паттернам (`AdvSettingRedisCache` + `RedisLockManager`).
- UI и enable только при `bot_active is True`.
- Enable дополнительно gate’ится на fresh/healthy stats (тот же freshness-класс, что исключает РК из ordinary automation при stale).
- Setup/hold scheduling для PENDING_SETUP / ACTIVE из полного eligible `advs` (не только `advs_filtred`).
- Alert/текст при blocked enable: причина + ограничение + `const.SUPPORT_LINK`.
- Дефолт «режим выкл» через paid/free mode policy overlays.

## Forbidden

- Реализовывать hold только комбинацией legacy-флагов без durable режима и without exclusion из ordinary V3.
- Держать hold/setup structural логику внутри ordinary V3 NORMAL preamble как «ещё одну ветку if» без отдельного owner path.
- Останавливать биддер как способ «заморозить» позиции (в т.ч. через `bot_active=False` ради A/B).
- Менять whitelist / target place / enable / structural emergency ACT во время PENDING_SETUP / ACTIVE.
- Считать Redis единственным source of truth режима кампании без PG-состояния.
- Прерывать после успешного apply как штатный «safe abort».
- Отдавать UI или enable режима при `bot_active is False`.
- Задавать дефолт режима прямым присваиванием в transition-helper / handler в обход mode policy overlays.
- Включать A/B Hold (PENDING), когда кампания не проходит freshness/stats-health gate.
- Планировать setup/hold **только** из `advs_filtred`, оставляя PENDING без тика при stale stats.
- Silent enable-fail без причины и без рекомендации со `SUPPORT_LINK`.

## Examples

Good:

- Клиент включает A/B Hold при fresh stats → PG `PENDING_SETUP` + Redis signal ENTER → ordinary V3 тик abort до apply → setup фиксирует ЦП на текущих → PG `ACTIVE` → дальше только hold + bidder.
- Клиент жмёт «Включить» при stale/stats problem → enable no-op; alert с reason + «обратитесь в поддержку» + `SUPPORT_LINK`; PG остаётся OFF.
- Parallel `update_top_key_in_advs` / individual target-place updater видит ACTIVE и не выполняет structural write.
- PENDING_SETUP при последующем stale всё равно получает `process_ab_setup` (не застревает из‑за `advs_filtred`).

Bad:

- Только `if card_ab_hold_mode` внутри ordinary preamble без exclusion scheduling и без gates на соседних ACT-корутинах.
- Выключить `bot_active`, чтобы «не мешать тесту» (биддер тоже останавливается).
- Хранить режим только в Redis без PG.
- Enable при проблемах статы «втихую» или setup только для fresh → вечный PENDING.

## Related specs

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md` (delta; создаётся в этом change)

## Related changes

- `openspec/changes/card-ab-hold-mode/`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`openspec/decisions/mode-defaults-policy-ownership/decision.md`)
- [x] new decision proposed because accepted decision was missing for hold write-path
- [x] implementation layer matches decision
- [x] tests verify structural freeze without masking placement violations
- [x] paid-only gate enforced for UI and enable paths
