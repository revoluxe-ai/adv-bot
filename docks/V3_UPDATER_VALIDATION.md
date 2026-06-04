# V3 updater: наблюдаемость и контролируемая валидация

## Campaign mode vs keyword data tier (V3)

Два независимых уровня решений:

### Campaign-level (`CampaignMode`, `v3_campaign_mode.py`)

| Режим | Условие | Поведение |
|-------|---------|-----------|
| **NOT_READY** | `detect_campaign_state(...) is None` | full stop — без bootstrap, sync, cache |
| **NO_DATA** | `SalesStates.NO_DATA` (`fact.pay_for_order is None`) | только `plan_campaign_no_data_bootstrap_safe` → flush → sync с `force_all_target_place_zero=True` (управляемые ключи) |
| **NORMAL** | OVERSPEND / UNDERPERFORM / STABLE / OPTIMAL | полный preamble + post-gate (без gate) + snapshots |

При **NO_DATA** запрещены: COST_REALLOCATION, selector ladder, plan/fact/views snapshots (кроме bootstrap path).

### Keyword-level (`KeywordDataTier`, `keyword_v3_eligibility.py`)

| Tier | UP/realloc targets | Cost |
|------|-------------------|------|
| **KEYWORD_FULL** | MIN, OPT, MAX | CH profile CPO |
| **KEYWORD_PFO** | только MIN | `keyword.pay_for_order` |
| **KEYWORD_NO_DATA** | ∅ (enable → MIN отдельной фазой) | нет |

Legacy aliases: `KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV` → PFO, `KEYWORD_INVALID` → NO DATA.

`OFF` **не** target mode: `can_target_mode(_, OFF) == False`.

## Порядок тика (`process_adv_v3`)

```
load CH profiles → plan/fact → resolve_campaign_mode

NOT_READY → full stop (no bootstrap, flush, sync)
NO_DATA   → safe bootstrap → flush → target_place (force 0, managed only)
NORMAL    → filter operable → V → NF → NF_migrate → NF_overspend_tp → NF_plan_fact → skip_up → raise → reset → S → R → enable → calibration(DOWN|UP)
            → post-gate (noop) → snapshots plan/fact + views → flush → target_place
```

### Cap-down (legacy B) — намеренно удалён

До рефакторинга V3 была фаза **B** (`CapDownExecutor`, `plan_mode_cap_down`): опускать
``strategy_mode`` выше ``max_allowed_mode`` по ``KeywordDataTier``.

**Сейчас отдельной фазы нет — это не баг.**

| Ситуация | Кто обрабатывает |
|----------|------------------|
| Нет CH-профиля (`position_profile` пуст), PFO или GAP | **NF** — active → ``MIN_CPA``; tp: migrate ``0→round(pos)−1``, plan-fact ±1 (gate fact+views) |
| Есть CH-профиль | Лестница M/O/C и CPO из профиля (**FULL**); режим берётся из профиля, cap по tier не режет |
| UP/realloc/calibration | ``can_target_mode(eligibility, mode)`` — tier без профиля не даёт OPT/MAX |

**Не восстанавливать** ``CapDownExecutor`` без изменения продуктового контракта «есть профиль →
работаем из профиля». Статика: ``tests/unit/auto_updater_v3/test_orchestrator_campaign_mode_layout.py``
(``test_no_legacy_cap_down_executor_in_preamble``).

Каждая фаза NORMAL in-place: `UpdatePipelineManager.run_preamble` → `NextState` на `KeywordDTO`.

Фазы NORMAL (только `allows_ladder_phases`, in-place executors):

