"""Фаза R: симметричный cost reallocation (DOWN дорогого + UP дешёвого)."""

from __future__ import annotations

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

_MAX_REBALANCE_CYCLES = 50


class RebalanceExecutor:
    """COST_REALLOCATION: цикл DOWN max-CPO active + UP min-CPO potential."""

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
            recipient = _pick_cheapest(potential_states)
            if donor[2] <= recipient[2]:
                break
            down_state = pick_effective_down_ladder_state(donor[0])
            if down_state is None:
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


def _pick_most_expensive(states: list[StateBinding]) -> StateBinding:
    return max(states, key=lambda item: (item[2], item[0].keyword_setting_id))


def _pick_cheapest(states: list[StateBinding]) -> StateBinding:
    return min(states, key=lambda item: (item[2], item[0].keyword_setting_id))
