# V3 updater: наблюдаемость и контролируемая валидация

## Structured logs

Строки `v3_selection` в orchestrator: `pool`, `tier` (`confirmed` / `missing_above_rec`), `state_cost`, переход `from_mode->to_mode`, `move`, `imputed` (worst-per-state при `missing_target_matrix`).

Сигналы:
- **missing_target_matrix** — нет валидных M/O/C в профиле; `state_cost` из worst-per-state доноров.
- **missing_above_rec** — `above_rec_conversion is None`; на полке provisional UP, tier ниже `confirmed`.

Контракт `state_cost`:
- источник `state_cost` — только профильные ставки мест из CH (target M/O/C) + `conv_views_to_orders`;
- fallback на `keyword.pay_for_order` (текущий CPM ключа) **не используется**;
- если профильный расчёт недоступен и imputation невозможен — `state_cost = inf`, переход не планируется.

## Unified pooled contract

Для `UNDERPERFORM` в shelf и non-shelf используется один и тот же pooled-процесс:
- для каждого ключа берем все состояния строго выше текущего;
- считаем `state_cost` для каждого допустимого target;
- фильтруем target по `aggressiveness`:
  - `1` -> только `MIN`,
  - `2` -> `MIN/OPT`,
  - `3` -> `MIN/OPT/C`;
- выбираем один самый дешевый кандидат из общего пула.

Rec-gate:
- при `organic > shelf` — не применяется;
- при `shelf >= organic` и `UNKNOWN` — отсекает только `above_rec=False`.

Алерт: рост доли `reason=no_valid_up_after_rec_filter`.

## Shadow на 1–2 РК

Сравнить за 7 дней: jump vs M→O, средний `state_cost`, `pay_for_order`, доля shelf/organic.

## Gap-rebalance (phase 0 в `process_adv_v3`)

Перед plan/fact и `select_v3_actions`, **всегда** (даже если plan/fact в cache не менялся):

1. БС (`hard_status == 2`), сортировка `pay_for_order` asc (MIN_CPO).
2. Первая «дыра»: `OFF` с активными ключами ниже по списку.
3. Хвост (строго ниже якоря OFF) → `FORCE_OFF`, сумма `mode_level` = N.
4. N× UP по ветке shelf/non-shelf (`plan_cost_first_up_one`).

V3 **не** обслуживается в `white_list_tail_trimmer` (только v2 trim). Не зависит от `white_list_mode`.

Логи: `v3 gap rebalance: force_off=… up=…`, при обрыве UP — `v3_gap_rebalance: UP stopped early`.

Unit: `tests\unit\auto_updater_v3\test_ladder_gap_rebalance.py`.

## OVERSPEND: массовый OFF по max себесу

При `SalesStates.OVERSPEND` (факт кампании `> plan.max_pay_for_order`) за один цикл:

- все активные ключи (не OFF) с известным `pay_for_order > max` → `FORCE_OFF` (сразу OFF, без пошагового DOWN);
- ключи с `pay_for_order is None` не трогаются;
- если ни один ключ не выше max — один обычный DOWN (как раньше).

Проверка: unit `test_select_overspend_force_off_all_keys_above_max`,
`test_select_overspend_force_off_with_plan_and_fact`, shelf `test_select_overspend_shelf_force_off_above_max`.

При неизменном plan/fact в Redis цикл обычно пропускается, **кроме OVERSPEND** — пока факт
кампании `> max`, селектор и apply выполняются каждый тик (`test_process_adv_v3_runs_selector_when_plan_fact_equal_overspend`).

## UI: последнее V3-действие в блоке «Обновл:»

Для `automatic_version == 3` в меню РК вместо строк «добавл/удал из БС» (legacy V2 Redis) показывается:

`посл. V3: <ACTION> «<ключ>» <FROM>→<TO> <HH:MM:SS dd-mm-yyyy>`

- **Redis:** ключ `LastV3UpdaterAction:{adv_id}`, JSON-снимок, TTL 7 суток.
- **Запись:** после успешного `apply_v3_actions` (последнее применённое действие цикла; при пакете однотипных действий — суффикс `(+N ещё)`).
- **Время в UI:** московское (MSK, UTC+3); в Redis — `updated_at` в UTC ISO.
- **Нет снимка:** «Нет данных» (цикл без изменений в БД или ещё не было apply).

Строки «цел.поз +/-» и «топ в БС» для V3 без изменений.

## Новый state-first контракт (M1/M2/M3)

В V3 решения принимаются по `state_cost` — прогноз **себестоимости заказа** для режима
(как `CalculatedKeyword.pay_for_order` в V2: `calc_pay_for_order(calc_orders_per_1000_rub(conv, CPM))`
по точке профиля M/O/C), относительно `resolve_cost_threshold`:

- `resolve = target_pay_for_order`, если `fact.predict_orders >= plan.orders`;
- иначе `resolve = max_pay_for_order`.

Три механизма запускаются на каждом тике:

1. `M1 (mass_cheap_promotion)` — для каждого ключа UP до наивысшего состояния с
   `state_cost <= resolve` (только UP, без DOWN/OFF).
2. `M2 (state_rebalance)` — работает только со `state_cost > resolve`,
   итеративно выполняет 1:1 `DOWN` худшего активного и `UP` лучшего потенциального
   до устранения разрыва `max(active_B) > min(potential_B)`.
3. `M3 (headroom_plus_one)` — если `fact.pay_for_order < 0.9 * resolve`, выполняет
   один `UP` на самый дешёвый потенциальный state.