1. **V** (`HardStatusValidateExecutor`) — авто hard_status=1 → OFF.
2. **NF** (`NotFullValidateExecutor`) — NOT FULL active → MIN (tp не сбрасывается в 0); **до migrate**, иначе migrate не видит MIN_CPA.
3. **NF_migrate** (`NotFullTargetPlaceMigrateExecutor`) — NOT FULL MIN + tp=0 → ``round(position)−1``; skip при overspend.
4. **NF_overspend_tp** (`NotFullTargetPlaceOverspendResetExecutor`) — при ``fact CPO РК > MAX``: NOT FULL MIN → tp=0; sync fallback force 0.
5. **NF_plan_fact** (`NotFullTargetPlacePlanFactExecutor`) — tp ±1 по fact vs 0.9×resolve; gate: plan/fact и views; skip при overspend.
6. **skip_up** (`SkipUpTargetPlaceExecutor`) — alias UP на том же target_place (NOT FULL пропуск).
7. **raise** (`RaiseStateToTargetCpoExecutor`) — UP до resolve по ladder CPO (NOT FULL пропуск).
8. **reset** (`ResetOverMaxCpoOnOverspendExecutor`) — сброс ключей с CPO > max при overspend (лестница).
9. **S** (`ShelfCleanupExecutor`) — shelf active + rec FAIL: **while** на ключе — effective DOWN / OFF до PASS или OFF (счётчик ladder-шагов); затем **столько же** UP-итераций min CPO из list2 (`run_potential_up_steps`), пересборка списков каждый шаг.
10. **R** (`RebalanceExecutor`) — симметричный DOWN max-CPO + UP min-CPO (до 50 циклов).
11. **enable** (`PayForOrderGapEnableExecutor`) — один GAP OFF→MIN за тик; skip: no fact, fact>max, fact≥ratio×plan.max (env ``V3_PAY_FOR_ORDER_GAP_ENABLE_PLAN_HEADROOM_RATIO``, default 1).
12. **pfo_off** (`PayForOrderOverMaxOffOnDeepOverspendExecutor`) — OFF ключей с PFO>max при fact≥ratio×plan.max (env ``V3_PAY_FOR_ORDER_OFF_PLAN_HEADROOM_RATIO``, default 1).
13. **calibration** (`ResolveCalibrationExecutor`) — CAL UP/DOWN через `run_calibration_*`; gate plan/fact AND views.
14. **Post-gate** — `select_v3_post_gate_actions` → DO_NOTHING (shelf в preamble S).
15. **Snapshots** — `ChangePlanFact` + `ChangePlanFactViews`.

Prod-хелперы (бывший `rollout_planner.py`): `resolve_threshold.py`, `ladder_tick_helpers.py`.

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

**orders_per_cart для CPO:** effective rate только через ``LadderInputs.orders_per_cart_for_ctx(ctx)``
(сглаживание ``smooth_key_orders_per_cart``: prior ``V3_KEY_CART_TO_ORDER_PRIOR_CARTS``, baseline
``campaign_orders_per_cart_7d`` из ``wb_common_stat`` 7d, key ``orders``/``add_to_cart`` 7d из cluster stats).
Исключения: UI-строка «РК 7д»; ``target_place_sync`` без ``CalculatedKeyword`` → campaign fallback;
``KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV`` → ``pay_for_order``, не CH×orders_per_cart.

UI (Telegram) и updater (COST_REALLOCATION / RESOLVE_CALIBRATION / PROFITABLE_EXPANSION / MAX_CPA_GUARD) используют **одну** модель:

| Модуль | Роль |
|--------|------|
| `keyword_v3_contexts.py` | `build_keyword_v3_contexts`, `load_campaign_v3_contexts` |
| `keyword_v3_ladder_view.py` | `LadderInputs`, `cost_for_mode`, `resolve_ladder_stage_display` |
| `resolve_threshold.py` | `compute_resolve_cost_threshold`, `is_resolve_valid` |
| `ladder_tick_helpers.py` | tick-report / gap enable helpers (`mode_catalog_for_ctx`, …) |
| `effective_ladder_steps.py` | collapsed UP/DOWN, alias groups; SSOT ``LadderStepSnapshot`` / ``classify_ladder_step`` (1 шаг = смена ``target_place`` или OFF; alias на том же place = 0) |
| `update_pipeline/executors/` | in-place preamble executors + `NextStateManager` |

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

- **Usable-точки:** env `INCLUDE_SYNTHETIC_POSITION_PROFILE` (default **true**) — в M/O/C входят синтетические позиции `_fill_positions` (`ch_observed=False`); при `false` только реальные buckets `bid_decision_log`. Откат без деплоя: переменная в config updater. Риск при true: prior-conv на верхних `pos_bin` до накопления факта.
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

На каждом тике **NORMAL**:

1. **DATA_BOOTSTRAP** — tier-aware MIN/выравнивание.
2. **ACTIVE_INVALID_CLEANUP** — invalid/worst-only active state → DOWN или FORCE_OFF.
3. **COST_REALLOCATION** — DOWN-only rebalance (headroom); gate `fact < 0.9×resolve`.
4. **RESOLVE_CALIBRATION** — **CAL DOWN** (max `state_cost` → один DOWN, до `max_effective_steps`) или **CAL UP** (min `state_cost` → один UP) при `fact ≤ max` **и**
   `not plan_fact_equal` **и** `not views_equal` (AND-gate). Направление: `fact < 0.9×resolve` → UP, иначе DOWN.
   Guard / realloc / expansion — full-trim без лимита.
