# Decision: Card A/B Hold Write-Path Ownership

## Status

Proposed

## Context

Режим A/B Hold затрагивает write-path рекламы: setup ключей/whitelist, фиксацию и запрет обновления целевых позиций, guard перерасхода, freeze разрешённого набора фраз (allowed-set PG snapshot + enforcement исключения не-разрешённых фраз во время hold; минус — derived), а также координацию bot-пода и shop-runner-пода через Redis. Ordinary V3 preamble, minus-phrase auto-update и параллельные ACT-корутины уже пишут в те же сущности (ключ / БС / ЦП / ставки / минус-фразы). Без reusable правила ownership любой «if в orchestrator» или ручное переключение legacy-флагов снова смешает normal updater с hold и сделает A/B-тест карточки нестабильным.

Accepted decision `openspec/decisions/mode-defaults-policy-ownership/decision.md` закрывает только placement дефолтов paid/free overlays (в т.ч. `auto_update_minus_phrases`). Он не отвечает, кто владеет setup/hold write-path, какие ACT-пути должны быть заморожены (включая минус-фразы), когда UI может заявить готовность A/B, как PG-состояние режима / snapshot соотносится с Redis-прерыванием между подами, и **запрещён ли Excel как write-path режима** в MVP.

Production bug: Excel `import_apply` мог выставить `card_ab_hold_mode=active` (или `pending_setup`) без ENTER allowed-set snapshot; `process_ab_setup` не бежит для уже ACTIVE → freeze/enforcement пустой или stale; UI ready-after-ACTIVE может врать.

## Decision

A/B Hold — отдельный paid automation write-path с durable состоянием в кампании и cross-pod interrupt в Redis.

