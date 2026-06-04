"""Фаза: поднять ключ до max ladder-state с CPO <= resolve кампании."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    current_aggression_rank,
    ladder_aggression_rank,
    pick_max_ladder_state_at_or_below_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class RaiseStateToTargetCpoExecutor:
    """Поднять ключ до max ступени с ``cpo <= resolve``; DOWN запрещён (no-op)."""

    phase_name = "raise_state_to_target_cpo"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RaiseStateToTargetCpoExecutor)

    def execute(self, context: UpdateContext) -> str | None:
        if self._skip(context):
            return 'fact cpo > 0.9 max'
        target_cpo = float(context.adv_state.resolve)
        for dto in context.keywords:
            if dto.is_not_full():
                continue
            state = pick_max_ladder_state_at_or_below_cpo(dto, target_cpo)
            if state is None:
                continue
            if ladder_aggression_rank(state) <= current_aggression_rank(dto):
                continue
            self._next_state_manager.raise_state_to_target_cpo(dto, state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason

    def _skip(self, context: UpdateContext) -> bool:
        if context.adv_state.fact_pay_for_order is None:
            self._skip_reason = 'fact pay is None'
            return True
        if context.adv_state.fact_pay_for_order > 0.9:
            self._skip_reason = 'fact cpo > 0.9 max'
            return True
        return False