5. **PROFITABLE_EXPANSION** — mass cheap UP (M1 successor).
6. **MAX_CPA_GUARD** — trim если `fact.pay_for_order > plan.max_pay_for_order`.
7. **Post-gate selector** — shelf cleanup (`select_v3_post_gate_actions`); **каждый** NORMAL-тик, без plan/fact gate.
8. **Snapshots (конец тика)** — `ChangePlanFact` + `ChangePlanFactViews` (sum views `all_adv_ids`).

### Gates calibration vs post-gate

| Сигнал | Источник | Equal = skip calibration |
|--------|----------|--------------------------|
| plan/fact | `ChangePlanFact`: plan + `fact.original_orders` + `fact.pay_for_order` | да |
| views | `ChangePlanFactViews`: SUM views по `complex_adv.all_adv_ids`, `full_adv_wb_stat`, окно `max_last_period` (как fact V3) | да |

Calibration: **AND** — оба сигнала должны измениться + `fact ≤ max` (без нижней границы 0.9×resolve). Ошибка CH при resolve views → fail-closed (`views_equal=True`, calibration/enable не запускаются); **plan/fact и views snapshots в Redis не пишутся**, пока views снова не прочитаются (нет рассинхрона «кэш plan обновился, а gate views думает что unchanged»).

### Adaptive calibration steps (Redis `V3CalibrationStepState`)

Направление по зоне fact vs resolve (одна ветка калибровки за тик):
- **CAL DOWN** — `fact >= 0.9×resolve`; итерации max `state_cost` → один DOWN; adaptive steps.
- **ветка UP** — `fact < 0.9×resolve`; до `effective_steps` итераций «самый дешёвый следующий state → один UP» (adaptive ×2/÷2, cap `keyword_calibration_max_step`).

В Redis/UI legacy-строки `tighten` / `loosen` (`CalibrationDirect`) соответствуют веткам DOWN/UP.

#### Калибровка UP и ключи OFF (контракт)

| Категория | Enable (6) | Calibration UP (7) |
|-----------|------------|---------------------|
| OFF + NO DATA | да, ≤1/тик, OR gate plan/views, без rec-gate | да, min CPO из пула, AND gate, с rec-gate; ослаблены `participates_in_ladder` / `can_target_mode`; при `cost=inf` — imputed из каталога |
| OFF + FULL/PFO | нет | да, полный ladder UP (rec-gate, cost, eligibility) — единственный preamble-путь «включить» OFF с данными на ключе |

- Снят исторический skip «все OFF» в `collect_calibration_up_next_step_candidates`: иначе при массе OFF NO DATA ветка UP давала пустой пул при `fact << resolve`.
- Enable и calibration UP **не дублируют** друг друга: разные gate (OR vs AND), лимит отбора (ks_id vs min CPO), reason (`pay_for_order_gap_enable` vs `resolve_calibration_up`).
- Порядок в тике: enable → refresh `prepared` → calibration; за тик возможны два разных OFF NO DATA, если оба gate прошли.

**OFF collapse и calibration UP (ограничение):** `resolve_next_effective_step_up(OFF)` схлопляет M/O/C на первом `target_place` до max режима (не обязательно MIN). В `collect_calibration_up_next_step_candidates` ослабление `can_target_mode` (`off_no_data_bootstrap`) действует **только** при `to_mode == MIN_CPA` (OFF + NO DATA). Если collapsed target — OPT/MAX, а tier MIN-only или bootstrap не применим, ключ **не попадает в пул** (fallback на MIN нет). Enable (`plan_pay_for_order_gap_enable`) всегда OFF→MIN и не зависит от collapse. См. `effective_ladder_steps.py` module docstring.

Effective steps за NORMAL-тик (cap = `keyword_calibration_max_step`, default 1):
- первый тик / нет Redis-истории → `1`;
- то же направление → `min(prev × 2, cap)`;
- смена направления → `max(prev ÷ 2, 1)`.

Снимок в Redis — **только если calibration выполнилась** (gate plan/views + `fact ≤ max`, без guard): в конце NORMAL-тика вместе с plan/fact/views. Пропуск calibration **не** обновляет `V3CalibrationStepState` (иначе ×2/÷2 без фактического прогона).

**UI:** кнопка `V3 cal. шаг: {N}` в меню РК (только `automatic_version == 3`, рядом с переключателем версии); FSM-ввод 1..50, как `bidder_step`.

Realloc / expansion / guard — **без** plan/fact/views gate.

Post-gate selector: **без** gate (раньше пропускался при unchanged plan/fact, кроме OVERSPEND — исключение снято).

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

## UI: отчёт «Последние действия с ключами» (V3)

