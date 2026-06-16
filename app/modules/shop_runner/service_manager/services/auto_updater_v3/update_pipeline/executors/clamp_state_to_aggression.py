"""Early preamble clamp: понижает текущие ladder-state выше policy cap.

Executor нужен как явный защитный слой для V3 actions: если ключ уже поднят
выше разрешённой агрессии, мы сразу сводим его к cap-state до всех UP/rebalance
фаз. Это сохраняет полную матрицу ladder для чтения и DOWN-логики, но делает
policy.max_target_mode инвариантом для action-generation.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    valid_ladder_state_for_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)

_MISSING_CAP_LADDER_STATE = "missing_cap_ladder_state"


class ClampStateToAggressionExecutor:
    """Понизить FULL/PFO ключи до policy cap, если текущий mode выше cap."""

    phase_name = "clamp_state_to_aggression"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(ClampStateToAggressionExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Понизить ключи выше cap до валидного ladder-state на cap."""
        self._skip_reason = None
        cap = context.adv_state.policy.max_target_mode
        missing_cap_state = False
        applied = False

        for dto in context.keywords:
            if dto.current_mode <= cap:
                continue
            cap_state = valid_ladder_state_for_mode(dto, cap)
            if cap_state is None:
                missing_cap_state = True
                continue
            self._next_state_manager.raise_state_to_target_cpo(dto, cap_state)
            applied = True

        if not applied and missing_cap_state:
            self._skip_reason = _MISSING_CAP_LADDER_STATE

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
