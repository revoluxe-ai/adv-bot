# V3 updater: наблюдаемость и контролируемая валидация

## Campaign mode vs keyword data tier (V3)

Два независимых уровня решений:

### Campaign-level (`CampaignMode`, `v3_campaign_mode.py`)

| Режим | Условие | Поведение |
|-------|---------|-----------|
| **NOT_READY** | `detect_campaign_state(...) is None` | full stop — без bootstrap, sync, cache |
| **NO_DATA** | `SalesStates.NO_DATA` (`fact.pay_for_order is None`) | только `plan_campaign_no_data_bootstrap_safe` → flush → sync с `force_all_target_place_zero=True` (управляемые ключи) |
| **NORMAL** | OVERSPEND / UNDERPERFORM / STABLE / OPTIMAL | полный preamble + gate + shelf cleanup |

При **NO_DATA** запрещены: COST_REALLOCATION, PROFITABLE_EXPANSION, MAX_CPA_GUARD, selector, `ChangePlanFact` gate.

### Keyword-level (`KeywordDataTier`, `keyword_v3_eligibility.py`)

| Tier | UP/realloc targets | Лестница |
|------|-------------------|----------|
| **KEYWORD_FULL** | MIN, OPT, MAX | да |
| **KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV** | только MIN | да (MIN-only), `target_place=0` |
| **KEYWORD_PESSIMISTIC_FALLBACK** | MIN, OPT, MAX | да (imputed conv) |
| **KEYWORD_INVALID** | ∅ | нет |

`OFF` **не** target mode: `can_target_mode(_, OFF) == False`. UP/realloc фильтруют через `can_target_mode` и `max_allowed_mode`.

## Порядок тика (`process_adv_v3`)

```
load CH profiles → plan/fact → resolve_campaign_mode

NOT_READY → full stop (no bootstrap, flush, sync)
NO_DATA   → safe bootstrap → flush → target_place (force 0, managed only)
NORMAL    → DATA_BOOTSTRAP (без NO_CH OFF→MIN) → [resolve valid: realloc + expansion]
            → MAX_CPA_GUARD (если fact > plan.max; вне is_resolve_valid) → plan/fact gate
            → shelf cleanup (post-gate) → flush → target_place
```

Каждая фаза NORMAL: `_apply_v3_phase` → rebuild contexts → пересчёт eligibility.

Фазы NORMAL (только `allows_ladder_phases`):

1. **DATA_BOOTSTRAP** (`plan_data_bootstrap_v3`) — выровнять caps по tier перед ladder.
2. **COST_REALLOCATION** (`plan_cost_reallocation`) — схлопнутое итоговое действие на ключ (WL: DOWN; авто: FORCE_OFF + технический UP).
3. **PROFITABLE_EXPANSION** (`plan_profitable_expansion`) — UP до max passing mode; NO_CH OFF→MIN только при V2 CPO ≤ resolve.
4. **MAX_CPA_GUARD** (`plan_max_cpa_guard`) — trim по `plan.max_pay_for_order` (не зависит от `resolve`; при `resolve=0` всё равно выполняется).
5. **Post-gate selector** — только shelf cleanup (`select_v3_post_gate_actions`); M2/M3/FINAL_TUNING отключены.

## Structured logs

Строки `v3_selection` в orchestrator: `pool`, `tier` (`confirmed` / `missing_above_rec`), `state_cost`, переход `from_mode->to_mode`, `move`, `imputed` (worst-per-state при `missing_target_matrix`).

Сигналы:
- **missing_target_matrix** — нет валидных M/O/C в профиле; `state_cost` из worst-per-state доноров.
- **missing_above_rec** — `above_rec_conversion is None`; на полке provisional UP, tier ниже `confirmed`.

Контракт `state_cost`:
- источник `state_cost` — только профильные ставки мест из CH (target M/O/C) + `conv_views_to_orders`;
- fallback на `keyword.pay_for_order` (текущий CPM ключа) **не используется**;
- если профильный расчёт недоступен и imputation невозможен — `state_cost = inf`, переход не планируется.

## SSOT лестницы M/O/C (`keyword_v3_ladder_view.py`)

UI (Telegram) и updater (COST_REALLOCATION / PROFITABLE_EXPANSION / MAX_CPA_GUARD) используют **одну** модель:

| Модуль | Роль |
|--------|------|
| `keyword_v3_contexts.py` | `build_keyword_v3_contexts`, `load_campaign_v3_contexts` |
| `keyword_v3_ladder_view.py` | `LadderInputs`, `cost_for_mode`, `resolve_ladder_stage_display` |
| `rollout_planner.py` | фазы делегируют в `cost_for_mode` через `ladder_inputs` (отдельный `worst_costs` в API planner **нет**) |

