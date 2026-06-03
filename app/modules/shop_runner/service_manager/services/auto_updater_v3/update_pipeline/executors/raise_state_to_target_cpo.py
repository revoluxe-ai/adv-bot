"""Фаза: поднять ключ до max ladder-state с CPO <= resolve кампании."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    KeywordDTO,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.update_context import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)

_OPERABLE_LADDER_STAGES = (
    V3LadderStageKind.MIN_CPA,
    V3LadderStageKind.OPTIMUM,
    V3LadderStageKind.MAX_CONVERSION,
)


class RaiseStateToTargetCpoExecutor:
    """Поднять каждый ключ до max ступени с ``cpo <= adv_state.resolve`` (без skip)."""

    phase_name = "raise_state_to_target_cpo"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(RaiseStateToTargetCpoExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = None
        target_cpo = float(context.adv_state.resolve)
        for dto in context.keywords:
            state = self._get_max_state_to_target_cpo(dto, target_cpo)
            self._next_state_manager.raise_state_to_target_cpo(dto, state)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason

    @staticmethod
    def _get_max_state_to_target_cpo(
        dto: KeywordDTO,
        target_cpo: float,
    ) -> KeywordV3LadderState | None:
        """Максимальная по агрессии ступень MIN/OPT/MAX с ``cpo <= target_cpo``."""
        threshold = float(target_cpo)
        candidates = [
            state
            for state in dto.ladder_states
            if state.cpo is not None
            and state.stage in _OPERABLE_LADDER_STAGES
            and float(state.cpo) <= threshold
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda state: mode_level(state.strategy_mode))
