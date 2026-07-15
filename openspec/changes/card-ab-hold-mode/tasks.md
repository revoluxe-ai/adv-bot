## 1. Tests-first: characterization и gates

- [x] 1.1 Добавить characterization-тесты текущего scheduling ordinary V3 / structural ACT для campaign с `bot_active=True` до введения A/B Hold (базовая матрица «что вызывается»).
- [x] 1.2 Добавить unit-тесты decision setup ENTER (spec `card-ab-hold-mode`): PASS при `pay_for_order ≤ max CPO` и `views ≥ 100`; FAIL→OFF при PFO >, views < 100, PFO missing — без мока самой decision-функции.
- [x] 1.3 Добавить paired gate-тесты paid visibility: при `bot_active=False` UI entry скрыт / enable no-op; при `bot_active=True` экран доступен (spec paid-only).
- [x] 1.4 Добавить write-gate тесты structural freeze на ACTIVE/PENDING_SETUP: top-key whitelist, individual target-place, WL trim не доходят до WB write boundary; paired positive при mode OFF.
- [x] 1.5 Добавить write-gate: bidder / cluster bids остаются допустимы при ACTIVE (биддер MUST работать).
- [x] 1.6 Добавить тест interrupt: signal ENTER до apply → structural apply не вызывается, результат «safe / can continue».
- [x] 1.7 Добавить тест EXIT: после выключения ordinary target-place update снова eligible; snapshot restore не требуется.
- [x] 1.8 Добавить тест Excel apply: enable A/B Hold при `bot_active=False` не применяется.

## 2. Модель состояния и defaults

- [x] 2.1 Добавить PG-поле durable режима кампании OFF / PENDING_SETUP / ACTIVE с default OFF (миграция).
- [x] 2.2 Провести default «выкл» через mode policy overlays (accepted `mode-defaults-policy-ownership`); без прямого присваивания в transition-helper.
- [x] 2.3 Прокинуть режим в DTO кампании / ComplexAdv для scheduler и UI gates.

## 3. Redis coordination (project patterns)

- [x] 3.1 Реализовать `CardAbHoldSignal` cache (`AdvSettingRedisCache` + `RedisCacheBase`, TTL ~15 мин).
- [x] 3.2 Реализовать `CardAbHoldLastAbort` cache (safe/can_continue/reason/at, TTL ~1 ч).
- [x] 3.3 Setup lock через `RedisLockManager` с ключом `CardAbHoldSetupLock:{adv_id}` (TTL ~5 мин).
- [x] 3.4 Unit-тесты Redis roundtrip / lock NX без лишних MagicMock доменных моделей.

## 4. Setup / Hold pipelines и scheduling

- [x] 4.1 Реализовать decision + apply ENTER setup: классификация ключей, OFF на FAIL, ЦП := текущая фактическая на PASS, flush через существующий apply path.
- [x] 4.2 Реализовать hold-тик: только overspend/PFO-max guard; без TP update / WL / enable / calibration UP.
- [x] 4.3 Встроить scheduling exclusion: PENDING_SETUP→setup, ACTIVE→hold, OFF→ordinary V3; ordinary structural не schedule’ится на PENDING/ACTIVE.
- [x] 4.4 Встроить interrupt check-points (после load и до apply) в ordinary structural path.
- [x] 4.5 Добавить structural ACT guards на параллельные корутины (whitelist top-key, individual TP, trim, emergency structural) при PENDING/ACTIVE.

## 5. Paid UI и Excel

- [x] 5.1 Экран A/B Hold: инструкция (прогрев max CPO / план / полки recommend-off / не менять цену) + кнопки включить / выключить / назад.
- [x] 5.2 Handler enable: gate `bot_active`, PG PENDING_SETUP, Redis ENTER, poll last-abort / ACTIVE; docstring со ссылкой на spec.
- [x] 5.3 Handler disable: EXIT → PG OFF + signal cleanup; без restore.
- [x] 5.4 Скрыть entry при `bot_active=False`.
- [x] 5.5 Excel EDIT-колонка режима; apply только при `bot_active=True`.

## 6. Документация и проверка

