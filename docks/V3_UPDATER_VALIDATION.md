# V3 updater: наблюдаемость и контролируемая валидация

## Structured logs

Строки `v3_selection` в orchestrator: `pool`, `pool_after_rec`, `tier`, `state_cost`, переход `from_mode->to_mode`, `move`, `imputed`.

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

Проверка: unit `test_select_overspend_force_off_all_keys_above_max`, shelf `test_select_overspend_shelf_force_off_above_max`.

## CI

```powershell
poetry run pytest -m unit tests\unit\auto_updater_v3\ tests\unit\test_auto_updater_v3.py tests\unit\test_auto_updater_v3_applier.py tests\unit\test_process_adv_v3_plan_fact_cache.py tests\unit\test_v3_ui_sort.py -q
poetry run pytest -m integration tests\integration\test_v3_up_selection_integration.py tests\integration\test_v3_target_place_strategy_order_integration.py -q
```