1. **Ownership pipeline:** setup ENTER и hold-тик принадлежат выделенному A/B Hold automation path в shop-runner (отдельные entrypoints / pipeline для setup и hold). Ordinary V3 NORMAL preamble не является владельцем структурных изменений на время PENDING_SETUP / ACTIVE.
2. **Scheduling:** при состоянии режима PENDING_SETUP или ACTIVE кампания MUST NOT планироваться в ordinary V3 structural update; запускаются только setup (пока PENDING_SETUP) или hold (пока ACTIVE).
2a. **Stats freshness asymmetry:** включение режима (**paid Telegram UI** → PENDING_SETUP) MUST быть запрещено, если кампания не проходит тот же класс проверки свежести/доступности статы, что `_split_advs_by_stats_freshness` / попадание в `advs_filtred` (проблемы получения статистики по РК). После успешного переключения (PENDING_SETUP или ACTIVE) setup/hold MUST планироваться из полного eligible списка кампаний и MUST NOT блокироваться отсутствием в `advs_filtred` — сбои свежести статы после входа не должны оставлять РК в вечном PENDING и не должны отменять hold-тик только из‑за freshness gate.
2b. **Enable UX on stats block:** при отказе enable из‑за проблем статы пользователь MUST сразу видеть причину, текст ограничения и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (в кодовой базе нет singular `ADMIN`; whitelist админов — `ADMINS`; публичная ссылка поддержки для пользователя — `SUPPORT_LINK`).
2c. **Launch validity soft-gate (низкий объём показов):** при попытке enable (**paid Telegram UI** → PENDING_SETUP), после прохождения freshness/health гейта (§2a), система MUST оценить суммарные недавние показы (окно последних 24ч из того же источника статистики кампании, что и карточки ключей) ключей-кандидатов теста. Если сумма ниже минимального порога недавних показов, enable MUST NOT выполняться молча: пользователю MUST быть показана причина (мало показов для надёжного A/B-теста), рекомендация поднять план max CPO и повторить попытку, и явный выбор «всё равно запустить» / «отмена». До выбора mode MUST оставаться `OFF`; «всё равно запустить» → `PENDING_SETUP` + Redis ENTER; «отмена» → `OFF` без ENTER. Это **soft-gate** (предупреждение, не hard block; пользователь MAY продолжить на свой риск), в отличие от freshness hard-block (§2a) и правила пустого allowed-set (не-ready, §8). Конкретный порог и источник запроса — implementation-деталь design; owner — тот же bot enable write-path (paid Telegram UI), что §2a/2b.
3. **Structural freeze:** пока режим PENDING_SETUP или ACTIVE, структурные ACT-пути MUST NOT менять whitelist, целевые позиции, разгон/enable ключей, emergency structural mutations и ordinary recalculation минус-фраз (см. §8: snapshot + restore). Bidder path (ставки к уже зафиксированным ЦП) MUST оставаться разрешённым.
4. **Durable vs ephemeral:** PG-состояние режима (OFF / PENDING_SETUP / ACTIVE) — source of truth «в каком режиме живёт кампания». Redis signal / last-abort / setup-lock — только cross-pod координация прерывания и single-flight setup; Redis не заменяет PG-режим.
5. **Interrupt:** cooperative abort normal/hold тика через Redis signal читается в shop-runner; штатный early return до apply считается безопасным («остановлено, можно продолжать»). Abort mid-apply недопустим как штатный путь.
6. **Paid boundary:** enable / UI режима — только при `bot_active is True`. При `bot_active is False` UI скрыт, enable MUST NOT выполняться.
7. **Defaults:** дефолт режима «выкл» при paid/free overlays подчиняется `openspec/decisions/mode-defaults-policy-ownership/decision.md` (declarative overlays), не transition-helper и не UI-handler.
8. **Allowed-phrase-set freeze + PG snapshot + UI readiness:** **primary invariant** режима — заморозить **разрешённый (relevant) набор фраз** кампании (relevant-фразы + получившийся GOOD/whitelist профиль ключей), а не список минус-фраз. Минус-лист — **производный механизм принудительного исключения** (derived enforcement), а не замораживаемая сущность. Переиспользуется существующая модель `auto_add_only_relevant_phrase` / `relevant_phrases` / `NOT_RELEVANT_PHRASE` (не-разрешённая фраза → BAD → минус). allowed-set snapshot хранится durable в PG; UI «можно запускать A/B» только после полного setup.
   - **ENTER / PENDING_SETUP (жёсткий порядок до ACTIVE):** (1) зафиксировать разрешённый набор фраз (relevant-фразы + GOOD/whitelist тексты ключей) и сохранить как durable allowed-set snapshot в PG (новое durable поле — **новая Alembic migration**, т.к. upgrade поля режима уже был); (2) одной setup-мутацией / sync привести WB к этому состоянию — исключить (минус) всё, что вне allowed-set, в пределах WB minus cap (не ordinary recalculation loop); (3) завершить остальной setup профиля (критерии ключей / ЦП / БС); (4) только после успешной записи allowed-set snapshot и всего выше setup MAY считаться завершённым и mode → **ACTIVE**.
   - **UI readiness (исключая гонку):** интерфейс MUST NOT сообщать, что режим включён и можно запускать A/B-тесты, пока mode ≠ **ACTIVE** после успешного завершения setup (включая allowed-set snapshot). Ответ «можно тестировать» на одном PENDING_SETUP / «запрос принят» без полного setup — Forbidden. Redis interrupt / setup lock MUST исключать готовность UI при незавершённом или прерванном setup.
   - **PENDING_SETUP / ACTIVE (hold enforcement ≠ ordinary recalculation):** ordinary recalculation / auto-update минус-фраз — то есть пересчёт GOOD/BAD по свежей стате и **изменение** allowed-set — MUST NOT (allowed-set заморожен). Отдельно и независимо от этого, hold-protection MUST поддерживать фактическую поверхность трат равной замороженному allowed-set: любые новые / не-разрешённые фразы, появившиеся после ENTER, MUST исключаться (минус как enforcement), а разрешённые фразы, снятые вручную, MUST восстанавливаться. Ручные правки в боте или кабинете WB считаются нарушением freeze и перезаписываются. Bot callback ordinary minus refresh («Обновить минус-слова») при freeze MUST NOT сообщать success; MUST объяснить, что набор фраз зафиксирован и для изменений нужен EXIT / disable A/B Hold. Silent no-op с «Минус-слова обновлены» — Forbidden.
   - **WB minus cap (видимая деградация, не тихий обман):** enforcement производного минус-листа ограничен лимитом WB (~1000 фраз на nmid). Если для удержания замороженного allowed-set требуется исключить больше фраз, чем допускает cap, система MUST деградировать **видимо** (лог ERROR/WARN + честный статус, что hold **не может** гарантировать чистую поверхность для этой РК) и MUST NOT молча заявлять чистый hold. Для типов кампаний с открытым матчингом (open-match), где controllability через минус не доказана реализацией, freeze — **best-effort**, а не гарантированный; UI / справка не должны обещать полную заморозку без привязки к типу РК и cap-feasibility.
   - **EXIT → OFF:** ordinary auto-update минус-фраз и recalculation allowed-set снова разрешены; allowed-set snapshot clear/archive; UI снимает статус готовности теста.
   - Allowed-set snapshot — durable SoT в PG рядом с mode; Redis не заменяет PG-snapshot разрешённого набора фраз.