- [x] 6.1 Русские docstrings на новых/изменённых публичных модулях, классах, методах и тестах с указанием spec `card-ab-hold-mode` и обоснованием.
- [x] 6.2 Прогнать focused unit + ab_hold gate tests.
- [x] 6.3 Запустить `poetry run pyright-strict` на затронутых путях (или project gate) и `git diff --check`.
- [x] 6.4 Сверить placement с proposed decision `card-ab-hold-write-path-ownership` (нет sole-if в ordinary preamble, биддер не останавливается).
- [x] 6.5 Verify remediations: `filter_structural_act_candidates` wired in manager ACT paths + boundary write-gate tests; Excel shared gate; enable polls LastAbort; design open questions resolved.

## 7. Stats freshness: enable gate + post-enter schedule (update)

- [x] 7.1 Enable gate: UI/Excel MUST NOT → PENDING, если РК не проходит freshness/health класс `_split_advs_by_stats_freshness` (не в fresh set).
- [x] 7.2 UI при blocked enable: сразу показать причину, текст ограничения включения теста и рекомендацию обратиться в поддержку/к админу со ссылкой `app.client_bot.const.SUPPORT_LINK` (не silent fail; в коде нет `ADMIN`, whitelist — `ADMINS`).
- [x] 7.3 Scheduling: `process_ab_setup` / `process_ab_hold` из полного eligible `advs` (не только `advs_filtred`); V2 freshness контракт не ломать без нужды.
- [x] 7.4 Tests: paired — enable blocked when stale + сообщение содержит reason/`SUPPORT_LINK`; PENDING+stale всё равно eligible для setup; ACTIVE+stale eligible для hold.
- [x] 7.5 Docstrings / ссылка на updated spec requirements (enable blocked when stats freshness fails; post-enter schedule).

## 8. Allowed-phrase-set freeze + hold enforcement + UI readiness after ACTIVE (update — decision §8 REDEFINED)

> Supersedes the earlier minus-snapshot/restore design of this section. Frozen unit = allowed (relevant) phrase set; minus = derived enforcement only. Checkboxes reset to unbuilt: the previously-implemented minus-snapshot behavior no longer matches decision §8 and must be redone via `/opsx:apply`.

- [x] 8.1 Tests-first: setup MUST capture allowed-set → PG allowed-set snapshot → ACTIVE; fail capture/snapshot → no ACTIVE / UI not ready.
- [x] 8.2 Tests-first: PENDING/ACTIVE → ordinary `update_minus_phrases` recalc (изменение allowed-set) не применяется; **новая не-разрешённая фраза → исключается**; снятая вручную разрешённая фраза → восстанавливается; paired positive при mode OFF.
- [x] 8.3 Tests-first: UI ready-to-test / «можно запускать A/B» только при ACTIVE; PENDING не показывает ready; EXIT clear/archive allowed-set snapshot + ordinary minus/recalc снова eligible.
- [x] 8.4 Alembic migration: durable PG поле **allowed-set** snapshot на кампании (relevant-фразы + GOOD/whitelist тексты) (+ модель/DTO); переопределить/переименовать ранее введённое snapshot-поле; не переиспользовать migration режима.
- [x] 8.5 ENTER setup: зафиксировать allowed-set (переиспользуя `auto_add_only_relevant_phrase` / `relevant_phrases` / `NOT_RELEVANT_PHRASE`) → записать PG allowed-set snapshot → одной setup sync привести WB к allowed-set (исключить вне набора в пределах WB minus cap) → только затем mode → ACTIVE (decision §8).
- [x] 8.6 Gate ordinary recalculation allowed-set в manager / MinusPhraseManager при PENDING_SETUP / ACTIVE; **отдельный** hold-enforcement path: исключать новые/не-разрешённые фразы и восстанавливать снятые разрешённые к замороженному allowed-set (минус как enforcement, hold-protection ≠ ordinary recalc).
- [x] 8.7 WB minus cap / open-match: если enforcement замороженного allowed-set превышает cap (или тип РК open-match без доказанной controllability) — **видимая деградация** (лог ERROR/WARN + честный статус, что hold не гарантирован); MUST NOT молча заявлять чистый hold.
- [x] 8.8 EXIT: clear/archive PG allowed-set snapshot; ordinary minus auto-update + allowed-set recalc снова разрешены; без keyword-profile restore.
- [x] 8.9 UI: текст инструкции про фиксацию **набора фраз** (новые исключаются) / restore из WB / «чтобы изменить набор — отключите A/B Hold»; scoped/best-effort wording (не обещать полную заморозку вне типа РК / WB cap); ready message только после ACTIVE (исключая гонку с PENDING).
- [x] 8.10 Regression test (доказывает исправление bug): в ACTIVE hold новая не-разрешённая фраза исключается, снятая разрешённая восстанавливается; enforcement ≠ ordinary recalc; при превышении WB cap — видимая деградация, не тихий success.
- [x] 8.11 Docstrings + focused pytest на 8.1–8.3 / 8.10; сверка placement с decision §8 (allowed-set — primary invariant, minus — derived).
- [x] 8.12 Honest degradation durable SoT (decision §8, owner = A/B Hold write-path): новое PG-поле `card_ab_hold_degraded` (+ Alembic migration) на `AdvSetting`; `process_ab_setup` персистит вместе с mode → ACTIVE, `process_ab_hold` — durable флаг из `enforce["cap_exceeded"]` со self-healing (снятие, когда cap не превышен). Закрывает разрыв «enforcement логировал cap_exceeded, но не персистил».
- [x] 8.13 Honest status в UI читает durable флаг: `build_enter_poll_status_lines(degraded=…)` и `card_ab_hold_status_label` при ACTIVE + degraded НЕ заявляют чистый hold; regression — paired degraded/not-degraded + write-boundary тест реального PG update поля (`test_minus_freeze.py`).

