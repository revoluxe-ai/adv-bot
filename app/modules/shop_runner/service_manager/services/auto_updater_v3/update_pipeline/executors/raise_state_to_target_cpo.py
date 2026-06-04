"""Фаза: поднять ключ до max ladder-state с CPO <= resolve кампании."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    should_skip_raise_state_to_target_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
)
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
    """Поднять ключ до max ступени с ``cpo <= resolve``; DOWN запрещён (no-op).

    Skip всей фазы, если fact CPO РК ``>= 90 % plan.max_pay_for_order`` (стабилизация).
    """

    phase_name = "raise_state_to_target_cpo"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RaiseStateToTargetCpoExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Поднять operable ключи до max ступени с ``cpo <= resolve`` (только UP)."""
        self._skip_reason = _phase_skip_reason(context.adv_state)
        if self._skip_reason is not None:
            return
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


def _phase_skip_reason(adv_state: AdvState) -> str | None:
    """Skip R↑ при fact в зоне ``>= 90 % plan.max``; без fact — фаза выполняется."""
    if not should_skip_raise_state_to_target_cpo(adv_state):
        return None
    return "fact_cpo_ge_90pct_plan_max"
