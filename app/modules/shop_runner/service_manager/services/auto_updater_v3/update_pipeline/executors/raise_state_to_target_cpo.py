"""Фаза: поднять ключ до max ladder-state с CPO < min(resolve, raise_cpo_ceiling)."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    should_skip_keyword_raise_to_target_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
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
    current_aggression_rank,
    has_ch_backed_economic_ladder,
    ladder_aggression_rank,
    pick_max_valid_ladder_state_at_or_below_cpo,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class RaiseStateToTargetCpoExecutor:
    """Поднять ключ до max ступени с ``cpo < min(resolve, raise_cpo_ceiling)``; DOWN запрещён.

    Фаза работает только по FULL ключам: для PFO/GAP её контур закрыт NF
    validate/migrate/plan-fact. При overspend (``guard_condition``) потолок —
    ``raise_cpo_ceiling`` (fact CPO). Per-keyword skip в зоне стабилизации только
    если ``kw.pay_for_order > resolve``.
    """

    phase_name = "raise_state_to_target_cpo"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RaiseStateToTargetCpoExecutor)

    def execute(self, context: UpdateContext) -> None:
        """Поднять operable ключи до max ступени под потолком (только UP)."""
        self._skip_reason = None
        adv = context.adv_state
        target_cpo = float(adv.resolve)
        if adv.guard_condition:
            ceiling = adv.raise_cpo_ceiling
            if ceiling is not None:
                target_cpo = min(target_cpo, float(ceiling))

        for dto in context.keywords:
            if not has_ch_backed_economic_ladder(dto):
                continue
            if should_skip_keyword_raise_to_target_cpo(dto, adv):
                continue

            state = pick_max_valid_ladder_state_at_or_below_cpo(
                dto,
                target_cpo,
                strict_ceiling=True,
                max_target_mode=adv.policy.max_target_mode,
            )
            if state is None:
                continue
            if ladder_aggression_rank(state) <= current_aggression_rank(dto):
                continue
            self._next_state_manager.raise_state_to_target_cpo(dto, state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason


def _pick_cap_aware_ladder_state(
    dto: KeywordDTO,
    target_cpo: float,
    *,
    max_target_mode: KeywordStrategyMode,
) -> KeywordV3LadderState | None:
    """Выбрать максимальный CH-backed state под resolve и cap агрессии."""
    cap_level = mode_level(max_target_mode)

    candidates = [
        state
        for state in dto.ladder_states
        if state.cpo is not None
        and state.strategy_mode != KeywordStrategyMode.OFF
        and mode_level(state.strategy_mode) <= cap_level
        and state.cpo <= target_cpo
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda state: mode_level(state.strategy_mode))
