"""Preamble clamp for active states against the live ``resolve`` ceiling.

The executor keeps the economic invariant centralized: active keyword states
must stay at or below the current campaign ``resolve``. ``max_effective_steps``
remains a separate calibration-budget concern.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_tier import (
    keyword_pfo_value,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    OPERABLE_LADDER_STAGES,
    pick_off_ladder_state,
    resolve_current_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class ClampStatesToResolveWhenNoEffectiveStepsExecutor:
    """Clamp active states to the current ``resolve`` ceiling."""

    phase_name = "clamp_states_to_resolve_when_no_effective_steps"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(
            ClampStatesToResolveWhenNoEffectiveStepsExecutor
        )

    def execute(self, context: UpdateContext) -> None:
        """Downgrade over-resolve active states to the best reachable economic state."""
        self._skip_reason = None
        state = context.adv_state
        if not state.resolve_valid or float(state.resolve) <= 0:
            self._skip_reason = "resolve_invalid"
            return

        resolve = float(state.resolve)
        cap_level = mode_level(state.policy.max_target_mode)

        for dto in context.keywords:
            if dto.current_mode == KeywordStrategyMode.OFF:
                continue

            current_cost = _current_effective_cost(dto)
            if current_cost is None or current_cost <= resolve:
                continue

            target_state = _resolve_clamp_target(
                dto,
                resolve=resolve,
                cap_level=cap_level,
            )
            if target_state is None:
                self._next_state_manager.force_off(dto)
                continue
            self._next_state_manager.raise_state_to_target_cpo(dto, target_state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _current_effective_cost(dto: KeywordDTO) -> float | None:
    """Current active economic cost for CH-backed ladder or PFO/no-CH key."""
    if bool(dto.position_profile):
        current_state = resolve_current_ladder_state(dto)
        if current_state is None or current_state.cpo is None:
            return None
        return float(current_state.cpo)
    return keyword_pfo_value(dto.calculated_keyword)


def _resolve_clamp_target(
    dto: KeywordDTO,
    *,
    resolve: float,
    cap_level: int,
) -> KeywordV3LadderState | None:
    """Best reachable state at or below the live resolve ceiling.

    The helper keeps the search strictly downward: candidates must not exceed
    the current active mode and must remain inside the policy cap.
    """
    if bool(dto.position_profile):
        current_state = resolve_current_ladder_state(dto)
        if current_state is None:
            return None
        current_level = mode_level(dto.current_mode)
        candidates = [
            state
            for state in dto.ladder_states
            if state.strategy_mode != KeywordStrategyMode.OFF
            and state.is_valid
            and state.cpo is not None
            and float(state.cpo) <= float(resolve)
            and state.stage in OPERABLE_LADDER_STAGES
            and mode_level(state.strategy_mode) <= current_level
            and mode_level(state.strategy_mode) <= cap_level
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda state: (
                mode_level(state.strategy_mode),
                -int(state.target_position),
            ),
        )

    pfo = keyword_pfo_value(dto.calculated_keyword)
    if pfo is None:
        return None
    if float(pfo) <= float(resolve):
        return None
    return pick_off_ladder_state(dto)
