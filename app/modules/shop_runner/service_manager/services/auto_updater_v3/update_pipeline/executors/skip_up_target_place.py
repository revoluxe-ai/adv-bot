"""Фаза: схлопнуть alias UP на текущем ``target_place`` (до max M/O/C на place)."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    state_candidates_by_mode_for_ctx,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)


class SkipUpTargetPlaceExecutor:
    """Если следующий шаг вверх на том же ``target_place`` — max режим alias-группы."""

    phase_name = "skip_up_same_target_place"
    _skip_reason: str | None = None

    def __init__(self) -> None:
        self._next_state_manager = NextStateManager(SkipUpTargetPlaceExecutor)

    def execute(self, context: UpdateContext) -> None:
        self._skip_reason = None
        ladder_inputs = context.adv_state.ladder_inputs
        for dto in context.keywords:
            if dto.is_not_full():
                continue
            catalog = state_candidates_by_mode_for_ctx(dto.context, ladder_inputs)
            self._next_state_manager.skip_up_same_target_place(dto, catalog)

    @property
    def skip_reason(self) -> str | None:
        return self._skip_reason
