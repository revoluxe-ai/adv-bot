"""Фаза R: симметричный cost reallocation (DOWN дорогого + UP дешёвого)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    LadderStepSnapshot,
    classify_ladder_step,
    ladder_step_snapshot_from_dto,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StateBinding,
    StatesListGenerator,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)

# Верхняя граница пар DOWN+UP за тик (каждая итерация — одна пара при наличии donor/recipient).
_MAX_REBALANCE_CYCLES = 3000


class RebalanceExecutor:
    """COST_REALLOCATION: перетекание cost из active в potential.

    Итерация: самый дорогой ``current_active`` → DOWN; из ``potential_up`` — минимальный
    CPO с учтённым UP. Это не «recipient обязан дешевле донора», а перебор списков,
    пока дешёвая ступень в potential ещё **ниже** CPO текущего донора (иначе смысла
    резать дорогого нет — выход из цикла).

    Пара пишется в audit только если оба шага реальны (``classify_ladder_step``).
    """

    phase_name = "cost_reallocation"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RebalanceExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = _phase_skip_reason(context)
        if self._skip_reason is not None:
            return
        generator = StatesListGenerator(context.adv_state)
        for _ in range(_MAX_REBALANCE_CYCLES):
            current_states, potential_states = generator.get_current_states(
                context.keywords
            )
            if not current_states or not potential_states:
                break
            donor = _pick_most_expensive(current_states)
            down_state = pick_effective_down_ladder_state(donor[0])
            if down_state is None:
                break
            if not _ladder_step_would_change(donor[0], down_state):
                break
            recipient = _pick_cheapest_actionable_recipient(potential_states)
            if recipient is None:
                break
            if donor[2] <= recipient[2]:
                break
            self._next_state_manager.raise_state_to_target_cpo(donor[0], down_state)
            self._next_state_manager.raise_state_to_target_cpo(
                recipient[0],
                recipient[1],
            )

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _phase_skip_reason(context: UpdateContext) -> str | None:
    if not context.adv_state.resolve_valid:
        return "resolve_invalid"
    return None


def _snapshot_for_ladder_state(state: KeywordV3LadderState) -> LadderStepSnapshot:
    place = (
        None
        if state.strategy_mode == KeywordStrategyMode.OFF
        else int(state.target_position)
    )
    return LadderStepSnapshot(state.strategy_mode, place)


def _ladder_step_would_change(dto: KeywordDTO, state: KeywordV3LadderState) -> bool:
    """``True``, если применение ``state`` попадёт в audit как UP/DOWN/OFF."""
    before = ladder_step_snapshot_from_dto(dto)
    after = _snapshot_for_ladder_state(state)
    return classify_ladder_step(before, after) is not None


def _pick_cheapest_actionable_recipient(
    potential_states: list[StateBinding],
) -> StateBinding | None:
    """Минимальный CPO в ``potential_up``, для которого UP попадёт в audit."""
    for binding in sorted(
        potential_states, key=lambda item: (item[2], item[0].keyword_setting_id)
    ):
        if _ladder_step_would_change(binding[0], binding[1]):
            return binding
    return None


def _pick_most_expensive(states: list[StateBinding]) -> StateBinding:
    return max(states, key=lambda item: (item[2], item[0].keyword_setting_id))
