"""Циклы calibration UP/DOWN через ``StatesListGenerator`` + in-place ``KeywordDTO``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    LadderStepKind,
    classify_ladder_step,
    ladder_step_snapshot_from_dto,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedListLike,
)
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


_MAX_CALIBRATION_LOOP_ITERATIONS = 500


def _apply_and_count_up_ladder_step(
    dto: KeywordDTO,
    mutator: Callable[[], None],
) -> int:
    """Применить UP-мутацию; ``1`` только если SSOT зафиксировал ladder UP."""
    before = ladder_step_snapshot_from_dto(dto)
    mutator()
    after = ladder_step_snapshot_from_dto(dto)
    return 1 if classify_ladder_step(before, after) == LadderStepKind.UP else 0


def _apply_and_count_down_ladder_step(
    dto: KeywordDTO,
    mutator: Callable[[], None],
) -> int:
    """Применить DOWN-мутацию; ``1`` если SSOT зафиксировал ladder DOWN или OFF."""
    before = ladder_step_snapshot_from_dto(dto)
    mutator()
    after = ladder_step_snapshot_from_dto(dto)
    kind = classify_ladder_step(before, after)
    return 1 if kind in (LadderStepKind.DOWN, LadderStepKind.OFF) else 0


@dataclass(frozen=True)
class PotentialUpRunResult:
    """Итог цикла list2 UP (calibration или shelf compensation)."""

    ladder_steps_done: int = 0
    iterations_done: int = 0
    step_budget: int = 0
    stop_reason: str = "zero_budget"
    remaining_potential: int = 0


def run_calibration_down(
    context: UpdateContext,
    *,
    resolve: float,
    max_steps: int,
    nsm: NextStateManager,
) -> PotentialUpRunResult:
    """CAL DOWN: до ``max_steps`` ladder DOWN/OFF из list1 с ``cpo > resolve``.

    Returns:
        Счётчик фактически применённых ladder-шагов и служебные итоги цикла.
    """
    ceiling = float(resolve)
    step_budget = max(1, int(max_steps))
    generator = StatesListGenerator(context.adv_state, for_calibration=True)
    eligibility = context.adv_state.eligibility_by_ks_id

    ladder_steps_done = 0
    iterations = 0
    remaining_potential = 0
    stop_reason = "budget_exhausted"
    while ladder_steps_done < step_budget and iterations < _MAX_CALIBRATION_LOOP_ITERATIONS:
        iterations += 1
        current_states, _potential = generator.get_current_states(context.keywords)
        donors = [binding for binding in current_states if binding[2] > ceiling]
        if not donors:
            remaining_potential = 0
            stop_reason = "empty_potential"
            break
        donor = _pick_most_expensive(donors)
        down_state = _resolve_calibration_down_state(
            donor,
            ceiling=ceiling,
            eligibility_by_ks_id=eligibility,
        )
        if down_state is None:
            remaining_potential = len(donors)
            stop_reason = "budget_exhausted"
            break
        dto = donor[0]
        delta = _apply_and_count_down_ladder_step(
            dto,
            lambda s=down_state: nsm.raise_state_to_target_cpo(dto, s),
        )
        if delta == 0:
            remaining_potential = len(donors)
            stop_reason = "budget_exhausted"
            break
        ladder_steps_done += delta
        remaining_potential = len(donors)
    else:
        if iterations >= _MAX_CALIBRATION_LOOP_ITERATIONS:
            stop_reason = "max_iterations_safety"

    return PotentialUpRunResult(
        ladder_steps_done=ladder_steps_done,
        iterations_done=iterations,
        step_budget=step_budget,
        stop_reason=stop_reason,
        remaining_potential=remaining_potential,
    )


def run_potential_up_steps(
    context: UpdateContext,
    *,
    max_steps: int,
    nsm: NextStateManager,
    for_calibration: bool = False,
) -> PotentialUpRunResult:
    """До ``max_steps`` ladder UP: min CPO из list2; alias на том же ``target_place`` не считаются."""
    step_budget = max(0, int(max_steps))
    if step_budget == 0:
        return PotentialUpRunResult(step_budget=0, stop_reason="zero_budget")
    generator = StatesListGenerator(
        context.adv_state,
        for_calibration=for_calibration,
    )
    ladder_steps_done = 0
    iterations_done = 0
    stop_reason = "budget_exhausted"
    while (
        ladder_steps_done < step_budget
        and iterations_done < _MAX_CALIBRATION_LOOP_ITERATIONS
    ):
        _current, potential_states = generator.get_current_states(context.keywords)
        remaining_potential = len(potential_states)
        if not potential_states:
            stop_reason = "empty_potential"
            break
        recipient = _pick_cheapest(potential_states)
        dto, target_state, _cpo = recipient
        delta = _apply_and_count_up_ladder_step(
            dto,
            lambda s=target_state: nsm.raise_state_to_target_cpo(dto, s),
        )
        iterations_done += 1
        if delta == 0:
            continue
        ladder_steps_done += delta
    else:
        if iterations_done >= _MAX_CALIBRATION_LOOP_ITERATIONS:
            stop_reason = "max_iterations_safety"
        _current, potential_states = generator.get_current_states(context.keywords)
        remaining_potential = len(potential_states)
        if (
            stop_reason == "budget_exhausted"
            and ladder_steps_done < step_budget
            and not potential_states
        ):
            stop_reason = "budget_exhausted_pool_empty"
    return PotentialUpRunResult(
        ladder_steps_done=ladder_steps_done,
        iterations_done=iterations_done,
        step_budget=step_budget,
        stop_reason=stop_reason,
        remaining_potential=remaining_potential,
    )


def run_calibration_up(
    context: UpdateContext,
    *,
    max_steps: int,
    nsm: NextStateManager,
) -> PotentialUpRunResult:
    """CAL UP: до ``max_steps`` ladder UP из list2 (alias на том же ``target_place`` не считаются)."""
    return run_potential_up_steps(
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

# TODO: Кажется мертвый метод
def plan_calibration_trim_actions(
    prepared: PreparedListLike,
    *,
    resolve: float,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
    max_effective_steps: int,
) -> list[V3Action]:
    """Legacy trim entry: CAL DOWN на ``prepared`` → ``V3Action`` для unit-тестов."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        build_eligibility_map,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
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

# TODO: Кажется мертвый метод
def plan_calibration_actions(
    prepared: PreparedListLike,
    *,
    resolve: float,
    calibration_direct: CalibrationDirect,
    shelf_click_mode: ShelfClickMode,
    aggressiveness: V3RolloutAggressiveness,
    eligibility_by_ks_id: dict[int, KeywordV3Eligibility] | None = None,
    ladder_inputs: LadderInputs | None = None,
    max_effective_steps: int,
) -> list[V3Action]:
    """Legacy test entry: CAL UP/DOWN на ``prepared`` → ``V3Action``."""
    from dataclasses import replace

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
        CalibrationDirect,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
        AdvState,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        build_eligibility_map,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
        update_context_from_prepared,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
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
