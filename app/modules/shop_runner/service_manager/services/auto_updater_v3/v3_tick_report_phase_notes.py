"""Диагностика нулевого исхода preamble-фаз для отчёта V3-тика (Telegram UI).

Зеркалит условия ``plan_*`` / executor skip-gates без построения действий:
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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    FACT_OVER_MAX_DEEP_OVERSPEND_RATIO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    is_keyword_no_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedListLike,
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder_tick_helpers import (
    hard_status_allows_up,
    ladder_inputs_for_prepared,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )


def summarize_phase_zero_actions(
    phase_id: str,
    *,
    prepared: PreparedListLike,
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
        calibration_direct: ветка калибровки UP или DOWN (``CalibrationDirect``).
        max_effective_steps: adaptive cap калибровки.
        policy: SelectionPolicy для passing/realloc (опционально).

    Returns:
        Русский текст для UI (без префикса «без изменений —»).
    """
    handlers = {
        "validate_state_by_hard_status": lambda: "нет ключей с hard_status=1",
        "not_full_target_place_migrate": lambda: _note_not_full_tp_migrate(prepared),
        "validate_not_full_state": lambda: _note_validate_not_full(prepared),
        "not_full_target_place_overspend_reset": lambda: _note_not_full_tp_overspend(
            fact_pay_for_order=fact_pay_for_order,
            max_pay_for_order=max_pay_for_order,
        ),
        "not_full_target_place_plan_fact": lambda: _note_not_full_tp_plan_fact(
            plan_fact_changed=plan_fact_changed,
            views_changed=views_changed,
        ),
        "raise_state_to_target_cpo": lambda: _note_raise_state_to_target_cpo(
            prepared,
            resolve=resolve,
        ),
        "reset_over_max_cpo_on_overspend": lambda: _note_reset_over_max_cpo(
            prepared,
            max_pay_for_order=max_pay_for_order,
            fact_pay_for_order=fact_pay_for_order,
        ),
        "shelf_cleanup": lambda: _note_shelf_cleanup(
            prepared,
            shelf_active=shelf_active,
            click_mode=shelf_click_mode,
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
            max_pay_for_order=max_pay_for_order,
        ),
        "pay_for_order_over_max_off_on_deep_overspend": lambda: _note_pfo_off_deep_overspend(
            prepared,
            fact_pay_for_order=fact_pay_for_order,
            max_pay_for_order=max_pay_for_order,
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


def _note_validate_not_full(prepared: PreparedListLike) -> str:
    if not prepared:
        return "нет operable ключей"
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        if not bool(ctx.position_profile):
            return "NOT FULL active уже MIN (tp — migrate / plan-fact)"
    return "нет NOT FULL active ключей"


def _note_not_full_tp_overspend(
    *,
    fact_pay_for_order: float | None,
    max_pay_for_order: float | None,
) -> str:
    if fact_pay_for_order is None or max_pay_for_order is None:
        return "нет fact/max для overspend"
    if float(fact_pay_for_order) <= float(max_pay_for_order):
        return "CPO РК в пределах MAX"
    return "fact CPO > MAX — сброс tp NOT FULL MIN в 0"


def _note_not_full_tp_migrate(prepared: PreparedListLike) -> str:
    if not prepared:
        return "нет operable ключей"
    for ctx, mode in prepared:
        if mode == KeywordStrategyMode.OFF:
            continue
        if not bool(ctx.position_profile):
            return "есть NOT FULL MIN с tp=0 для миграции на pos−1"
    return "нет кандидатов migrate (tp≠0 или нет позиции)"


def _note_not_full_tp_plan_fact(
    *,
    plan_fact_changed: bool,
    views_changed: bool,
) -> str:
    if not plan_fact_changed and not views_changed:
        return "plan/fact и views без изменений"
    if not plan_fact_changed:
        return "plan/fact без изменений"
    if not views_changed:
        return "views без изменений"
    return "gate пройден — можно сдвинуть tp ±1"


def _note_raise_state_to_target_cpo(
    prepared: PreparedListLike,
    *,
    resolve: float | None,
) -> str:
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if not prepared:
        return "нет operable ключей"
    return "нет ключей для подъёма до resolve (все ступени выше resolve или уже на max)"


def _note_reset_over_max_cpo(
    prepared: PreparedListLike,
    *,
    max_pay_for_order: float | None,
    fact_pay_for_order: float | None,
) -> str:
    if max_pay_for_order is None:
        return "max недоступен"
    if fact_pay_for_order is None:
        return "fact pay_for_order недоступен"
    if float(fact_pay_for_order) <= float(max_pay_for_order):
        return "fact ≤ plan max (overspend gate)"
    if not prepared:
        return "нет operable ключей"
    return "нет GAP/active ключей с ladder CPO > max для сброса"


def _note_shelf_cleanup(
    prepared: PreparedListLike,
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


def _note_cost_reallocation(
    prepared: PreparedListLike,
    *,
    resolve: float | None,
    policy: SelectionPolicy | None,
) -> str:
    _ = policy
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if not prepared:
        return "нет operable ключей"
    return (
        "нет пар donor/recipient: potential пуст (все на потолке), "
        "равновесие CPO или нет active для среза"
    )


def _note_pfo_off_deep_overspend(
    prepared: PreparedListLike,
    *,
    fact_pay_for_order: float | None,
    max_pay_for_order: float | None,
) -> str:
    if max_pay_for_order is None:
        return "max недоступен"
    if fact_pay_for_order is None:
        return "fact pay_for_order недоступен"
    threshold = FACT_OVER_MAX_DEEP_OVERSPEND_RATIO * float(max_pay_for_order)
    if float(fact_pay_for_order) <= threshold:
        return (
            f"fact ≤ {FACT_OVER_MAX_DEEP_OVERSPEND_RATIO:.0%}×max "
            "(deep overspend gate)"
        )
    if not prepared:
        return "нет operable ключей"
    return "нет active ключей с pay_for_order > max для OFF"


def _note_enable_gap(
    prepared: PreparedListLike,
    *,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    fact_pay_for_order: float | None,
    resolve: float | None,
    max_pay_for_order: float | None = None,
) -> str:
    if fact_pay_for_order is None:
        return "fact pay_for_order недоступен"
    if resolve is None or float(resolve) <= 0:
        return "resolve недоступен"
    if (
        max_pay_for_order is not None
        and float(fact_pay_for_order) > float(max_pay_for_order)
    ):
        return "fact > max (overspend, enable не нужен)"
    if float(fact_pay_for_order) >= MAX_PAY_STABILIZATION_RATIO * float(resolve):
        return (
            f"fact ≥ {MAX_PAY_STABILIZATION_RATIO:.0%}×resolve "
            "(зона стабилизации, enable не нужен)"
        )
    if eligibility_by_ks_id is None:
        return "нет NO DATA GAP-ключей в OFF"
    candidates = 0
    for ctx, mode in prepared:
        if mode != KeywordStrategyMode.OFF:
            continue
        ks_id = ctx.keyword.keyword_setting_original_id
        if ks_id <= 0:
            continue
        elig = eligibility_by_ks_id.get(ks_id)
        if elig is None or elig.data_tier != KeywordDataTier.KEYWORD_NO_DATA:
            continue
        if not is_keyword_no_data(ctx.keyword):
            continue
        if not hard_status_allows_up(int(ctx.keyword.hard_status)):
            continue
        candidates += 1
    if candidates == 0:
        return "нет NO DATA GAP-ключей в OFF"
    return "нет подходящего GAP-кандидата для enable"


def _note_resolve_calibration(
    prepared: PreparedListLike,
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
        return _note_calibration_down(
            prepared,
            cost_ceiling=float(resolve),
            shelf_click_mode=click,
            aggressiveness=aggr,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        )
    return "направление калибровки не задано"


def _note_calibration_up(
    prepared: PreparedListLike,
    *,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    """Причина нулевого UP: пустой list2 ``StatesListGenerator`` (``for_calibration=True``)."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
        StatesListGenerator,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    ladder = ladder_inputs or ladder_inputs_for_prepared(prepared)
    adv_state = replace(
        AdvState.empty(),
        eligibility_by_ks_id=eligibility_by_ks_id or {},
        ladder_inputs=ladder,
        policy=policy,
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    context = update_context_from_prepared(prepared, adv_state=adv_state)
    _current, potential = StatesListGenerator(
        adv_state,
        for_calibration=True,
    ).get_current_states(context.keywords)
    if not potential:
        return "нет ключа с допустимым следующим шагом UP (state/PFO)"
    return f"пул UP: {len(potential)} кандидатов, действие не сформировано"


def _note_calibration_down(
    prepared: PreparedListLike,
    *,
    cost_ceiling: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None,
    ladder_inputs: LadderInputs | None,
) -> str:
    """Причина нулевого CAL DOWN: нет ключа с CPO > resolve в list1."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
        StatesListGenerator,
    )

    policy = SelectionPolicy.from_aggressiveness(
        click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    ladder = ladder_inputs or ladder_inputs_for_prepared(prepared)
    adv_state = replace(
        AdvState.empty(),
        eligibility_by_ks_id=eligibility_by_ks_id or {},
        ladder_inputs=ladder,
        policy=policy,
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
    )
    context = update_context_from_prepared(prepared, adv_state=adv_state)
    current, _potential = StatesListGenerator(
        adv_state,
        for_calibration=True,
    ).get_current_states(context.keywords)
    ceiling = float(cost_ceiling)
    donors = [binding for binding in current if binding[2] > ceiling]
    if not donors:
        return "нет ключа с state > resolve и допустимым шагом CAL DOWN"
    return f"пул CAL DOWN: {len(donors)} кандидатов, действие не сформировано"