**Производительность:** `LadderInputs.from_contexts(contexts)` один раз на тик (orchestrator после финального `contexts` для realloc/expansion); `cost_for_mode` и `ladder_inputs_for_prepared` не пересчитывают worst вне `LadderInputs`.

**Правило cost (per-mode):**

1. Сначала `eligibility`: tier `KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV` → MIN только `resolve_no_ch_operational_pay_for_order_cost` (`keyword.pay_for_order`, `source=pay_for_order`); O/C → `inf`, **не** `source=worst`.
2. CH-tier: `profile_cost` → `ladder_inputs.worst_costs[mode]` (per-mode, без gate «вся матрица invalid») → `inf`.

**N-state vs MIN-only (диагностика UI):**

- `n_state` ⟺ `NO_CONV` или нет CH без V2 CPO.
- `no_ch_min_only` ⟺ нет CH + есть V2 CPO (не n_state).
- CH + imputed conv (`RK_AGGREGATE` / `PEER_MAX`) — полная лестница, `n_state=False`.

Тесты: `tests/unit/auto_updater_v3/test_keyword_v3_ladder_view.py`.

**Выбор точек M/O/C в `candidates.build_mode_candidates`:**

- **MIN_CPA** — min `predicted_cpa` (CPO заказа, conv ключа V2).
- **MAX_CONVERSION** — max `predicted_conversion` (conv показ→корзина CH).
- **OPTIMUM** — max `0.5*conv_n + 0.5*economy_n` по usable точкам (`v3_optimum_balance.py`); tie — меньший CPO, ставка, позиция. Не середина между позициями M и C, а компромисс на всей матрице.

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

## Preamble (NORMAL) и post-gate selector

На каждом тике **NORMAL**, **до** `check_equal_in_cache`:

1. **DATA_BOOTSTRAP** — tier-aware MIN/выравнивание.
2. **COST_REALLOCATION** — DOWN-only rebalance (headroom).
3. **PROFITABLE_EXPANSION** — mass cheap UP (M1 successor).
4. **MAX_CPA_GUARD** — trim если `fact.pay_for_order > plan.max_pay_for_order`.

Selector после gate: **только shelf cleanup** (rec-false DOWN / FORCE_OFF), без M2/M3/FINAL_TUNING.

При `SalesStates.OVERSPEND` селектор по-прежнему **не** режется cache gate
(`test_process_adv_v3_runs_selector_when_plan_fact_equal_overspend`).

Legacy ``select_v3_actions`` с ``plan``/``fact`` → ``_select_v3_actions_with_plan_fact``
(post-gate only; ``plan_max_pay_for_order`` игнорируется). OVERSPEND trim — в preamble
(``plan_max_cpa_guard``). Без plan/fact: ``plan_overspend_actions`` по ``plan_max_pay_for_order``.

## UI: последнее V3-действие в блоке «Обновл:»

Для `automatic_version == 3` в меню РК вместо строк «добавл/удал из БС» (legacy V2 Redis) показывается:

`посл. V3: <ACTION> «<ключ>» <FROM>→<TO> <HH:MM:SS dd-mm-yyyy>`

- **Redis:** ключ `LastV3UpdaterAction:{adv_id}`, JSON-снимок, TTL 7 суток.
- **Запись:** после успешного `apply_v3_actions` (последнее применённое действие цикла; при пакете однотипных действий — суффикс `(+N ещё)`).
- **Время в UI:** московское (MSK, UTC+3); в Redis — `updated_at` в UTC ISO.
- **Нет снимка:** «Нет данных» (цикл без изменений в БД или ещё не было apply).

Строки «цел.поз +/-» и «топ в БС» для V3 без изменений.

## State-first контракт (resolve / state_cost)

В V3 решения принимаются по `state_cost` — прогноз **себестоимости заказа** для режима
(как `CalculatedKeyword.pay_for_order` в V2: `calc_pay_for_order(calc_orders_per_1000_rub(conv, CPM))`
по точке профиля M/O/C), относительно `resolve_cost_threshold`:

- `resolve = target_pay_for_order`, если `fact.predict_orders >= plan.orders`;
- иначе `resolve = max_pay_for_order`.

API ladder-фаз:

- `resolve_effective_state_cost_for_mode` — себестоимость target mode;
- `collect_potential_passing_states` — pooled UP-кандидаты с `state_cost <= resolve`, фильтр eligibility;
- `plan_cost_reallocation` — DOWN-only rebalance;
- `plan_profitable_expansion` — UP до max passing mode;
- `plan_max_cpa_guard` — trim по max CPA.

