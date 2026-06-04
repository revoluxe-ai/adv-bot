"""Циклы calibration UP/DOWN через ``StatesListGenerator`` + in-place ``KeywordDTO``."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
    pick_off_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StateBinding,
    StatesListGenerator,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


def run_calibration_down(
    context: UpdateContext,
    *,
    resolve: float,
    max_steps: int,
    nsm: NextStateManager,
) -> None:
    """CAL DOWN: до ``max_steps`` итераций max CPO из list1 с ``cpo > resolve`` → DOWN."""
    ceiling = float(resolve)
    step_budget = max(1, int(max_steps))
    generator = StatesListGenerator(context.adv_state, for_calibration=True)
    eligibility = context.adv_state.eligibility_by_ks_id

    for _ in range(step_budget):
        current_states, _potential = generator.get_current_states(context.keywords)
        donors = [binding for binding in current_states if binding[2] > ceiling]
        if not donors:
            break
        donor = _pick_most_expensive(donors)
        down_state = _resolve_calibration_down_state(
            donor,
            ceiling=ceiling,
            eligibility_by_ks_id=eligibility,
        )
        if down_state is None:
            break
        nsm.raise_state_to_target_cpo(donor[0], down_state)


def run_potential_up_steps(
    context: UpdateContext,
    *,
    max_steps: int,
    nsm: NextStateManager,
    for_calibration: bool = False,
) -> None:
    """До ``max_steps`` UP-итераций: min CPO из list2, пересборка списков каждый шаг."""
    step_budget = max(0, int(max_steps))
    if step_budget == 0:
        return
    generator = StatesListGenerator(
        context.adv_state,
        for_calibration=for_calibration,
    )
    for _ in range(step_budget):
        _current, potential_states = generator.get_current_states(context.keywords)
        if not potential_states:
            break
        recipient = _pick_cheapest(potential_states)
        nsm.raise_state_to_target_cpo(recipient[0], recipient[1])


def run_calibration_up(
    context: UpdateContext,
    *,
    max_steps: int,
    nsm: NextStateManager,
) -> None:
    """CAL UP: до ``max_steps`` итераций min CPO из list2 → apply ladder state."""
    run_potential_up_steps(
        context,
        max_steps=max(1, int(max_steps)),
        nsm=nsm,
        for_calibration=True,
    )


def _resolve_calibration_down_state(
    donor: StateBinding,
    *,
    ceiling: float,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
) -> KeywordV3LadderState | None:
    """Effective DOWN или OFF для NO CH MIN bound by pay_for_order."""
    dto = donor[0]
    elig = eligibility_by_ks_id.get(dto.keyword_setting_id)
    if _min_cpa_bound_by_pay_for_order(elig):
        if _keyword_pay_for_order_exceeds(dto, ceiling=ceiling):
            return pick_off_ladder_state(dto)
        return None
    return pick_effective_down_ladder_state(dto)


def _min_cpa_bound_by_pay_for_order(
    eligibility: KeywordV3Eligibility | None,
) -> bool:
    """MIN-only + ``target_place=0``: NO CH или collapsed CH ladder + pay_for_order."""
    return (
        eligibility is not None
        and eligibility.participates_in_ladder
        and eligibility.target_place_fallback_zero
        and eligibility.allowed_modes == frozenset({KeywordStrategyMode.MIN_CPA})
    )


def _pick_most_expensive(states: list[StateBinding]) -> StateBinding:
    return max(states, key=lambda item: (item[2], item[0].keyword_setting_id))


def _pick_cheapest(states: list[StateBinding]) -> StateBinding:
    return min(states, key=lambda item: (item[2], item[0].keyword_setting_id))


def _keyword_pay_for_order_exceeds(dto: KeywordDTO, *, ceiling: float) -> bool:
    """``pay_for_order`` строго выше ``ceiling`` (NO CH MIN trim → OFF)."""
    pfo = dto.calculated_keyword.pay_for_order
    if pfo is None:
        return False
    return float(pfo) > float(ceiling)


def plan_calibration_trim_actions(
    prepared: "PreparedList",
    *,
    resolve: float,
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: "V3RolloutAggressiveness",
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    max_effective_steps: int = 1,
) -> list["V3Action"]:
    """Legacy trim entry: CAL DOWN на ``prepared`` → ``V3Action`` для unit-тестов."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3Action,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        build_eligibility_map,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
        V3RolloutAggressiveness,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        PreparedList,
        SelectionPolicy,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
        ResolveCalibrationExecutor,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
        NextStateManager,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
        next_state_steps_for_executor,
        steps_to_v3_actions,
    )

    _ = ShelfClickMode, V3RolloutAggressiveness
    ladder = ladder_inputs or LadderInputs.from_contexts(
        [ctx for ctx, _ in prepared],
    )
    elig = eligibility_by_ks_id
    if not elig:
        elig = build_eligibility_map(
            ladder.all_contexts,
            campaign_orders_per_cart_7d=ladder.campaign_orders_per_cart_7d,
        )
    adv_state = replace(
        AdvState.empty(),
        eligibility_by_ks_id=elig,
        ladder_inputs=ladder,
        resolve=float(resolve),
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=shelf_click_mode,
            aggressiveness=aggressiveness,
        ),
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        resolve_valid=True,
        max_effective_steps=max_effective_steps,
    )
    context = update_context_from_prepared(prepared, adv_state=adv_state)
    nsm = NextStateManager(ResolveCalibrationExecutor)
    run_calibration_down(
        context,
        resolve=float(resolve),
        max_steps=max_effective_steps,
        nsm=nsm,
    )
    executor_name = ResolveCalibrationExecutor.__name__
    actions: list[V3Action] = []
    for dto in context.keywords:
        steps = next_state_steps_for_executor(
            dto,
            executor_name=executor_name,
            steps_before=0,
        )
        actions.extend(steps_to_v3_actions(dto, steps))
    return actions