9. **Excel write-path (MVP — out):** Excel roundtrip MUST NOT экспортировать, импортировать или применять `card_ab_hold_mode` (колонки нет; если значение всё же попало в payload — apply MUST NO-OP / ignore). Excel MUST NOT переводить режим в `pending_setup`, `active` или `off`. Единственный enable/disable write-path в MVP — **paid Telegram UI** (ENABLE from `OFF` → PENDING_SETUP + Redis ENTER → setup → ACTIVE; DISABLE → OFF + clear allowed-set snapshot). Прямой переход в `ACTIVE` любым non-setup путём (в т.ч. бывший Excel setattr) — **Forbidden** (§8). Excel-колонка / Excel enable A/B Hold — **future / out of MVP** (идея сохранена, не текущий контракт).
10. **Telegram Enable idempotent while PENDING_SETUP / ACTIVE:** Enable MUST NO-OP (mode unchanged; no Redis ENTER rewrite; no re-trigger of ENTER `force_ab_hold_setup_sync`) when mode is already `PENDING_SETUP` or `ACTIVE`. Demote `ACTIVE`→`PENDING_SETUP` via Enable — **Forbidden** (ломает minus freeze / re-runs ENTER sync mid-hold). EXIT → `OFF` (+ clear snapshot) — единственный MVP path перед новым ENTER. In-flight shop-runner setup при стабильном `PENDING_SETUP` (lock) — Allowed и не считается re-ENTER от Enable. Handler no-op remains the safety net even if the button is still visible or a stale callback arrives.
11. **Telegram keyboard MAY hide Enable while PENDING_SETUP / ACTIVE:** A/B Hold screen keyboard MUST always offer Disable and Back. Enable MUST be offered when mode is `OFF` (subject to paid/access gates). When mode is `PENDING_SETUP` or `ACTIVE`, the UI MAY omit the Enable button to reduce accidental presses; this is Allowed UX and does not change write ownership. Hiding Enable MUST NOT be the sole protection — §10 handler no-op remains mandatory.
12. **A/B Hold — только V3 auto-updater + взаимоисключение с V2:** enable A/B Hold MUST быть разрешён только при `automatic_version == 3`; enable на не-V3 РК — no-op (mode остаётся `OFF`) + причина «A/B Hold требует V3». Пока mode `PENDING_SETUP` / `ACTIVE`, переключение версии авто-апдейтера на V2 MUST быть заблокировано (сначала EXIT → `OFF`). Owner: paid Telegram enable handler (`enable_card_ab_hold` / `ui_access`) — V3-gate рядом с paid/freshness gates; `auto_updater_version_toggle` handler — downgrade-block при активном режиме. Авто-переключатель стратегии РК (`change_adv_strategy`, MIN_CPO/MAX_CONV) — **V2-scope** и вне structural freeze §3: A/B Hold не добавляет отдельный freeze-гард на этот путь, а held V3-профиль MUST NOT управляться этим campaign-level strategy objective. Развязка V3 keyword `strategy_mode` от `AdvSetting.strategy` — отдельная задача вне этого change (не в scope decision).
13. **Shared defaults application ≠ A/B Hold disable path:** shared campaign-defaults application (`apply_defaults_to_adv_setting`, «Применить дефолты» single/shop-wide handlers) MUST NOT disable/mutate A/B Hold на кампании в `PENDING_SETUP` / `ACTIVE`: MUST NOT форсить `card_ab_hold_mode=off`, MUST NOT очищать / оставлять stale allowed-set snapshot, MUST NOT сбрасывать A/B-Hold-coupled структурные поля (`automatic_version`→non-V3, whitelist/target-place automation, bidder profile) в обход freeze / V3-only. Disable — только owned paid Telegram EXIT (§9). Для `OFF`-кампаний defaults применяются как обычно. §7 (default off via overlays для новых / сброса) не отменяется; §13 запрещает именно un-owned disable held-кампании.