**Shelf cleanup (post-gate):** при активной полочной фазе
(`shelf_promotion_active` и `shelf>=organic` или `UNKNOWN`) — массовый сброс ключей с `above_rec=False`:
БС — `DOWN`, авто — `FORCE_OFF`.

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

## NO_DATA кампании vs N-state ключа

- **Кампания NO_DATA:** `SalesStates.NO_DATA` — `fact.pay_for_order is None`. V3: safe bootstrap (управляемые → MIN_CPA) → flush → sync `target_place=0`; без realloc/expansion/guard/selector/gate.
- **NOT_READY:** `detect_campaign_state() is None` — полный стоп без bootstrap и sync.
- **N-state ключа** (кампания NORMAL): нет conv даже с импутацией → INVALID; NO_CH + own conv → MIN-only tier (не n_state); NO_CH без conv → INVALID.
- **UI:** «Н» в меню РК — campaign NO_DATA; диагностика ключа — CH/V2 CPO / tier.
- **`target_place`:** `0` = min bid WB; NO_DATA — force 0 (managed); NORMAL NO_CH tier — fallback map by `KeywordSetting.id`.

Unit: `tests\unit\auto_updater_v3\test_no_data_activation.py`, `tests\unit\auto_updater_v3\test_keyword_v3_eligibility.py`, `tests\unit\auto_updater_v3\test_orchestrator_tick_preamble.py`, `tests\unit\auto_updater_v3\test_rollout_phases.py`, `tests\unit\test_process_adv_v3_plan_fact_cache.py`.

## target_place и ClickHouse bid profiles

- **Один** `get_keyword_bid_profiles` на цикл `process_adv_v3` (`_load_v3_wb_context`); phase 0 и phase 1 переиспользуют тот же snapshot.
- При cache miss `min_bids.search` для `main_nmid`: `backfill_min_bids_for_adv` (как `preload_min_bids_cache_miss` → при необходимости WB API) и повторный `get_wb_advs_dto`; иначе пустые профили без падения цикла.
- **Порядок тика:** CH profiles → plan/fact → `CampaignMode` → фазы по режиму → flush → `target_place`.
- **`sync_keyword_target_places_v3`** — `force_all_target_place_zero` (NO_DATA, managed keys); `target_place_fallback_zero_by_keyword_id` (NORMAL, by `KeywordSetting.id`).

Unit: `tests\unit\auto_updater_v3\test_orchestrator_tick_preamble.py`.
- Обновляются **все** ключи, включая OFF (позиция из профиля как для MIN_CPA; торги OFF по-прежнему отрезаются в `UpdateClusterBidsManager`).
- Корутина **`update_individual_keyword_target_places`** (каждые 5 мин) — **только V2**; V3 — early return в updater.

Unit: `tests\unit\test_keyword_target_place_updater_v3.py`, `tests\unit\auto_updater_v3\test_orchestrator_profiles.py`.

## Telegram: профиль ключа (V3)

- Карточка одного ключа (`KeywordSettingMessage`) при `automatic_version == 3`.
- Блок «Профиль ключа (V3)»: ступени OFF → MIN_CPA → OPTIMUM → MAX_CONVERSION; `🌟` на текущем `strategy_mode`.
- Метрики M/O/C — `build_mode_candidates` (позиция, CPM, CPO, цель по режиму) на том же CH-профиле, что updater (`load_bid_profiles_for_nmid` + `resolve_keyword_bid_profile`).
- Загрузка: `min_bid` из Redis (`get_min_bids_cache_only`), без полного `get_wb_advs_dto` на клик.
- Нет CH / min_bid в кеше — «недоступен» (техн.); нет строки ключа в CH при загруженном профиле nmid — **N-state** (нет матрицы CH).

Unit: `tests\unit\client_bot\test_keyword_v3_profile_ui.py`, `tests\unit\client_bot\test_keyword_v3_profile_loader.py`.

## CI

```powershell
poetry run pytest -m unit tests\unit\auto_updater_v3\ tests\unit\test_auto_updater_v3.py tests\unit\test_auto_updater_v3_applier.py tests\unit\test_process_adv_v3_plan_fact_cache.py tests\unit\test_keyword_target_place_updater_v3.py tests\unit\test_v3_ui_sort.py -q
poetry run pytest -m integration tests\integration\test_v3_up_selection_integration.py tests\integration\test_v3_target_place_strategy_order_integration.py -q
```