def plan_calibration_actions(
    prepared: "PreparedList",
    *,
    resolve: float,
    calibration_direct: "CalibrationDirect",
    shelf_click_mode: "ShelfClickMode",
    aggressiveness: "V3RolloutAggressiveness",
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: "LadderInputs | None" = None,
    max_effective_steps: int = 1,
) -> list["V3Action"]:
    """Legacy test entry: CAL UP/DOWN на ``prepared`` → ``V3Action``."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
        CalibrationDirect,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        V3Action,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        build_eligibility_map,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
        V3RolloutAggressiveness,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        PreparedList,
        SelectionPolicy,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.resolve_calibration import (
        ResolveCalibrationExecutor,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
        NextStateManager,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
        next_state_steps_for_executor,
        steps_to_v3_actions,
    )

    _ = ShelfClickMode, V3RolloutAggressiveness, PreparedList
    ladder = ladder_inputs or LadderInputs.from_contexts(
        [ctx for ctx, _ in prepared],
    )
    elig = eligibility_by_ks_id
    if not elig:
        elig = build_eligibility_map(
            ladder.all_contexts,
            campaign_orders_per_cart_7d=ladder.campaign_orders_per_cart_7d,
        )
    adv_state = replace(
        AdvState.empty(),
        eligibility_by_ks_id=elig,
        ladder_inputs=ladder,
        resolve=float(resolve),
        policy=SelectionPolicy.from_aggressiveness(
            click_mode=shelf_click_mode,
            aggressiveness=aggressiveness,
        ),
        shelf_click_mode=shelf_click_mode,
        aggressiveness=aggressiveness,
        resolve_valid=True,
        calibration_direct=calibration_direct,
        max_effective_steps=max_effective_steps,
    )
    context = update_context_from_prepared(prepared, adv_state=adv_state)
    nsm = NextStateManager(ResolveCalibrationExecutor)
    if calibration_direct == CalibrationDirect.TIGHTEN:
        run_calibration_down(
            context,
            resolve=float(resolve),
            max_steps=max_effective_steps,
            nsm=nsm,
        )
    else:
        run_calibration_up(
            context,
            max_steps=max_effective_steps,
            nsm=nsm,
        )
    executor_name = ResolveCalibrationExecutor.__name__
    actions: list[V3Action] = []
    for dto in context.keywords:
        steps = next_state_steps_for_executor(
            dto,
            executor_name=executor_name,
            steps_before=0,
        )
        actions.extend(steps_to_v3_actions(dto, steps))
    return actions
