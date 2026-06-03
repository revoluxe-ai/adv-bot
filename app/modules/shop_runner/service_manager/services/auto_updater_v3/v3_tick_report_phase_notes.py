"""Диагностика нулевого исхода preamble-фаз для отчёта V3-тика (Telegram UI).

Зеркалит условия ``plan_*`` / ``_plan_calibration_*`` без построения действий:
возвращает короткую русскую фразу для ``V3PhaseStats.outcome_note``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    MAX_PAY_STABILIZATION_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    operational_cpo_at_keyword_target_place,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    _HARD_STATUS_AUTO_MODE,
    _HARD_STATUS_WHITE_LIST,
    _eligibility_for_ctx,
    _find_trim_target_mode_limited_steps,
    _hard_status_allows_up,
    _min_cpa_bound_by_pay_for_order,
    _mode_catalog_for_ctx,
    ladder_inputs_for_prepared,
    resolve_effective_state_cost_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_preamble_phases import (
    plan_mode_cap_down,
    plan_passing_up,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )


def summarize_phase_zero_actions(
    phase_id: str,
    *,
    prepared: PreparedList,
    resolve: float | None = None,
    max_pay_for_order: float | None = None,
    fact_pay_for_order: float | None = None,
    plan_fact_changed: bool = True,
    views_changed: bool = True,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
    shelf_click_mode: ShelfClickMode | None = None,
    aggressiveness: V3RolloutAggressiveness | None = None,
    shelf_active: bool = False,
    calibration_direct: CalibrationDirect | str | None = None,
    max_effective_steps: int = 1,
    policy: SelectionPolicy | None = None,
    **_: Any,
) -> str:
    """Краткая причина, почему фаза выполнилась, но действий 0.

    Args:
        phase_id: идентификатор фазы (как в ``PHASE_TITLES``).
        prepared: operable snapshot после предыдущих фаз.
        resolve: порог resolve для UP/passing/calibration.
        max_pay_for_order: потолок для guard.
        fact_pay_for_order: факт CPA pay_for_order для enable.
        plan_fact_changed: gate enable / calibration.
        views_changed: gate enable / calibration.
        eligibility_by_ks_id: eligibility по ks_id.
        ladder_inputs: лестница RK/rec.
        shelf_click_mode: режим полки.
        aggressiveness: агрессивность rollout.
        shelf_active: полка включена в РК.
        calibration_direct: TIGHTEN или LOOSEN для resolve_calibration.
        max_effective_steps: adaptive cap калибровки.
        policy: SelectionPolicy для passing/realloc (опционально).

    Returns:
        Русский текст для UI (без префикса «без изменений —»).
    """
    handlers = {
        "hard_status_sync": lambda: "режимы уже соответствуют hard_status",
        "cap_down": lambda: _note_cap_down(prepared, eligibility_by_ks_id),
        "passing_up": lambda: _note_passing_up(
            prepared,
            resolve=resolve,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        ),
        "shelf_cleanup": lambda: _note_shelf_cleanup(
            prepared,
            shelf_active=shelf_active,
            click_mode=shelf_click_mode,
            ladder_inputs=ladder_inputs,
        ),
        "max_cpa_guard": lambda: _note_max_cpa_guard(
            prepared,
            max_pay_for_order=max_pay_for_order,
            shelf_click_mode=shelf_click_mode,
            aggressiveness=aggressiveness,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        ),
        "cost_reallocation": lambda: _note_cost_reallocation(
            prepared,
            resolve=resolve,
            policy=policy,
        ),
        "pay_for_order_gap_enable": lambda: _note_enable_gap(
            prepared,
            eligibility_by_ks_id=eligibility_by_ks_id,
            fact_pay_for_order=fact_pay_for_order,
            resolve=resolve,
            plan_fact_changed=plan_fact_changed,
            views_changed=views_changed,
        ),
        "resolve_calibration": lambda: _note_resolve_calibration(
            prepared,
            resolve=resolve,
            calibration_direct=calibration_direct,
            shelf_click_mode=shelf_click_mode,
            aggressiveness=aggressiveness,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
            max_effective_steps=max_effective_steps,
        ),
        "no_data_bootstrap": lambda: "нет ключей для DATA_BOOTSTRAP",
    }
    handler = handlers.get(phase_id)
    if handler is None:
        return "планировщик не выбрал ключей"
    return handler()


def _note_cap_down(
    prepared: PreparedList,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
) -> str:
    if not prepared:
        return "нет operable ключей"
    if eligibility_by_ks_id is None:
        return "нет ключей выше tier-cap"
    if plan_mode_cap_down(prepared, eligibility_by_ks_id=eligibility_by_ks_id):
        return "планировщик не выбрал ключей"
    return "нет ключей выше tier-cap"


def _note_passing_up(
    prepared: PreparedList,
    *,
    resolve: float | None,
    policy: SelectionPolicy | None,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if not prepared:
        return "нет operable ключей"
    if policy is None:
        return "нет режимов с cost ≤ resolve для UP"
    actions = plan_passing_up(
        prepared,
        resolve=float(resolve),
        policy=policy,
        eligibility_by_ks_id=eligibility_by_ks_id,
        ladder_inputs=ladder_inputs,
    )
    if actions:
        return "планировщик не выбрал ключей"
    return "нет режимов с cost ≤ resolve для UP"


def _note_shelf_cleanup(
    prepared: PreparedList,
    *,
    shelf_active: bool,
    click_mode: ShelfClickMode | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    if not shelf_active:
        return "полка неактивна"
    if click_mode is None:
        return "полка неактивна"
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    if ladder.rec_orders_per_view is None:
        return "rec gate неактивен (нет rec_orders_per_view)"
    return "нет ключей с shelf rec FAIL"


def _note_max_cpa_guard(
    prepared: PreparedList,
    *,
    max_pay_for_order: float | None,
    shelf_click_mode: ShelfClickMode | None,
    aggressiveness: V3RolloutAggressiveness | None,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    if max_pay_for_order is None:
        return "max недоступен"
    if not prepared:
        return "нет operable ключей"
    click = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
    aggr = aggressiveness or V3RolloutAggressiveness.MID
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    above = 0
    for ctx, current in prepared:
        if current == KeywordStrategyMode.OFF:
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        cpo = operational_cpo_at_keyword_target_place(ctx, ladder_inputs=ladder)
        if cpo is not None and float(cpo) > float(max_pay_for_order):
            above += 1
    if above > 0:
        return (
            f"нет trim: {above} ключей с CPO > max, но планировщик не снизил "
            "(rec-gate / min_cpa bound / уже на целевом режиме)"
        )
    return "нет ключей с operational CPO > max"


def _note_cost_reallocation(
    prepared: PreparedList,
    *,
    resolve: float | None,
    policy: SelectionPolicy | None,
) -> str:
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if not prepared:
        return "нет operable ключей"
    return "нет пар для перераспределения (дорогие active / дешёвые passing)"


def _note_enable_gap(
    prepared: PreparedList,
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    fact_pay_for_order: float | None,
    resolve: float | None,
    plan_fact_changed: bool,
    views_changed: bool,
) -> str:
    if fact_pay_for_order is None:
        return "fact pay_for_order недоступен"
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if float(fact_pay_for_order) >= MAX_PAY_STABILIZATION_RATIO * float(resolve):
        return (
            f"fact ≥ {MAX_PAY_STABILIZATION_RATIO:.0%}×resolve "
            "(зона стабилизации, enable не нужен)"
        )
    if not plan_fact_changed:
        return "plan/fact не изменились"
    if not views_changed:
        return "views не изменились"
    if eligibility_by_ks_id is None:
        return "нет NO DATA ключей в OFF"
    candidates = 0
    for ctx, mode in prepared:
        if mode != KeywordStrategyMode.OFF:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = eligibility_by_ks_id.get(int(ks_id))
        if elig is None or elig.data_tier != KeywordDataTier.KEYWORD_NO_DATA:
            continue
        if not is_keyword_no_data(ctx.keyword):
            continue
        if not _hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        candidates += 1
    if candidates == 0:
        return "нет NO DATA ключей в OFF"
    return "планировщик не выбрал ключей"


def _note_resolve_calibration(
    prepared: PreparedList,
    *,
    resolve: float | None,
    calibration_direct: CalibrationDirect | str | None,
    shelf_click_mode: ShelfClickMode | None,
    aggressiveness: V3RolloutAggressiveness | None,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
    max_effective_steps: int,
) -> str:
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    direct = calibration_direct
    if isinstance(direct, str):
        try:
            direct = CalibrationDirect(direct)
        except ValueError:
            direct = None
    click = shelf_click_mode or ShelfClickMode.ORGANIC_DOMINANT
    aggr = aggressiveness or V3RolloutAggressiveness.MID
    if direct == CalibrationDirect.LOOSEN:
        return _note_calibration_up(
            prepared,
            shelf_click_mode=click,
            aggressiveness=aggr,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        )
    if direct == CalibrationDirect.TIGHTEN:
        return _note_calibration_tighten(
            prepared,
            cost_ceiling=float(resolve),
            shelf_click_mode=click,
            aggressiveness=aggr,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
            max_effective_steps=max_effective_steps,
        )
    return "направление калибровки не задано"


def _note_calibration_up(
    prepared: PreparedList,
    *,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    """Причина нулевого UP: нет ключа со следующим effective-шагом."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
        collect_calibration_up_next_step_candidates,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    pool = collect_calibration_up_next_step_candidates(
        prepared,
        policy=policy,
        ladder_inputs=ladder_inputs,
        eligibility_by_ks_id=eligibility_by_ks_id,
    )
    if not pool:
        return "нет ключа с допустимым следующим шагом UP (state/PFO)"
    return f"пул UP: {len(pool)} кандидатов, действие не сформировано"