Кнопка в меню РК (только `automatic_version == 3`): отдельное сообщение с отчётом стадий последнего тика.

- **Redis:** `V3TickReport:{adv_id}`, TTL 7 суток; запись в `finally` каждого тика с preamble (NORMAL / NO_DATA), **не** перезаписывается при `NOT_READY`.
- **Счётчики фаз** (post-hoc из `KeywordDTO.next_state`, модуль `v3_keyword_changes_report`): **`↑N on:L ↓M off:K`** — UP-шаги; ключи OFF→active по итогам фазы (`on`); DOWN+OFF-шаги лестницы в `↓`; ключи, окончившие фазу в OFF (`off`). Net-итог тика: **`+↑ on: −↓ off:`** (stored→current). `aggression_after` — из audit.
- **Redis audit:** `V3KeywordChanges:{adv_id}`, TTL 7 суток — полный per-keyword audit (цепочки режимов, executor); UI читает merged `V3TickReport`.
- **Стадии NORMAL:** filter → V → NF → skip_up → raise → reset → S → R → enable → calibration (post-gate в отчёт **не** входит — shelf в S, selector = DO_NOTHING). Legacy фаза **B (cap_down)** удалена — см. § Cap-down выше.
- **Стадии NO_DATA:** filter → sync → DATA_BOOTSTRAP.
- **Итог:** Δ агрессии РК (MIN=1, OPT=2, MAX=3, OFF=0), net `+↑ on: −↓ off:` (UP / OFF→active / DOWN без OFF / OFF net), распределение hard_status, время тика (MSK).
- **Кнопки:** «Обновить» (перечитать Redis), «Назад к меню РК».
- **Формат стадии:** без строки «Возможные:». **Пропуск** (`executed=False`, `skip_reason`) — `пропуск — …`. **Нулевой исход** (`executed=True`, действий 0) — `без изменений — …` из `outcome_note`. При ненулевом плане — **`↑ on: ↓ off:`** (все четыре поля, нули явно). Метаданные фаз (skip, outcome_note, filter, calibration extra) — из `V3TickReportCollector`; NO_DATA audit — из `ledger.applied_actions()`.
- **Шапка:** adaptive calibration (`calibration_effective_steps`, `calibration_direct`, `calibration_prev_effective_steps` из Redis resolver); **БС max** — самый дорогой ключ `hard_status=2` по decision CPO (FULL → state, PFO → `pay_for_order`), с обоими CPO если доступны.

## UI: порядок ключей в списке (V3)

Для `automatic_version == 3` список ключей в Telegram сортируется **до** пагинации
(`AdvKeywordsSetting` → `sort_keywords_for_v3_ui`, SSOT `sort_utils.sort_keywords_by_current_state_cost`):

1. По возрастанию **своего** `state_cost` из CH-профиля для **текущего** `strategy_mode` (`state_candidates_by_mode_for_ctx`); для `OFF` — ступень `MIN_CPA`.
2. Нет валидной точки / проблемы со стейтами (NO CH, collapsed ladder, нет матрицы) — **NO DATA для сортировки**: `keyword.pay_for_order` (как в operational tier). **Worst-импутация по РК не используется.**
3. Ключи без метрики и без `pay_for_order` — в конец, по алфавиту `keyword.text` (case-insensitive); tie-break при равной метрике — тоже по `text`.

При сбое CH/min_bids — fallback: сортировка по `pay_for_order` asc (как раньше). `LadderInputs` для eligibility строятся по **всей** РК; Redis `v3_worst_costs` из списка ключей **не читается и не пишется**. V2 (`automatic_version` 2) — прежние `sort_mode` (`by_adv`, `white_list`, …).

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
- Cache miss min_bids в логах — **WARNING** (`min_bids cache miss`), не ERROR; догрузка — `preload_min_bids_cache_miss`.
- Нет CH / min_bid в кеше — «недоступен» (техн.); нет строки ключа в CH при загруженном профиле nmid — **N-state** (нет матрицы CH).

Unit: `tests\unit\client_bot\test_keyword_v3_profile_ui.py`, `tests\unit\client_bot\test_keyword_v3_profile_loader.py`.

## CI

```powershell
poetry run pytest -m unit tests\unit\auto_updater_v3\ tests\unit\test_auto_updater_v3.py tests\unit\test_auto_updater_v3_applier.py tests\unit\test_process_adv_v3_plan_fact_cache.py tests\unit\test_keyword_target_place_updater_v3.py tests\unit\test_v3_ui_sort.py -q
poetry run pytest -m integration tests\integration\test_v3_up_selection_integration.py tests\integration\test_v3_target_place_strategy_order_integration.py -q
```