## Applies to

- Capability `card-ab-hold-mode`.
- Shop-runner ACT paths, затрагивающие whitelist, target place, keyword enable/mode ladder, overspend guards, bidder/cluster bids, **minus-phrase auto-update / set**.
- Paid Telegram UI экрана A/B Hold (вкл. readiness «можно запускать A/B») — **единственный** user-facing enable/disable path в MVP.
- Excel `adv_excel_roundtrip` — **запрет** колонки/apply `card_ab_hold_mode` в MVP (future option).
- Cross-pod координация bot ↔ shop-runner для ENTER/EXIT.
- PG durable allowed-set snapshot (новая migration) и enforcement-write на WB (исключение не-разрешённых фраз, восстановление снятых разрешённых) при drift, в пределах WB minus cap.

## Allowed

- Отдельные setup/hold entrypoints вне ordinary V3 NORMAL preamble.
- Exclusion кампании из ordinary structural V3 scheduling при PENDING_SETUP / ACTIVE.
- Hold: только overspend/guard-подобная защита относительно max CPO; bidder продолжает работать к зафиксированным ЦП.
- `ensure_campaigns_active` (`auto_budget_watchdog`) — ортогональный ОБРАТИМЫЙ activity-lifecycle (budget/spend/balance/schedule/rec_system run↔pause): при PENDING_SETUP / ACTIVE Allowed и НЕ structural-freeze нарушение, т.к. не мутирует allowed-set / ЦП / whitelist / enable / minus и возвращает РК в то же замороженное состояние; bidder eligibility сохраняется отдельно (`filter_bidder_eligible_by_ab_hold`). MUST NOT расширять этот путь до мутации frozen-сущностей.
- Redis `CardAbHoldSignal` / `CardAbHoldLastAbort` / `CardAbHoldSetupLock` по project Redis-паттернам (`AdvSettingRedisCache` + `RedisLockManager`).
- UI и enable только при `bot_active is True` через paid Telegram handlers.
- Enable from `OFF` (+ stats gate) → `PENDING_SETUP` + Redis ENTER; Enable while already `PENDING_SETUP` / `ACTIVE` → no-op (§10).
- Keyboard MAY omit Enable button while `PENDING_SETUP` / `ACTIVE`; Disable and Back MUST remain (§11). Enable while `OFF` MUST still be offered (subject to paid/access gates).
- Enable дополнительно gate’ится на fresh/healthy stats (тот же freshness-класс, что исключает РК из ordinary automation при stale).
- Enable soft-gate по объёму теста: при суммарных недавних показах (окно 24ч) ключей-кандидатов ниже порога — предупреждение с причиной, рекомендацией поднять max CPO и повтором, и выбором «всё равно запустить» / «отмена»; пользователь MAY продолжить на свой риск (§2c).
- Setup/hold scheduling для PENDING_SETUP / ACTIVE из полного eligible `advs` (не только `advs_filtred`).
- Alert/текст при blocked enable: причина + ограничение + `const.SUPPORT_LINK`.
- Дефолт «режим выкл» через paid/free mode policy overlays.
- Одна setup-мутация / sync на ENTER (привести WB к allowed-set) до записи PG allowed-set snapshot.
- PG allowed-set snapshot + enforcement-write на WB (исключение новых/не-разрешённых фраз, восстановление снятых разрешённых) во время PENDING_SETUP / ACTIVE, в пределах WB minus cap.
- Видимая деградация (лог + честный статус) при превышении WB minus cap; best-effort для open-match типов РК без доказанной controllability.
- UI «режим включён / можно запускать A/B» только после transition в ACTIVE (полный setup done).
- Clear/archive PG allowed-set snapshot на EXIT → OFF.
- Ignore / no-op `card_ab_hold_mode` в Excel import/export schema (MVP).
- Enable A/B Hold только при `automatic_version == 3`; блок переключения на V2, пока mode `PENDING_SETUP` / `ACTIVE` (EXIT → OFF сначала).
- Трактовать `change_adv_strategy` (MIN_CPO/MAX_CONV) как V2-scope вне A/B Hold freeze; held V3-профиль не зависит от campaign strategy objective.