## 9. Remove Excel A/B Hold write-path (update — decision §9)

> Supersedes Excel enable/edit intent of 1.8 / 5.5 / Excel parts of 7.1: MVP = Telegram-only; Excel column/apply removed (future option separately).

- [x] 9.1 Tests-first: Excel import `active` / `pending_setup` / `off` → mode unchanged; schema MUST NOT expose EDIT column `card_ab_hold_mode`.
- [x] 9.2 Remove `card_ab_hold_mode` from Excel schema export/import (fields, labels, parse).
- [x] 9.3 `import_apply`: MUST NOT apply `card_ab_hold_mode` (ignore/no-op); disable Excel enable path (`can_apply_card_ab_hold_mode_via_excel` always deny non-ignore / remove call path).
- [x] 9.4 Update/remove obsolete Excel enable + Excel freshness tests; wiring assert no mode apply via Excel.
- [x] 9.5 Docstrings + focused pytest; сверка placement с decision §9 / spec «Excel MUST NOT expose or apply».

## 10. Honest UX: freeze no-op on «Обновить минус-слова» (clarify)

- [x] 10.1 Tests-first: ACTIVE/PENDING + ordinary update → no set_minus + non-success freeze message; OFF → success path.
- [x] 10.2 `update_minus_phrases` returns skip/status; `wb_update_minus_keywords` uses it for Telegram copy.
- [x] 10.3 Focused pytest; сверка со scenario Manual bot minus update.

## 11. Telegram Enable idempotent while PENDING/ACTIVE (update — decision §10)

- [x] 11.1 Tests-first: ACTIVE + Enable → mode stays ACTIVE, no Redis ENTER; PENDING + Enable → mode stays PENDING; OFF + Enable → PENDING + ENTER (paired).
- [x] 11.2 `enable_card_ab_hold` / `ui_access`: no-op when mode ∈ {PENDING_SETUP, ACTIVE}; no demote, no ENTER rewrite.
- [x] 11.3 Focused pytest; сверка со spec «Telegram Enable is idempotent» / decision §10.

## 12. Telegram keyboard MAY hide Enable while PENDING/ACTIVE (update — decision §11)

- [x] 12.1 Tests-first: OPEN screen / `_screen_keyboard` — OFF → Enable+Disable+Back; PENDING/ACTIVE → Disable+Back, Enable absent (or documented optional show + handler no-op still covered by §10).
- [x] 12.2 Mode-aware keyboard builder: omit Enable when mode ∈ {PENDING_SETUP, ACTIVE}; always include Disable+Back; OFF keeps Enable.
- [x] 12.3 Focused pytest; сверка со spec screen controls + decision §11; §10 handler tests remain green.

## 13. Launch validity soft-gate: low 24h views warning (update — decision §2c)

> Новый enable-поток: попытка запуска → оценка объёма показов ключей-кандидатов за 24ч → при проблеме → информация + рекомендация (поднять max CPO) + выбор «всё равно запустить / отмена». Soft-gate (не hard block), distinct от §2a freshness и §8 empty allowed-set. Пороговая константа `AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000`.

