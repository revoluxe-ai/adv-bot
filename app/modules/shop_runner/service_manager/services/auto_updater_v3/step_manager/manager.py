"""Класс StepManager — фасад UP/DOWN по ``UpdateContext`` и resolve по catalog."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.dto import (
    StepCandidate,
    StepRunBatchResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.resolve_effective import (
    resolve_effective_down,
    resolve_effective_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.step_down import (
    run_step_down,
    run_steps_down,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.step_up import (
    run_step_up,
    run_steps_up,
)

PoolT = TypeVar("PoolT")


class StepManager:
    """UP/DOWN по ``UpdateContext``: пул → sort → pick → history."""

    @staticmethod
    def down(
        context: UpdateContext,
        budget: int,
        *,
        collect: Callable[[UpdateContext], Sequence[StepCandidate]],
        sort_key: Callable[[StepCandidate], tuple[float, ...]],
        on_pick: Callable[[StepCandidate, UpdateContext, int], None] | None = None,
    ) -> StepRunBatchResult[StepCandidate]:
        """Серия DOWN-итераций."""
        return run_steps_down(
            context,
            budget,
            collect=collect,
            sort_key=sort_key,
            on_pick=on_pick,
        )

    @staticmethod
    def up(
        context: UpdateContext,
        budget: int,
        *,
        collect: Callable[[UpdateContext], Sequence[PoolT]],
        sort_key: Callable[[PoolT], tuple[float, ...]],
        keyword_setting_id_of: Callable[[PoolT], int],
        to_mode_of: Callable[[PoolT], KeywordStrategyMode | None],
        from_mode_of: Callable[[PoolT], KeywordStrategyMode],
        is_valid_pick: Callable[[PoolT], bool] | None = None,
        on_pick: Callable[[PoolT, UpdateContext, int], None] | None = None,
    ) -> StepRunBatchResult[PoolT]:
        """Серия UP-итераций."""
        return run_steps_up(
            context,
            budget,
            collect=collect,
            sort_key=sort_key,
            keyword_setting_id_of=keyword_setting_id_of,
            to_mode_of=to_mode_of,
            from_mode_of=from_mode_of,
            is_valid_pick=is_valid_pick,
            on_pick=on_pick,
        )

    run_step_down = staticmethod(run_step_down)
    run_step_up = staticmethod(run_step_up)
    run_steps_down = staticmethod(run_steps_down)
    run_steps_up = staticmethod(run_steps_up)
    resolve_down = staticmethod(resolve_effective_down)
    resolve_up = staticmethod(resolve_effective_up)