## Forbidden

- Реализовывать hold только комбинацией legacy-флагов без durable режима и without exclusion из ordinary V3.
- Держать hold/setup structural логику внутри ordinary V3 NORMAL preamble как «ещё одну ветку if» без отдельного owner path.
- Останавливать биддер как способ «заморозить» позиции (в т.ч. через `bot_active=False` ради A/B).
- Менять whitelist / target place / enable / structural emergency ACT во время PENDING_SETUP / ACTIVE (кроме A/B setup/hold allowed paths и §8 allowed-set enforcement).
- Ordinary recalculation / auto-update минус-фраз (изменение allowed-set по свежей стате) во время PENDING_SETUP / ACTIVE (вместо freeze allowed-set + hold enforcement).
- Считать setup завершённым / переводить в ACTIVE без зафиксированного и записанного PG allowed-set snapshot.
- Молча заявлять чистый hold, когда enforcement замороженного allowed-set превышает WB minus cap или РК open-match без доказанной controllability (нужна видимая деградация).
- Сообщать в UI, что режим включён и можно запускать A/B, пока mode ещё PENDING_SETUP или setup не завершён (гонка с незавершённым / прерванном setup).
- Считать Redis единственным source of truth режима кампании или allowed-set snapshot без PG.
- Прерывать после успешного apply как штатный «safe abort».
- Отдавать UI или enable режима при `bot_active is False`.
- Задавать дефолт режима прямым присваиванием в transition-helper / handler в обход mode policy overlays.
- Включать A/B Hold (PENDING), когда кампания не проходит freshness/stats-health gate.
- Планировать setup/hold **только** из `advs_filtred`, оставляя PENDING без тика при stale stats.
- Silent enable-fail без причины и без рекомендации со `SUPPORT_LINK`.
- Молча включать A/B Hold (PENDING), когда суммарные недавние показы ключей-кандидатов (окно 24ч) ниже порога, без причины, рекомендации поднять max CPO и явного выбора запустить/отмена (§2c).
- Excel export/import/apply колонки `card_ab_hold_mode` в MVP (включая enable `pending_setup`/`active` и disable `off` через Excel).
- Telegram Enable demote `ACTIVE`→`PENDING_SETUP` (или rewrite ENTER / restart force setup sync) while already `PENDING_SETUP` / `ACTIVE`.
- Прямой setattr / import `card_ab_hold_mode=active` (или `pending_setup`) минуя Telegram ENTER + `process_ab_setup` (§8).
- Включать A/B Hold на не-V3 РК (`automatic_version != 3`) или переключать РК на V2, пока mode `PENDING_SETUP` / `ACTIVE`.
- Добавлять A/B Hold freeze-гард на V2 `change_adv_strategy` или позволять campaign strategy objective менять held V3-профиль.
- Отключать / сбрасывать A/B Hold held-кампании (`PENDING_SETUP` / `ACTIVE`) через shared defaults / «Применить дефолты» в обход owned Telegram EXIT (§13).