def _note_calibration_tighten(
    prepared: PreparedList,
    *,
    cost_ceiling: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
    max_effective_steps: int,
) -> str:
    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    ladder = ladder_inputs_for_prepared(prepared, ladder_inputs)
    operable = 0
    already_ok = 0
    no_down = 0
    for ctx, current in prepared:
        if current == KeywordStrategyMode.OFF:
            continue
        hard_status = int(ctx.keyword.hard_status)
        if hard_status not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
            continue
        operable += 1
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id is None:
            continue
        elig = _eligibility_for_ctx(ctx, eligibility_by_ks_id)
        if _min_cpa_bound_by_pay_for_order(elig):
            cost, _ = resolve_effective_state_cost_for_mode(
                ctx=ctx,
                to_mode=current,
                prepared=prepared,
                eligibility_by_ks_id=eligibility_by_ks_id,
                ladder_inputs=ladder,
            )
            if cost != float("inf") and float(cost) <= float(cost_ceiling):
                already_ok += 1
            continue
        catalog = _mode_catalog_for_ctx(ctx, prepared, ladder)
        target = _find_trim_target_mode_limited_steps(
            ctx,
            current,
            catalog=catalog,
            cost_ceiling=float(cost_ceiling),
            ladder_inputs=ladder,
            policy=policy,
            eligibility_by_ks_id=eligibility_by_ks_id,
            max_effective_steps=max_effective_steps,
        )
        if target == current:
            already_ok += 1
        else:
            no_down += 1
    if operable == 0:
        return "нет operable ключей"
    if already_ok == operable:
        return f"все {operable} operable уже с CPO ≤ resolve"
    return (
        f"нет ключей для DOWN: {operable} operable "
        f"({already_ok} уже ≤ resolve, {no_down} без шага DOWN)"
    )