- [x] 13.1 Tests-first (integration, real/test CH): агрегат суммарных показов ключей-кандидатов за последние 24ч через реюз `full_wb_adv_stat.get_keywords_views_by_days` (MV `default_db.mv_clusters_daily_agg`); граничные значения вокруг порога 1000 (ниже / равно / выше).
- [x] 13.2 Tests-first: enable при `Σ 24h views < порога` → mode остаётся `OFF`; сообщение содержит причину (мало показов), рекомендацию поднять план max CPO и повторить, и inline-выбор «Всё равно запустить» / «Отмена». Paired: `Σ ≥ порога` → enable без предупреждения (обычный путь §7).
- [x] 13.3 Tests-first: «Всё равно запустить» (confirm-callback) → `PENDING_SETUP` + Redis ENTER; «Отмена» → остаётся `OFF`, ENTER не пишется.
- [x] 13.4 Telegram payload-limit тесты (`openspec/policies/telegram_bot_api_limits.md`): worst-case текст предупреждения + `callback_data` кнопок confirm/cancel в пределах Bot API байт-лимитов.
- [x] 13.5 Реализация: read-only CH-агрегат показов за 24ч (реюз `full_wb_adv_stat`); чистая пороговая функция + константа `AB_HOLD_MIN_TOTAL_VIEWS_24H = 1000`; wiring в `enable_card_ab_hold` (soft-gate после §2a freshness, до записи PENDING/ENTER); copy рекомендации (поднять max CPO); confirm-callback «launch anyway». Кандидаты — тот же набор ключей, что setup (non-BAD / would-carry-test).
- [x] 13.6 RU-docstrings со ссылкой на spec (requirement «Enable warns when candidate test keywords have too few recent impressions») и decision §2c; прогон integration + focused unit; `pyright-strict` на затронутых путях.

## 14. A/B Hold — только V3 + взаимоисключение с V2 (update — decision §12)

> A/B Hold — V3-only фича. Enable блокируется на не-V3 РК; пока PENDING/ACTIVE запрещён downgrade на V2. Авто-переключатель стратегии РК (`change_adv_strategy`, MIN_CPO/MAX_CONV) — V2-scope и вне A/B Hold freeze (отдельный гард НЕ добавляем). Развязка V3 keyword `strategy_mode` от `AdvSetting.strategy` — отдельная задача вне этого change.

- [x] 14.1 Tests-first: `enable_card_ab_hold` при `automatic_version != 3` → mode остаётся `OFF`, Redis ENTER не пишется, сообщение «A/B Hold требует V3»; paired positive: V3 + gates pass → `PENDING_SETUP`.
- [x] 14.2 Tests-first: `toggle_auto_updater_version(new_version=2)` при `card_ab_hold_mode ∈ {PENDING_SETUP, ACTIVE}` → `automatic_version` не меняется + подсказка «отключите A/B Hold»; paired positive: `OFF` → downgrade применяется.
- [x] 14.3 Реализация V3-gate: `can_enable_card_ab_hold` / `enable_card_ab_hold` проверяют `automatic_version == 3` (рядом с paid + freshness gates), reason-alert; UI-видимость экрана не ломать.
- [x] 14.4 Реализация downgrade-block: `toggle_auto_updater_version` блокирует `new_version == 2` при активном режиме (читает `card_ab_hold_mode`), сообщение пользователю.
- [x] 14.5 Tests-first (регресс исходного finding): в `ACTIVE`/`PENDING_SETUP` (V3) авто-смена `AdvSetting.strategy` НЕ меняет held keyword bidding profile; A/B Hold НЕ добавляет freeze-гард в `change_adv_strategy` (strategy остаётся V2-scope). Примечание: полная гарантия зависит от отдельной развязки `strategy_mode` (вне change).
- [x] 14.6 RU-docstrings со ссылкой на spec requirement «A/B Hold requires the V3 auto-updater and is mutually exclusive with V2» + decision §12; focused pytest (`tests/unit/auto_updater_v3/`, client_bot version-toggle) + `pyright-strict` на затронутых путях.

## 15. Shared defaults MUST NOT disable/mutate A/B Hold on held campaign (update — decision §13)

