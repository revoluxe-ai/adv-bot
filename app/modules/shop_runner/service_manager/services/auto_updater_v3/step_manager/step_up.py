"""UP по списку ключей: пул состояний → sort → pick → bump ``UpdateContext``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keywords_prepared import (
    UpdateContext,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.dto import (
    StepRunBatchResult,
    StepRunResult,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.step_manager.prepared_state import (
    bump_prepared_mode,
)

PoolT = TypeVar("PoolT")


def run_step_up(
    context: UpdateContext,
    *,
    collect: Callable[[UpdateContext], Sequence[PoolT]],
    sort_key: Callable[[PoolT], tuple[float, ...]],
    keyword_setting_id_of: Callable[[PoolT], int],
    to_mode_of: Callable[[PoolT], KeywordStrategyMode | None],
    from_mode_of: Callable[[PoolT], KeywordStrategyMode],
    is_valid_pick: Callable[[PoolT], bool] | None = None,
) -> StepRunResult[PoolT]:
    """Одна итерация UP: пул → pick → обновление ``active_mode`` + history."""
    pool = list(collect(context))
    if not pool:
        return StepRunResult(context=context.copy(), pick=None, pool_size=0)
    best = min(pool, key=sort_key)
    to_mode = to_mode_of(best)
    from_mode = from_mode_of(best)
    valid = (
        is_valid_pick(best)
        if is_valid_pick is not None
        else (to_mode is not None and to_mode != from_mode)
    )
    if not valid or to_mode is None:
        return StepRunResult(context=context.copy(), pick=None, pool_size=len(pool))
    updated = bump_prepared_mode(context, keyword_setting_id_of(best), to_mode)
    return StepRunResult(context=updated, pick=best, pool_size=len(pool))


def run_steps_up(
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
    """До ``budget`` итераций UP с пересбором пула после каждого шага."""
    working = context.copy()
    picks: list[PoolT] = []
    step_budget = max(1, int(budget))
    for _ in range(step_budget):
        result = run_step_up(
            working,
            collect=collect,
            sort_key=sort_key,
            keyword_setting_id_of=keyword_setting_id_of,
            to_mode_of=to_mode_of,
            from_mode_of=from_mode_of,
            is_valid_pick=is_valid_pick,
        )
        if result.pick is None:
            break
        if on_pick is not None:
            on_pick(result.pick, working, result.pool_size)
        working = result.context
        picks.append(result.pick)
    return StepRunBatchResult(context=working, picks=picks)