**Shelf cleanup (параллельно с M1/M2/M3):** при активной полочной фазе
(`shelf_promotion_active` и `shelf>=organic` или `UNKNOWN`) на том же тике планируется
массовый сброс всех активных ключей с `above_rec=False` (не проходят rec-gate на UP):
БС — один шаг `DOWN`, авто (`hard_status=1`) — `FORCE_OFF` (applier не делает `DOWN`
для авто). Действия cleanup сливаются с M1/M2/M3; при конфликте по `keyword_setting_id`
побеждает cleanup. Legacy shelf-путь (`UNDERPERFORM` без plan/fact) по-прежнему может
отдать только cleanup, если список непустой.

Общие guard-правила:

- `hard_status in {3, 4}` — не изменяем;
- `aggressiveness` ограничивает верхний target mode;
- shelf-gate (при `shelf>=organic`/`UNKNOWN`) фильтрует `above_rec=False` на UP;
- при `resolve <= 0` тик пропускается (`DO_NOTHING + warning`);
- при `detect_campaign_state() is None` тик пропускается (`warning`, без обновления cache plan/fact).

Наблюдаемость:

- в `v3_cycle` логируются `resolve`, `fact_cpa`, counts (`up/down/off`) и breakdown
  по механизмам (`m1/m2/m3`);
- в UI используется агрегат цикла `+up/-down/off` из `LastV3UpdaterAction` snapshot.

## NO_DATA (Н) и ключи без V2 CPO

- **Кампания:** `SalesStates.NO_DATA` — `fact.pay_for_order is None` (`detect_campaign_state`); short-circuit plan/fact **не** режет тик (как `OVERSPEND`).
- **Ключ «нет данных»:** нет V2 CPO — та же цепочка, что рейтинг V2: `conv_views_to_orders` + CPM каскад → `orders_per_1000_rub` → `pay_for_order` (`keyword_v2_pay_for_order_unavailable`). Отсутствие только матрицы CH **не** считается no-data для активации.
- **Ключ с V2 CPO при кампании NO_DATA:** те же M1/M2/M3 (и shelf), что в UNDERPERFORM/STABLE — `split_prepared_by_v2_cpo` + merge с `no_data_min_bid`.
- **Действие:** OFF без CPO → MIN_CPA (`no_data_min_bid`); preamble, phase0, selector, shelf.
- **UI:** `SalesStates` в меню РК (`sales_state_short_label`); в списке ключей `target_place=0` → `->0` (мин. ставка WB), `None` → `->Н>`.
- **`target_place`:** `0` = min bid WB (`NO_DATA_TARGET_PLACE_FALLBACK`); в sync передаётся `calculated_by_text` из orchestrator для проверки V2 CPO.

Unit: `tests\unit\auto_updater_v3\test_no_data_activation.py`, `tests\test_sales_states.py`.

## target_place и ClickHouse bid profiles

- **Один** `get_keyword_bid_profiles` на цикл `process_adv_v3` (`_load_v3_wb_context`); phase 0 и phase 1 переиспользуют тот же snapshot.
- При cache miss `min_bids.search` для `main_nmid`: `backfill_min_bids_for_adv` (как `preload_min_bids_cache_miss` → при необходимости WB API) и повторный `get_wb_advs_dto`; иначе пустые профили без падения цикла.
- **Порядок тика:** CH profiles → **gap-rebalance (phase0)** → plan/fact Redis gate (только selector) → `target_place` один раз после всех смен режимов (`_sync_target_places_once` + dedupe в `finally`).
- **`sync_keyword_target_places_v3`** — при `individual_keywords_target_place_mode`; не режется short-circuit plan/fact; `calculated_by_text` для V2 CPO. Нет CH-профиля или нет V2 CPO → `target_place=0` (активные режимы). `_safe_sync_target_places_v3`: при падении sync — `logger.error`, исключение из `try` не подменяется.

Unit: `tests\unit\auto_updater_v3\test_orchestrator_tick_preamble.py`.
- Обновляются **все** ключи, включая OFF (позиция из профиля как для MIN_CPA; торги OFF по-прежнему отрезаются в `UpdateClusterBidsManager`).
- Корутина **`update_individual_keyword_target_places`** (каждые 5 мин) — **только V2**; V3 — early return в updater.

Unit: `tests\unit\test_keyword_target_place_updater_v3.py`, `tests\unit\auto_updater_v3\test_orchestrator_profiles.py`.

## Telegram: профиль ключа (V3)

- Карточка одного ключа (`KeywordSettingMessage`) при `automatic_version == 3`.
- Блок «Профиль ключа (V3)»: ступени OFF → MIN_CPA → OPTIMUM → MAX_CONVERSION; `🌟` на текущем `strategy_mode`.
- Метрики M/O/C — `build_mode_candidates` (позиция, CPM, CPO, цель по режиму) на том же CH-профиле, что updater (`load_bid_profiles_for_nmid` + `resolve_keyword_bid_profile`).
- Загрузка: `min_bid` из Redis (`get_min_bids_cache_only`), без полного `get_wb_advs_dto` на клик.
- Нет CH / min_bid в кеше — «недоступен», экран ключа не падает.

Unit: `tests\unit\client_bot\test_keyword_v3_profile_ui.py`, `tests\unit\client_bot\test_keyword_v3_profile_loader.py`.

## CI

```powershell
poetry run pytest -m unit tests\unit\auto_updater_v3\ tests\unit\test_auto_updater_v3.py tests\unit\test_auto_updater_v3_applier.py tests\unit\test_process_adv_v3_plan_fact_cache.py tests\unit\test_keyword_target_place_updater_v3.py tests\unit\test_v3_ui_sort.py -q
poetry run pytest -m integration tests\integration\test_v3_up_selection_integration.py tests\integration\test_v3_target_place_strategy_order_integration.py -q
```