## Examples

Good:

- Клиент включает A/B Hold из Telegram при fresh stats → PG `PENDING_SETUP` + Redis signal ENTER → ordinary V3 тик abort до apply → setup: фиксация allowed-set (relevant + GOOD ключи) → PG allowed-set snapshot → sync WB к allowed-set → фиксация ЦП/БС → PG `ACTIVE` → UI: «режим включён, можно запускать A/B» → дальше hold + bidder + enforcement (исключение не-разрешённых фраз) при drift.
- Во время ACTIVE появляется новая фраза или пользователь меняет минус в кабинете WB → следующий hold-тик приводит поверхность к замороженному allowed-set (исключает не-разрешённые, восстанавливает снятые разрешённые); ordinary recalculation allowed-set не запускается.
- EXIT из Telegram → OFF → ordinary minus auto-update + recalculation allowed-set снова eligible; PG allowed-set snapshot cleared/archived; UI больше не показывает «можно тестировать» по hold.
- Клиент жмёт «Включить» при stale/stats problem → enable no-op; alert с reason + «обратитесь в поддержку» + `SUPPORT_LINK`; PG остаётся OFF.
- Parallel `update_top_key_in_advs` / individual target-place updater видит ACTIVE и не выполняет structural write.
- PENDING_SETUP при последующем stale всё равно получает `process_ab_setup` (не застревает из‑за `advs_filtred`).
- Excel import с полем `card_ab_hold_mode` игнорируется / колонка отсутствует в schema; режим не меняется.

Bad:

- Только `if card_ab_hold_mode` внутри ordinary preamble без exclusion scheduling и без gates на соседних ACT-корутинах.
- Выключить `bot_active`, чтобы «не мешать тесту» (биддер тоже останавливается).
- Хранить режим только в Redis без PG.
- Enable при проблемах статы «втихую» или setup только для fresh → вечный PENDING.
- UI пишет «можно запускать A/B» сразу после PENDING_SETUP, до allowed-set snapshot и ACTIVE.
- Во время ACTIVE продолжает ordinary `update_minus_phrases` recalculation (меняет allowed-set) или игнорирует появление новых не-разрешённых фраз (они откручиваются).
- Excel import `card_ab_hold_mode=active` (или `pending_setup`) через `can_apply_card_ab_hold_mode_via_excel` + setattr — ACTIVE без ENTER allowed-set snapshot.
- Telegram Enable на ACTIVE (или повторный Enable на PENDING) demote/rewrite ENTER и заново гоняет force setup sync mid-hold.
- Enforcement замороженного allowed-set требует больше фраз, чем WB minus cap, но бот молча рапортует чистый hold вместо видимой деградации.
- «Применить дефолты» (single или shop-wide) на `ACTIVE` РК молча ставит `off`, оставляет непустой allowed-set snapshot и сбивает `automatic_version` на V2 (un-owned disable в обход EXIT).

## Related specs

- `openspec/changes/card-ab-hold-mode/specs/card-ab-hold-mode/spec.md` (delta; создаётся в этом change)

## Related changes

- `openspec/changes/card-ab-hold-mode/`

## Review checklist

- [x] existing decisions searched
- [x] relevant decisions cited (`openspec/decisions/mode-defaults-policy-ownership/decision.md`)
- [x] new decision proposed because accepted decision was missing for hold write-path
- [x] implementation layer matches decision *(delta §9 Excel out — applied; delta §10 Enable idempotent — applied via `/opsx-fix-bug GO`; delta §11 hide Enable — applied via `/opsx:apply`; delta §13 shared-defaults not a disable path — proposed, not yet applied, tracked in tasks §15)*
- [x] tests verify structural freeze without masking placement violations
- [x] paid-only gate enforced for UI and enable paths