> «Применить дефолты» (single + shop-wide) и shared `apply_defaults_to_adv_setting` — не enable/disable path A/B Hold. Held (PENDING_SETUP/ACTIVE) кампания: mode / allowed-set snapshot / coupled structural fields этим путём не трогаются; disable — только owned Telegram EXIT.

- [x] 15.1 Tests-first (fail before fix): `apply_defaults_to_adv_setting` на held-кампании (ACTIVE и PENDING_SETUP) НЕ ставит `card_ab_hold_mode=off`, НЕ оставляет непустой allowed-set snapshot, НЕ сбивает `automatic_version` на не-V3; paired positive: `OFF` кампания получает полный набор дефолтов (write-boundary assert на значении полей). — `tests/unit/client_bot/test_apply_defaults_ab_hold_guard.py`.
- [x] 15.2 Tests-first (handler-level): `apply_campaign_defaults` / `apply_defaults_for_shop` на held-кампании не выполняют un-owned disable; shop-wide — held пропущены/сохранены, не-held получают дефолты.
- [x] 15.3 Реализация: guard в `apply_defaults_to_adv_setting` — при `is_ab_hold_structural_freeze(card_ab_hold_mode)` не мутировать A/B-Hold-owned/coupled поля; UX в handlers (single → сообщение «выключите A/B Hold на экране режима»; shop-wide → пропуск held + честный counter). Не дублировать owned EXIT-контракт вне A/B Hold модуля. Inline-import `mode` в `default_settings/__init__.py` (документированное исключение no-inline-imports из‑за раннего import-time цикла).
- [x] 15.4 RU-docstrings со ссылкой на spec requirement «Shared defaults MUST NOT disable or mutate A/B Hold on a held campaign» + decision §13; focused pytest (6 passed) + `pyright-strict` (exit 0) на затронутых путях.

## 16. PENDING_SETUP liveness: max-CPO enable gate + actionable status + EXIT recovery (update — decision §14)

> PENDING_SETUP исключает кампанию из ordinary automation; детерминированный блок setup MUST NOT оставлять молчаливый вечный semi-frozen state. §14a hard-gate `max_price_for_order > 0` на enable; §14b actionable non-ready причина; §14c MVP recovery = actionable reason + always-available EXIT (owned auto-abort = SHOULD/future, вне MVP; без новой миграции).

- [x] 16.1 Tests-first: `enable_card_ab_hold` при `max_price_for_order` missing / ≤ 0 → mode остаётся `OFF`, Redis ENTER не пишется, сообщение «нужен положительный план max CPO»; paired positive: `> 0` (+ прочие gates) → `PENDING_SETUP`. Gate проверяется вместе с §2a freshness / §12 V3-gate, до §2c soft-gate.
- [x] 16.2 Реализация hard-gate: чистый предикат `has_positive_plan_max_cpo(adv_setting)` (или эквивалент в `ui_access`) + wiring в `_handle_ab_hold_enable` рядом с §2a freshness / §12 V3-gate, до launch-validity §2c; reason/alert copy (задать план max CPO и повторить). Owner — bot enable write-path (не transition-helper, не defaults).
- [x] 16.3 Tests-first: `build_enter_poll_status_lines` / статус PENDING при детерминированном блоке (пустой allowed-set / max CPO пропал после enable) → конкретная причина + действие; транзиентная причина → generic «Подготовка…» допустим; ready — только ACTIVE (не ломать §8/4b readiness).
- [x] 16.4 Реализация actionable статуса: setup-путь помечает детерминированную причину блока через reuse `CardAbHoldLastAbort`-подобного Redis-признака (writer = shop-runner setup, reader = UI poll) — **без новой миграции**; `enter_status` / status label отражают причину; generic — только для транзиентных.
- [x] 16.5 Tests-first: EXIT при зависшем PENDING_SETUP → `OFF` + ordinary automation снова eligible (paired с существующими EXIT-тестами); подтвердить, что MVP не вводит авто-abort (owned auto-abort = future, без `pending_since` миграции).
- [x] 16.6 RU-docstrings со ссылкой на spec requirements («Enable is blocked when plan max CPO is missing or non-positive», «PENDING_SETUP setup blockers are surfaced and recoverable») + decision §14; focused pytest (`tests/unit/auto_updater_v3/card_ab_hold/`, client_bot enable) + `pyright-strict` на затронутых путях.
